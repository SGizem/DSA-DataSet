"""FAZ 8b: Üretilen instruction örneklerini otomatik kontroller ve yargıç modelle doğrular.

Çalıştırma (proje kökünden):
    python -m scripts.10_verify_instructions [--config ...] [--limit N] [--no-judge | --judge-only]

Kontrol sırası (örnek ilk takıldığı kontrolün sebep koduyla elenir, reports/exclusions.csv'ye yazılır):
 1. schema_error: zorunlu alan eksik/boş, bilinmeyen görev türü, passage'a dayanan örnekte kaynak yok ya da
    alan dışı örnekte kaynak var.
 2. too_much_noise: bozuk karakter (U+FFFD, kontrol karakteri) ya da gürültü oranı > filter.max_noise_ratio.
 3. too_short / too_long: talimat ya da cevap config.instruction.verify sınırlarının dışında (Qwen3 token).
 4. invalid_json_quiz: çoktan seçmeli cevabı geçerli JSON değil, dört dolu ve farklı şık yok ya da doğru şık
    şıklardan biri değil.
 5. wrong_language: talimatın ya da cevabın kod dışındaki kısmı Türkçe değil.
 6. task_mismatch: bağlamsız talimat ders içeriğine atıf yapıyor; hata_bulma talimatında kod bloğu yok ya da
    koddaki bütün satırlar ders içeriğinde aynen var (hata konmamış).
 7. duplicate_instruction: talimat başka bir örneğinkiyle çok benzer (MinHash aday + gerçek Jaccard).
 8. Yargıç (ikinci model, temperature 0): not_grounded, judge_rejected, task_mismatch.
Geçenler data/instruction/verified.jsonl'e verified_by="auto_judge", verified=false ile yazılır (insan
doğrulaması FAZ 9'da).

Yargıç kararları data/instruction/judge_results.jsonl'de saklanır: aynı örnek, aynı yargıç modeli ve aynı
yargıç prompt'uyla bir kez yargılanır. Günlük kota dolarsa yargılanmamış örnekler "bekliyor" kalır; script
ertesi gün yeniden çalıştırılınca kaldığı yerden sürer. Her çalıştırma bu adımın eski eleme kayıtlarını silip
kararları baştan yazar (yargıç kararları önbellekten gelir, yeniden istek atılmaz).
--limit N: en çok N yargıç isteği. --no-judge: yalnızca otomatik kontroller (API çağrısı yok).
--judge-only: üretim sürerken yargıç kotasını kullanmak için. Yalnızca yargıç kararlarını toplar;
exclusions.csv ve verified.jsonl'e dokunmaz (09 da exclusions.csv'ye yazdığı için iki script aynı anda
o dosyayı değiştirmesin). Üretim bittikten sonra script bir kez de seçeneksiz çalıştırılır.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from datasketch import MinHash, MinHashLSH
from langdetect import DetectorFactory, detect_langs
from langdetect.lang_detect_exception import LangDetectException

from scripts.utils.chunking import load_tokenizer, token_counter
from scripts.utils.config import add_common_args, load_config, resolve_path, set_seed
from scripts.utils.llm import (API_ERROR, DailyQuotaExhausted, LLMClient, append_jsonl, counts_as_attempt, read_jsonl,
                               write_jsonl)
from scripts.utils.logging_utils import log_summary, setup_logger
from scripts.utils.registry import drop_exclusions, log_exclusion
from scripts.utils.text_utils import CODE_START, INDENTED, tr_lower

gen = importlib.import_module("scripts.09_generate_instructions")
noise_ratio = importlib.import_module("scripts.04_filter").noise_ratio

DetectorFactory.seed = 0  # langdetect'in rastgeleliği sabit: aynı metne her çalıştırmada aynı dil
AUTO_STAGE, JUDGE_STAGE = "auto_check", "judge"  # exclusions.csv aşama adları (task_mismatch ikisinde de olabilir)
QUIZ_TASK = "coktan_secmeli_soru_uretimi"
MAX_JUDGE_ATTEMPTS = 2  # yargıç aynı örneğe bu kadar kez geçerli karar vermezse örnek judge_rejected ile elenir
REQUIRED = ["key", "task_type", "instruction", "response", "with_context", "generation_model", "prompt_version"]
BAD_CHARS = re.compile(r"[\x00-\x09\x0b-\x1f\x7f�]")
FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")
LETTER = re.compile(r"[^\W\d_]")
# Terimlerin İngilizcesi parantez içinde verilir (prompt kuralı 3); kısa talimatta dil tespitini yanıltıyor
# (ilk 600 kayıtta Türkçe bir talimat "ca" çıktı).
PARENTHESES = re.compile(r"\([^()]*\)")
# Talimata gömülü kod değerleri (Python sözlüğü, liste, dizgi) dil tespitini İngilizceye çekiyor (22.10.2026: Türkçe
# bir Viterbi talimatı `{"Healthy": 0.6, ...}` yüzünden "en" çıktı).
CODE_LITERALS = [re.compile(r'"[^"\n]*"'), re.compile(r"\[[^\[\]\n]*\]"), re.compile(r"\{[^{}\n]*\}")]
# Türkçeye özgü harfler. Bu harflerin hiçbiri geçmeyen uzun Türkçe metin "Türkçe karakter kullanmadan" yazılmış
# demektir ("Baslangicta dizi ... dongu calisir"); dil tespiti onu Türkçe sayıyor ama model yanlış yazmayı öğrenir.
TURKISH_CHARS = re.compile(r"[çğıöşüÇĞİÖŞÜ]")
TR_MIN_PROB = 0.20  # Türkçe olasılığı en az bu kadarsa metin Türkçe sayılır
WORD = re.compile(r"\w+")
# Bağlamsız talimatta öğrenci ders içeriğini görmez; içeriğe atıf yapan talimat cevapsız kalır. "metin" tek başına
# aranmaz: dizgi eşleme konularında "bir metinde deseni ara" gibi geçerli bir soru olabilir.
CONTEXT_REFERENCE = re.compile(
    r"yukarıdaki|yukarıda (?:verilen|anlatılan|açıklanan)|bu bölüm|ders içeriğ|verilen metin|verilen metn|metne göre|"
    r"bu metin|bu metne|metinde (?:anlatılan|bahsedilen|geçen|verilen|açıklanan|belirtilen|sözü)|metinden yola|"
    r"bu pasaj|bu paragraf", re.IGNORECASE)


# ---------------------------------------------------------------------------------------------------
# 1. Otomatik kontroller
# ---------------------------------------------------------------------------------------------------
def prose(text: str) -> str:
    """Dil tespiti için kod dışı metin: kod blokları, satır içi kod, girintili satırlar ve kod anahtar kelimesiyle
    başlayan satırlar çıkarılır. is_code_like burada kullanılmaz: Türkçe düzyazıdaki ";" satırı kod saydırıyor
    (ilk 328 kayıtta cevapların 120'si dil tespitine hiç girmedi)."""
    text = INLINE_CODE.sub(" ", FENCE.sub("\n", text))
    return "\n".join(line for line in text.splitlines() if not (CODE_START.match(line) or INDENTED.match(line)))


def quiz_problem(response: str) -> str | None:
    """Çoktan seçmeli cevabın yapısal sorunu; sorun yoksa None."""
    try:
        quiz = json.loads(response)
    except json.JSONDecodeError as exc:
        return f"JSON değil: {exc}"[:150]
    if not isinstance(quiz, dict):
        return "JSON nesnesi değil"
    options = quiz.get("options")
    if not isinstance(options, dict) or sorted(options) != list("ABCD"):
        return "şıklar A, B, C, D değil"
    values = [str(v).strip() for v in options.values()]
    if not all(values):
        return "boş şık var"
    if len({tr_lower(v) for v in values}) < 4:
        return "aynı şık iki kez yazılmış"
    if quiz.get("correct") not in options:
        return f"doğru şık geçersiz: {quiz.get('correct')!r}"
    for field in ("question", "explanation"):
        if not isinstance(quiz.get(field), str) or not quiz[field].strip():
            return f"{field} boş"
    return None


def quiz_text(response: str) -> str:
    quiz = json.loads(response)
    return "\n".join([quiz["question"], *quiz["options"].values(), quiz["explanation"]])


def code_lines(text: str) -> list[str]:
    return [" ".join(line.split()) for line in text.splitlines() if line.strip()]


def contains_run(haystack: list[str], needle: list[str]) -> bool:
    """needle, haystack içinde art arda ve aynı sırayla geçiyor mu?"""
    n = len(needle)
    return any(haystack[i:i + n] == needle for i in range(len(haystack) - n + 1))


def hata_bulma_problem(record: dict[str, Any]) -> str | None:
    """Talimattaki kod, ders içeriğindeki bir bölümün satırı satırına kopyasıysa hata konmamıştır. Satır kümesine
    bakmak yetmez: satır silerek, iki satırın yerini değiştirerek ya da içerikte başka yerde geçen bir satırı
    yazarak konan hatalarda da bütün satırlar içerikte bulunur (ilk 294 kayıtta 5 örnek)."""
    blocks = FENCE.findall(record["instruction"])
    if not blocks:
        return "talimatta kod bloğu yok"
    passage = code_lines(record["passage"] or "")
    if all(contains_run(passage, code_lines(block)) for block in blocks):
        return "talimattaki kod ders içeriğindekinin birebir kopyası; hata konmamış"
    return None


def language_of(text: str, min_letters: int) -> str | None:
    """Kod dışı metnin dili; değerlendirilecek kadar harf yoksa None."""
    body = PARENTHESES.sub(" ", prose(text))
    for _ in range(2):  # iç içe {[...]} için iki tur
        for pattern in CODE_LITERALS:
            body = pattern.sub(" ", body)
    if len(LETTER.findall(body)) < min_letters:
        return None
    try:
        langs = detect_langs(body)
    except LangDetectException:
        return None
    if any(lang.lang == "tr" and lang.prob >= TR_MIN_PROB for lang in langs):
        return "tr"
    return langs[0].lang


def auto_check(record: dict[str, Any], cfg: dict[str, Any], count) -> tuple[str, str] | None:
    """Döner: (sebep, ayrıntı) ya da None (geçti)."""
    ic, v = cfg["instruction"], cfg["instruction"]["verify"]
    missing = [f for f in REQUIRED if record.get(f) in (None, "")]
    if missing:
        return "schema_error", f"eksik alan: {', '.join(missing)}"
    task = record["task_type"]
    if task not in ic["taxonomy"]:
        return "schema_error", f"bilinmeyen görev türü: {task}"
    ood = record.get("subtype") == gen.SUBTYPE_OOD
    if ood and (record.get("source_document") or record.get("with_context")):
        return "schema_error", "alan dışı örnekte kaynak doküman ya da bağlam var"
    if not ood and not (record.get("source_document") and record.get("passage")):
        return "schema_error", "kaynak doküman ya da passage eksik"

    text = record["instruction"] + "\n" + record["response"]
    if BAD_CHARS.search(text):
        return "too_much_noise", "bozuk karakter (U+FFFD ya da kontrol karakteri)"
    noise = noise_ratio(text)
    if noise > cfg["filter"]["max_noise_ratio"]:
        return "too_much_noise", f"gürültü oranı {noise}"

    for field in ("instruction", "response"):
        n = count(record[field])
        limits = v[f"{field}_tokens"]
        if n < limits["min"]:
            return "too_short", f"{field} {n} token < {limits['min']}"
        if n > limits["max"]:
            return "too_long", f"{field} {n} token > {limits['max']}"

    response_text = record["response"]
    if task == QUIZ_TASK:
        problem = quiz_problem(record["response"])
        if problem:
            return "invalid_json_quiz", problem
        response_text = quiz_text(record["response"])

    for field, value in (("instruction", record["instruction"]), ("response", response_text)):
        lang = language_of(value, v["language_min_letters"])
        if lang is not None and lang != "tr":
            return "wrong_language", f"{field} dili {lang}"
        body = PARENTHESES.sub(" ", prose(value))
        if lang == "tr" and len(LETTER.findall(body)) >= v["ascii_turkish_min_letters"] and not TURKISH_CHARS.search(body):
            return "wrong_language", f"{field} Türkçe karakter kullanılmadan yazılmış"

    if not record["with_context"] and CONTEXT_REFERENCE.search(record["instruction"]):
        found = CONTEXT_REFERENCE.search(record["instruction"]).group(0)
        return "task_mismatch", f"bağlamsız talimat ders içeriğine atıf yapıyor: '{found}'"
    if task == "hata_bulma":
        problem = hata_bulma_problem(record)
        if problem:
            return "task_mismatch", problem
    return None


# ---------------------------------------------------------------------------------------------------
# 2. Talimat tekrarı
# ---------------------------------------------------------------------------------------------------
def instruction_words(record: dict[str, Any]) -> set[str]:
    return set(WORD.findall(tr_lower(record["instruction"])))


def context_of(record: dict[str, Any]) -> tuple:
    """Modelin gördüğü bağlam. Bağlamlı örnekte passage da kullanıcı mesajındadır; farklı passage'la gelen aynı
    talimat modele farklı bir mesajdır, tekrar sayılmaz."""
    if record["with_context"]:
        return record["source_document"], record["passage_idx"]
    return ()


def duplicate_instructions(records: list[dict[str, Any]], threshold: float, num_perm: int,
                           seed: int) -> dict[str, tuple[str, float]]:
    """{elenen anahtar: (kalan benzer anahtar, Jaccard)}. Anahtar sırasında ilk gelen kalır."""
    words = {r["key"]: instruction_words(r) for r in records}
    by_key = {r["key"]: r for r in records}
    lsh = MinHashLSH(threshold=0.5, num_perm=num_perm)  # aday üretir; karar gerçek Jaccard'la
    hashes = {}
    for key in sorted(words):
        m = MinHash(num_perm=num_perm, seed=seed)
        m.update_batch([w.encode("utf-8") for w in sorted(words[key])])
        hashes[key] = m
        lsh.insert(key, m)
    dropped: dict[str, tuple[str, float]] = {}
    for key in sorted(words):
        if key in dropped:
            continue
        for other in sorted(lsh.query(hashes[key])):
            if other <= key or other in dropped or context_of(by_key[key]) != context_of(by_key[other]):
                continue
            union = words[key] | words[other]
            score = len(words[key] & words[other]) / len(union) if union else 1.0
            if score >= threshold:
                dropped[other] = (key, round(score, 4))
    return dropped


# ---------------------------------------------------------------------------------------------------
# 3. Yargıç
# ---------------------------------------------------------------------------------------------------
VERDICT_FIELDS = ["supported", "answers_instruction", "task_type_ok", "states_limit", "answer_in_passage"]
JUDGE_SCHEMA = {
    "type": "OBJECT",
    "properties": {"items": {"type": "ARRAY", "items": {
        "type": "OBJECT",
        "properties": {"id": {"type": "STRING"}, "note": {"type": "STRING"},
                       "unsupported_claims": {"type": "ARRAY", "items": {"type": "STRING"}},
                       **{f: {"type": "BOOLEAN"} for f in VERDICT_FIELDS}},
        "required": ["id", "note", "unsupported_claims", *VERDICT_FIELDS],
        "property_ordering": ["id", "note", "unsupported_claims", *VERDICT_FIELDS]}}},
    "required": ["items"],
}


def load_judge_prompt(cfg: dict[str, Any]) -> tuple[str, str]:
    text = (resolve_path(cfg, "prompts_dir") / "judge.md").read_text(encoding="utf-8").strip()
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def show_response(record: dict[str, Any]) -> str:
    if record["task_type"] != QUIZ_TASK:
        return record["response"]
    quiz = json.loads(record["response"])
    options = "\n".join(f"{k}) {quiz['options'][k]}" for k in "ABCD")
    return f"Soru: {quiz['question']}\n{options}\nDoğru şık: {quiz['correct']}\nAçıklama: {quiz['explanation']}"


def build_judge_prompt(group: list[dict[str, Any]], passage: dict[str, Any] | None) -> str:
    parts = []
    if passage:
        parts.append(f"DERS İÇERİĞİ (kaynak: {passage['title']}):\n<<<\n{passage['text']}\n>>>")
    else:
        parts.append("Bu örneklerin ders içeriği yok: hepsi bilgi_yetersizligi / alan_disi örnekleri.")
    parts.append("DEĞERLENDİRİLECEK ÖRNEKLER:")
    for i, r in enumerate(group, start=1):
        mode = "BAĞLAMLI (öğrenci içeriği görüyor)" if r["with_context"] else "BAĞLAMSIZ (öğrenci içeriği görmüyor)"
        sub = f" / {r['subtype']}" if r.get("subtype") else ""
        parts.append(f"### id=e{i}\nGörev türü: {r['task_type']}{sub}\nBağlam: {mode}\n"
                     f"TALİMAT:\n<<<\n{r['instruction']}\n>>>\nCEVAP:\n<<<\n{show_response(r)}\n>>>")
    parts.append('ÇIKTI: Yalnızca {"items": [...]} biçiminde JSON döndür; her örnek için bir öğe, id aynen.')
    return "\n\n".join(parts)


def parse_verdicts(text: str, group: list[dict[str, Any]]) -> tuple[dict[str, dict], dict[str, str]]:
    try:
        items = json.loads(text).get("items")
    except (json.JSONDecodeError, AttributeError) as exc:
        return {}, {r["key"]: f"yargıç çıktısı JSON değil: {exc}"[:200] for r in group}
    by_id = {str(item.get("id")): item for item in items or [] if isinstance(item, dict)}
    ok, errors = {}, {}
    for i, r in enumerate(group, start=1):
        item = by_id.get(f"e{i}")
        if item is None or not all(isinstance(item.get(f), bool) for f in VERDICT_FIELDS):
            errors[r["key"]] = "yargıç bu örnek için geçerli karar vermedi"
        else:
            ok[r["key"]] = {f: item[f] for f in VERDICT_FIELDS} | {
                "note": str(item.get("note", ""))[:500],
                "unsupported_claims": [str(c)[:300] for c in item.get("unsupported_claims") or []]}
    return ok, errors


def judge_decision(record: dict[str, Any], verdict: dict[str, Any]) -> tuple[str, str] | None:
    """Yargıç kararını sebep koduna çevirir. Döner: (sebep, ayrıntı) ya da None (geçti)."""
    note = verdict.get("note", "")
    subtype = record.get("subtype")
    if subtype == gen.SUBTYPE_OOD:
        return None if verdict["states_limit"] else ("judge_rejected", f"alan sınırı belirtilmemiş: {note}")
    if not verdict["supported"]:
        claims = "; ".join(verdict.get("unsupported_claims") or []) or note
        return "not_grounded", claims[:300]
    if subtype == gen.SUBTYPE_MISSING:
        if verdict["answer_in_passage"]:
            return "judge_rejected", f"sorunun cevabı ders içeriğinde var: {note}"
        if not verdict["states_limit"]:
            return "judge_rejected", f"sınır belirtilmemiş: {note}"
        return None
    if not verdict["answers_instruction"]:
        return "judge_rejected", f"cevap talimatı karşılamıyor: {note}"
    if not verdict["task_type_ok"]:
        return "task_mismatch", f"görev türüne uymuyor: {note}"
    return None


def judge_groups(records: list[dict[str, Any]], ood_batch: int) -> list[list[dict[str, Any]]]:
    """Aynı passage'ın örnekleri tek istekte (passage bir kez gönderilir); alan dışı örnekler ood_batch'lik gruplar."""
    by_passage: dict[tuple, list] = defaultdict(list)
    ood = []
    for r in sorted(records, key=lambda r: r["key"]):
        if r.get("subtype") == gen.SUBTYPE_OOD:
            ood.append(r)
        else:
            by_passage[(r["source_document"], r["passage_idx"])].append(r)
    groups = [by_passage[k] for k in sorted(by_passage)]
    return groups + [ood[i:i + ood_batch] for i in range(0, len(ood), ood_batch)]


# ---------------------------------------------------------------------------------------------------
# 4. Çalıştırma
# ---------------------------------------------------------------------------------------------------
def read_raw(path) -> list[dict[str, Any]]:
    """Üretim sürerken de okunabilir: yazılmakta olan yarım son satır atlanır."""
    records = []
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            if i != len(lines) - 1:
                raise
    return records


def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description=__doc__.splitlines()[0]))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--no-judge", action="store_true", help="Yalnızca otomatik kontroller (API çağrısı yok)")
    mode.add_argument("--judge-only", action="store_true",
                      help="Yalnızca yargıç kararlarını topla; exclusions.csv ve verified.jsonl yazılmaz")
    args = parser.parse_args()
    cfg = load_config(args.config)
    logger = setup_logger("10_verify_instructions", cfg)
    seed = set_seed(cfg)
    ic, v = cfg["instruction"], cfg["instruction"]["verify"]
    out_dir = resolve_path(cfg, "instruction_dir")
    raw = read_raw(out_dir / "generated_raw.jsonl")
    if len({r["key"] for r in raw}) != len(raw):
        raise SystemExit("generated_raw.jsonl içinde aynı anahtar iki kez var; resume bozulmuş olabilir.")
    count = token_counter(load_tokenizer(cfg))
    removed = 0 if args.judge_only else drop_exclusions(cfg, "instruction", {r["key"] for r in raw},
                                                            [AUTO_STAGE, JUDGE_STAGE])
    logger.info("Ham örnek: %d | eski doğrulama kaydı silindi: %d", len(raw), removed)

    decisions: dict[str, tuple[str, str, str]] = {}  # anahtar: (aşama, sebep, ayrıntı)
    for r in raw:
        result = auto_check(r, cfg, count)
        if result:
            decisions[r["key"]] = (AUTO_STAGE, *result)
    passed = [r for r in raw if r["key"] not in decisions]
    dups = duplicate_instructions(passed, v["duplicate_threshold"], v["duplicate_num_perm"], seed)
    for key, (kept, score) in dups.items():
        decisions[key] = (AUTO_STAGE, "duplicate_instruction", f"benzer: {kept} (Jaccard {score})")
    candidates = [r for r in passed if r["key"] not in dups]
    logger.info("Otomatik kontroller: %d elendi %s | yargıca giden: %d", len(decisions),
                dict(Counter(d[1] for d in decisions.values())), len(candidates))

    judge_cfg = ic["judge"]
    judge_prompt, judge_sha = load_judge_prompt(cfg)
    results_path = out_dir / "judge_results.jsonl"
    cached: dict[str, dict] = {}
    failures: Counter = Counter()
    for entry in read_jsonl(results_path):
        if entry["judge_model"] != judge_cfg["model"] or entry["judge_prompt_sha"] != judge_sha:
            continue  # başka model ya da prompt'la verilmiş karar geçersiz
        if "error" in entry:
            if counts_as_attempt(entry):  # API/ağ hatası deneme sayılmaz
                failures[entry["key"]] += 1
        else:
            cached[entry["key"]] = entry["verdict"]

    todo = [r for r in candidates if r["key"] not in cached and failures[r["key"]] < MAX_JUDGE_ATTEMPTS]
    requests_made, stopped_for_quota = 0, False
    if todo and not args.no_judge:
        judge = LLMClient(judge_cfg, out_dir / "judge_request_log.jsonl", logger, JUDGE_SCHEMA)
        logger.info("Yargıç: %s | bugün kullanılan istek: %d/%d | yargılanacak örnek: %d", judge.model,
                    judge.used_today(), judge_cfg["requests_per_day"], len(todo))
        passages = {(p["document_id"], p["passage_idx"]): p for p in read_jsonl(out_dir / "passages.jsonl")}
        for group in judge_groups(todo, judge_cfg["out_of_domain_batch"]):
            if args.limit is not None and requests_made >= args.limit:
                break
            first = group[0]
            passage = passages.get((first["source_document"], first["passage_idx"])) if first["source_document"] else None
            try:
                text = judge.generate(judge_prompt, build_judge_prompt(group, passage))
            except DailyQuotaExhausted:
                stopped_for_quota = True
                break
            except Exception as exc:  # yeniden denemelere rağmen API/ağ hatası: deneme sayılmaz, sonra yeniden denenir
                stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
                append_jsonl(results_path, [{"key": r["key"], "judge_model": judge.model, "judge_prompt_sha": judge_sha,
                                             "timestamp": stamp, "error": f"{type(exc).__name__}: {exc}"[:200],
                                             "kind": API_ERROR} for r in group])
                logger.warning("API hatası, %d örnek sonraki çalıştırmaya kaldı: %s", len(group), str(exc)[:150])
                requests_made += 1
                continue
            else:
                ok, errors = parse_verdicts(text, group)
            requests_made += 1
            stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            base = {"judge_model": judge.model, "judge_prompt_sha": judge_sha, "timestamp": stamp}
            append_jsonl(results_path, [{"key": k, **base, "verdict": verdict} for k, verdict in ok.items()]
                         + [{"key": k, **base, "error": e} for k, e in errors.items()])
            cached.update(ok)
            for k in errors:
                failures[k] += 1
            if errors:
                logger.warning("Yargıç %d örnekte geçerli karar vermedi: %s", len(errors), "; ".join(errors.values())[:300])
            if requests_made % 25 == 0:
                logger.info("Yargıç ilerleme: %d istek, %d/%d karar", requests_made, len(cached), len(candidates))

    if args.judge_only:
        logger.info("--judge-only: %d istek, toplam %d/%d yargıç kararı hazır%s", requests_made, len(cached),
                    len(candidates), " (günlük kota doldu)" if stopped_for_quota else "")
        return

    verified, pending = [], 0
    for r in candidates:
        if r["key"] in cached:
            result = judge_decision(r, cached[r["key"]])
            if result:
                decisions[r["key"]] = (JUDGE_STAGE, *result)
            else:
                verified.append(r | {"verified_by": "auto_judge", "verified": False,
                                     "judge_model": judge_cfg["model"], "judge_prompt_sha": judge_sha})
        elif failures[r["key"]] >= MAX_JUDGE_ATTEMPTS:
            decisions[r["key"]] = (JUDGE_STAGE, "judge_rejected", "yargıç iki denemede geçerli karar vermedi")
        else:
            pending += 1

    for key in sorted(decisions):
        stage, reason, detail = decisions[key]
        log_exclusion(cfg, "instruction", key, stage, reason, detail)
    write_jsonl(out_dir / "verified.jsonl", sorted(verified, key=lambda r: r["key"]))
    state = {"raw": len(raw), "verified": len(verified), "excluded": len(decisions), "pending": pending,
             "judge_model": judge_cfg["model"], "judge_prompt_sha": judge_sha,
             "reasons": dict(sorted(Counter(f"{d[0]}/{d[1]}" for d in decisions.values()).items()))}
    (out_dir / "verify_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    if stopped_for_quota:
        logger.warning("Yargıcın günlük kotası doldu (%s). Kota Türkiye saatiyle ~10:00'da sıfırlanır; script'i "
                       "yeniden çalıştırınca kaldığı yerden sürer.", judge_cfg["model"])
    logger.info("Sonuç: %d doğrulandı, %d elendi %s, %d yargıç kararı bekliyor (bu çalıştırmada %d yargıç isteği)",
                len(verified), len(decisions), state["reasons"], pending, requests_made)
    log_summary(logger, len(raw), len(verified), len(decisions), pending)


if __name__ == "__main__":
    main()
