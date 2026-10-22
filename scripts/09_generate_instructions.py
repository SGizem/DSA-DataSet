"""FAZ 8a: Final dokümanlardan öğretmen modelle instruction (talimat-cevap) örnekleri üretir.

Çalıştırma (proje kökünden):
    python -m scripts.09_generate_instructions [--config ...] [--limit N] [--plan-only]

Akış:
1. Final dokümanlar utils/chunking.py ile paragraf/başlık/cümle sınırlarından passage'lara bölünür
   (config.instruction.passage_tokens) -> data/instruction/passages.jsonl.
2. Planlayıcı (seed'li): (doküman, passage, görev türü) üçlüleri taxonomy oranlarına ve
   target_total x plan_factor'a göre seçilir. Görev türü yalnızca uygun passage'a verilir (kod okuma kod
   içeren passage'a, karmaşıklık analizi karmaşıklıktan söz eden passage'a ...). Bir doküman en çok
   max_per_document görev alır; external_api_ok=no kaynaklar planlanmaz. -> data/instruction/plan.jsonl
3. Aynı passage'ın görevleri tek istekte (en çok tasks_per_request) üretilir; alan dışı sorular passage'sız
   gruplar hâlinde. Her kayıt üretilir üretilmez generated_raw.jsonl'e eklenir (append + flush).
4. Resume: (document_id, passage_idx, task_type) daha önce üretilmişse atlanır; script kesilip yeniden
   başlatılabilir. Günlük kota (requests_per_day) dolunca script durur, ertesi gün kaldığı yerden sürer.

--limit N: plan sırasındaki ilk N görev bitene kadar çalışır (pilot). Plan sırası görev türlerini sırayla
dolaşır, böylece pilotta bütün türler bulunur. --plan-only: API çağırmadan planı ve dağılımını yazar.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from scripts.utils.chunking import chunk_text, load_tokenizer, token_counter
from scripts.utils.config import add_common_args, load_config, resolve_path, set_seed
from scripts.utils.llm import (API_ERROR, DailyQuotaExhausted, EmptyResponse, LLMClient, append_jsonl,  # noqa: F401
                               counts_as_attempt, is_daily_quota, is_transient, read_jsonl, write_jsonl)
from scripts.utils.logging_utils import log_summary, setup_logger
from scripts.utils.registry import drop_exclusions, load_registry, log_exclusion
from scripts.utils.text_utils import is_code_like

SPLITS = ["train", "validation", "test"]
OOD_TASK = "bilgi_yetersizligi"
SUBTYPE_OOD, SUBTYPE_MISSING = "alan_disi", "metinde_yok"
CODE_TASKS = {"kod_okuma", "hata_bulma"}
ANY_SOURCE_TASKS = {"algoritma_izleme", "karmasiklik_analizi"}  # kod ya da düzyazı passage olabilir
MAX_ATTEMPTS = 2  # aynı görev bu kadar kez geçersiz çıktı verirse generation_error ile elenir

COMPLEXITY = re.compile(r"O\(|Θ\(|Ω\(|\\Theta|\\Omega|\\mathcal\{O\}|complexity|karmaşıklı|running time|"
                        r"çalışma zaman|worst case|en kötü durum|amortized|asymptotic", re.IGNORECASE)
ALGORITHM_WORD = re.compile(r"\b(?:algorithm|algoritma|pseudocode|sözde kod|insert|delet|rotat|travers|"
                            r"ekle|sil|döndür|dolaş)", re.IGNORECASE)
STEP_WORD = re.compile(r"\b(?:step|first|then|next|repeat|until|iterat|recursive|adım|önce|sonra|tekrar|"
                       r"yinele)\w*", re.IGNORECASE)
# Kaynakça satırı: pilotta kaynakça listesinden "Landau kimdir?" gibi işe yaramaz sorular üretildi.
CITATION = re.compile(r"\bRetrieved\b|\bISBN\b|\bdoi:|\bArchived\b|\(PDF\)|Erişim tarihi|\bArşivlenmiş\b")
CITATION_SHARE = 0.3  # satırlarının en az bu kadarı kaynakça satırı olan passage planlanmaz
CODE_RUN_MIN = 3   # kod bloğu sayılmak için art arda en az bu kadar kod satırı
STEP_MIN = 3       # algoritma adım adım anlatılıyor sayılmak için en az bu kadar adım kelimesi

# ---------------------------------------------------------------------------------------------------
# 1. Passage'lar
# ---------------------------------------------------------------------------------------------------
TEX = re.compile(r"\$|\\[a-zA-Z]{2,}")  # $...$ ya da \frac, \log: formül satırı, kod değil

def is_code_line(line: str) -> bool:
    """Kod/sözde kod satırı. is_code_like `{ } =` gördüğünde Vikipedi formüllerini de kod sayar; onlar dışarıda."""
    return is_code_like(line) and not TEX.search(line)

def longest_code_run(lines: list[str]) -> int:
    """Art arda gelen en uzun kod satırı dizisi (boş satırlar diziyi bozmaz). Düzyazının arasında tek tük
    kod gibi görünen satır (ör. "parent(v);") kod bloğu sayılmasın diye satır sayısı değil dizi uzunluğu."""
    best = run = 0
    for line in lines:
        if not line.strip():
            continue
        run = run + 1 if is_code_line(line) else 0
        best = max(best, run)
    return best

def passage_flags(text: str, source_type: str) -> dict[str, bool]:
    """Görev uygunluğu için passage özellikleri.

    has_code: kod dokümanı ya da en az CODE_RUN_MIN satırlık kod/sözde kod bloğu (kod okuma, hata bulma).
    complexity: karmaşıklıktan söz ediyor (karmaşıklık analizi).
    procedural: kod bloğu var ya da bir algoritma/işlem adım adım anlatılıyor (algoritma izleme).
    """
    lines = text.split("\n")
    has_code = source_type == "code" or longest_code_run(lines) >= CODE_RUN_MIN
    steps = len(STEP_WORD.findall(text))
    procedural = has_code or (bool(ALGORITHM_WORD.search(text)) and steps >= STEP_MIN)
    filled = [line for line in lines if line.strip()]
    citations = source_type != "code" and \
        sum(1 for line in filled if CITATION.search(line)) >= CITATION_SHARE * max(len(filled), 1)
    return {"has_code": has_code, "complexity": bool(COMPLEXITY.search(text)), "procedural": procedural,
            "citations": citations}

def build_passages(cfg: dict[str, Any], records: list[dict[str, Any]], source_types: dict[str, str],
                   count) -> list[dict[str, Any]]:
    p = cfg["instruction"]["passage_tokens"]
    passages = []
    for record in sorted(records, key=lambda r: r["document_id"]):
        source_type = source_types[record["document_id"]]
        for idx, text in enumerate(chunk_text(record["text"], source_type, count, p["min"], p["max"])):
            passages.append({"document_id": record["document_id"], "passage_idx": idx, "title": record["title"],
                             "source": record["source"], "source_type": source_type, "language": record["language"],
                             "split": record["split"], "tokens": count(text),
                             **passage_flags(text, source_type), "text": text})
    return passages

def eligible(task: str, p: dict[str, Any], max_tokens: int) -> bool:
    """Görev türü bu passage'a verilebilir mi?"""
    if p["tokens"] > max_tokens or p.get("citations"):  # bölünemeyen tek satır ya da kaynakça ağırlıklı
        return False
    if task in CODE_TASKS:
        return p["has_code"]
    if task == "karmasiklik_analizi":
        return p["complexity"]
    if task == "algoritma_izleme":
        return p["procedural"]
    return p["source_type"] != "code"  # kavram, karşılaştırma, özet ...: düzyazı passage

# ---------------------------------------------------------------------------------------------------
# 2. Plan
# ---------------------------------------------------------------------------------------------------
def task_key(document_id: str | None, passage_idx: int, task_type: str) -> str:
    return f"{document_id or 'OOD'}:{passage_idx}:{task_type}"

def type_counts(cfg: dict[str, Any]) -> tuple[dict[str, int], int]:
    """Görev türü başına planlanan sayı ve bunun içinden alan dışı (passage'sız) bilgi_yetersizligi sayısı."""
    ic = cfg["instruction"]
    total = round(ic["target_total"] * ic["plan_factor"])
    counts = {t: round(ratio * total) for t, ratio in ic["taxonomy"].items()}
    ood = round(counts.get(OOD_TASK, 0) * ic["out_of_domain_share"])
    return counts, ood

def plan_tasks(passages: list[dict[str, Any]], cfg: dict[str, Any], seed: int, logger=None) -> list[dict[str, Any]]:
    """Seed'li plan. Kıt türler (uygun passage'ı az olanlar) önce yerleştirilir. Bir görev önce, içinde
    başka türden görev bulunan ve dolmamış bir passage'a konur (aynı istekte üretilsin diye), yoksa yeni
    bir passage'a. Aynı passage'a aynı tür iki kez verilmez."""
    ic = cfg["instruction"]
    rng = random.Random(seed)
    counts, ood = type_counts(cfg)
    per_request, cap, max_tokens = ic["tasks_per_request"], ic["max_per_document"], ic["passage_tokens"]["max"]
    keys = [(p["document_id"], p["passage_idx"]) for p in passages]
    by_key = dict(zip(keys, passages))
    order = keys[:]
    rng.shuffle(order)
    rank = {k: i for i, k in enumerate(order)}
    need = {t: c - (ood if t == OOD_TASK else 0) for t, c in counts.items()}
    pools = {t: sorted((k for k in keys if eligible(t, by_key[k], max_tokens)), key=rank.get) for t in need}

    assigned: dict[tuple, list[str]] = defaultdict(list)
    per_doc: Counter = Counter()
    for t in sorted(need, key=lambda t: (len(pools[t]) / max(need[t], 1), t)):
        partial = [k for k in pools[t] if 0 < len(assigned[k]) < per_request]
        fresh = [k for k in pools[t] if not assigned[k]]
        placed = 0
        for k in partial + fresh:
            if placed == need[t]:
                break
            if t in assigned[k] or len(assigned[k]) >= per_request or per_doc[k[0]] >= cap:
                continue
            assigned[k].append(t)
            per_doc[k[0]] += 1
            placed += 1
        if placed < need[t] and logger:
            logger.warning("%s: %d görev planlanabildi, hedef %d (uygun passage yetmedi)", t, placed, need[t])

    tasks = []
    for k in sorted(assigned, key=rank.get):
        for t in assigned[k]:
            p = by_key[k]
            subtype = SUBTYPE_MISSING if t == OOD_TASK else ""
            tasks.append({"key": task_key(k[0], k[1], t), "document_id": k[0], "passage_idx": k[1], "task_type": t,
                          "subtype": subtype, "with_context": subtype == SUBTYPE_MISSING, "split": p["split"],
                          "group": f"{k[0]}:{k[1]}"})
    topics = ic["out_of_domain_topics"]
    batch = ic["out_of_domain_batch"]
    topic_order = []
    while len(topic_order) < ood:  # konular sırayla, her turda seed'li karışık: bir grupta aynı konu yok
        cycle = topics[:]
        rng.shuffle(cycle)
        topic_order += cycle
    for i in range(ood):
        tasks.append({"key": task_key(None, i, OOD_TASK), "document_id": None, "passage_idx": i, "task_type": OOD_TASK,
                      "subtype": SUBTYPE_OOD, "with_context": False, "split": "", "topic": topic_order[i],
                      "group": f"OOD:{i // batch}"})

    # with_context: hedef orana tam uymak için zorunlu olanlar (metinde_yok) dışındakilerden seed'li seçim
    target = round(ic["with_context_ratio"] * len(tasks))
    forced = sum(t["with_context"] for t in tasks)
    free = [t for t in tasks if not t["with_context"] and t["subtype"] != SUBTYPE_OOD]
    for t in rng.sample(free, max(0, min(len(free), target - forced))):
        t["with_context"] = True
    return tasks

def passage_preference(p: dict[str, Any]) -> int:
    """Ek plan için passage önceliği: 0 kod dosyası, 1 kod bloğu içeren metin, 2 düzyazı. Ana üretimde izleme ve
    hata bulma örneklerinin doğrulamadan geçme oranı bu sırayla düştü (experiments.md, 20.10.2026)."""
    return 0 if p["source_type"] == "code" else 1 if p["has_code"] else 2


def plan_top_up(passages: list[dict[str, Any]], base: list[dict[str, Any]], cfg: dict[str, Any],
                seed: int, logger=None) -> list[dict[str, Any]]:
    """config.instruction.top_up'taki türler için ana plana EK görevler. Ana plan değişmez (anahtarları ve
    sırası aynı kalır, üretilmiş kayıtlar geçerli kalır). Ek görev, ana planda o türü almamış bir passage'a
    verilir; doküman sınırı ana planla birlikte sayılır. Passage'lar önce önceliğe, sonra seed'li sıraya göre."""
    ic = cfg["instruction"]
    extra = ic.get("top_up") or {}
    if not extra:
        return []
    rng = random.Random(f"{seed}:topup")
    cap, per_request, max_tokens = ic["max_per_document"], ic["tasks_per_request"], ic["passage_tokens"]["max"]
    used = {t["key"] for t in base}
    per_doc = Counter(t["document_id"] for t in base if t["document_id"])
    keys = [(p["document_id"], p["passage_idx"]) for p in passages]
    by_key = dict(zip(keys, passages))
    order = keys[:]
    rng.shuffle(order)
    rank = {k: i for i, k in enumerate(order)}
    assigned: dict[tuple, list[str]] = defaultdict(list)
    for t in sorted(extra):
        pool = sorted((k for k in keys if eligible(t, by_key[k], max_tokens) and task_key(k[0], k[1], t) not in used),
                      key=lambda k: (passage_preference(by_key[k]), rank[k]))
        placed = 0
        for k in pool:
            if placed == extra[t]:
                break
            if per_doc[k[0]] >= cap or len(assigned[k]) >= per_request:
                continue
            assigned[k].append(t)
            per_doc[k[0]] += 1
            placed += 1
        if placed < extra[t] and logger:
            logger.warning("Ek plan %s: %d görev planlanabildi, istenen %d", t, placed, extra[t])
    tasks = [{"key": task_key(k[0], k[1], t), "document_id": k[0], "passage_idx": k[1], "task_type": t,
              "subtype": "", "with_context": False, "split": by_key[k]["split"], "group": f"EK:{k[0]}:{k[1]}"}
             for k in sorted(assigned, key=lambda k: (passage_preference(by_key[k]), rank[k])) for t in assigned[k]]
    for t in rng.sample(tasks, round(ic["with_context_ratio"] * len(tasks))):
        t["with_context"] = True
    return tasks


def execution_order(tasks: list[dict[str, Any]], seed: int) -> list[list[dict[str, Any]]]:
    """İstek grupları; görev türlerini sırayla dolaşan bir düzende (pilot ve kısmi çalıştırma bütün türleri
    görsün). Grup içi sıra plan sırası."""
    groups: dict[str, list] = defaultdict(list)
    for t in tasks:
        groups[t["group"]].append(t)
    names = sorted(groups)
    random.Random(f"{seed}:order").shuffle(names)
    by_type: dict[str, list[str]] = defaultdict(list)
    for name in names:  # alan dışı sorular ayrı bir "tür" sayılır: pilotta iki alt tür de görünsün
        for t in {task["task_type"] + (":" + task["subtype"] if task["subtype"] == SUBTYPE_OOD else "")
                  for task in groups[name]}:
            by_type[t].append(name)
    types = sorted(by_type)
    ordered, used = [], set()
    pointers = {t: 0 for t in types}
    while len(ordered) < len(names):
        for t in types:
            queue = by_type[t]
            while pointers[t] < len(queue) and queue[pointers[t]] in used:
                pointers[t] += 1
            if pointers[t] < len(queue):
                name = queue[pointers[t]]
                used.add(name)
                ordered.append(groups[name])
    return ordered

# ---------------------------------------------------------------------------------------------------
# 3. Prompt
# ---------------------------------------------------------------------------------------------------
def load_prompts(cfg: dict[str, Any]) -> tuple[str, dict[str, str], str]:
    """Ortak kurallar, görev türü dosyaları ve hepsinin kısa özeti (hangi prompt metniyle üretildiği izlensin)."""
    folder = resolve_path(cfg, "prompts_dir")
    common = (folder / "_common.md").read_text(encoding="utf-8").strip()
    tasks = {t: (folder / f"{t}.md").read_text(encoding="utf-8").strip() for t in cfg["instruction"]["taxonomy"]}
    digest = hashlib.sha256((common + "".join(tasks[t] for t in sorted(tasks))).encode("utf-8")).hexdigest()[:12]
    return common, tasks, digest

# Yapılandırılmış çıktı şeması: API çıktıyı bu şemaya uyan geçerli JSON olarak üretir. Şemasız denemede model
# LaTeX'i (\log, \frac) kaçışsız yazıp JSON'u bozdu (pilot, 19.10.2026); sonradan onarmak güvenli değil,
# çünkü \f ve \n geçerli JSON kaçışlarıdır ve \frac sessizce başka karaktere dönüşürdü.
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {"items": {"type": "ARRAY", "items": {
        "type": "OBJECT",
        "properties": {
            "task_id": {"type": "STRING"},
            "instruction": {"type": "STRING"},
            "response": {"type": "STRING"},
            "quiz": {"type": "OBJECT", "properties": {
                "question": {"type": "STRING"},
                "options": {"type": "OBJECT", "properties": {k: {"type": "STRING"} for k in "ABCD"},
                            "required": list("ABCD"), "property_ordering": list("ABCD")},
                "correct": {"type": "STRING", "enum": list("ABCD")},
                "explanation": {"type": "STRING"}},
                "required": ["question", "options", "correct", "explanation"],
                "property_ordering": ["question", "options", "correct", "explanation"]}},
        "required": ["task_id", "instruction"],
        "property_ordering": ["task_id", "instruction", "response", "quiz"]}}},
    "required": ["items"],
}

# Satır sonu dışındaki kontrol karakterleri. Pilotta model "\text" yazdı; JSON'da "\t" geçerli bir kaçış (TAB)
# olduğu için metin "TAB + ext" oldu. Böyle çıktı onarılmaz (\n ile \nabla ayırt edilemez), görev yeniden üretilir.
CONTROL_CHARS = re.compile(r"[\x00-\x09\x0b-\x1f\x7f]")

OUTPUT_FORMAT = (
    'ÇIKTI: Yalnızca şu JSON nesnesini döndür: {"items": [{"task_id": "...", "instruction": "...", '
    '"response": "..."}]}. Her görev için tam olarak bir öğe yaz, görev sırasını koru, task_id\'yi aynen kopyala. '
    'coktan_secmeli_soru_uretimi görevinde "response" yerine "quiz" alanını kullan.')

def build_prompt(group: list[dict[str, Any]], passage: dict[str, Any] | None, task_rules: dict[str, str]) -> str:
    parts = []
    if passage:
        parts.append(f"DERS İÇERİĞİ (kaynak: {passage['title']}):\n<<<\n{passage['text']}\n>>>")
        parts.append("GÖREVLER:")
        for i, t in enumerate(group, start=1):
            mode = "BAĞLAMLI" if t["with_context"] else "BAĞLAMSIZ"
            sub = " — alt tür (b) METİNDE YOK" if t["subtype"] == SUBTYPE_MISSING else ""
            parts.append(f"--- Görev task_id=g{i}: {t['task_type']} ({mode}){sub}\n{task_rules[t['task_type']]}")
    else:
        topics = "\n".join(f"- task_id=g{i}: {t['topic']}" for i, t in enumerate(group, start=1))
        parts.append(f"Bu istekte ders içeriği yok. GÖREV: {OOD_TASK}, alt tür (a) ALAN DIŞI, BAĞLAMSIZ. "
                     f"Aşağıdaki her konu için bir örnek yaz:\n{topics}\n\n{task_rules[OOD_TASK]}")
    parts.append(OUTPUT_FORMAT)
    return "\n\n".join(parts)

def parse_items(text: str, group: list[dict[str, Any]]) -> tuple[dict[str, tuple[str, str]], dict[str, str]]:
    """Model çıktısından {task_key: (instruction, response)} ve {task_key: hata} çıkarır."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return {}, {t["key"]: f"json_parse: {exc}"[:200] for t in group}
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return {}, {t["key"]: "items listesi yok" for t in group}
    by_id = {str(item.get("task_id")): item for item in items if isinstance(item, dict)}
    ok, errors = {}, {}
    for i, t in enumerate(group, start=1):
        item = by_id.get(f"g{i}")
        if item is None and len(items) == len(group) and isinstance(items[i - 1], dict):
            item = items[i - 1]  # task_id yazılmamış ama sıra korunmuş
        if item is None:
            errors[t["key"]] = "görev çıktıda yok"
            continue
        instruction = item.get("instruction")
        if t["task_type"] == "coktan_secmeli_soru_uretimi":
            quiz = item.get("quiz") if isinstance(item.get("quiz"), dict) else item.get("response")
            if isinstance(quiz, str):
                try:
                    quiz = json.loads(quiz)
                except json.JSONDecodeError:
                    quiz = None
            response = json.dumps(quiz, ensure_ascii=False) if isinstance(quiz, dict) else None
        else:
            response = item.get("response")
        if not isinstance(instruction, str) or not instruction.strip():
            errors[t["key"]] = "instruction boş"
        elif not isinstance(response, str) or not response.strip():
            errors[t["key"]] = "response boş ya da quiz nesnesi yok"
        elif CONTROL_CHARS.search(instruction) or CONTROL_CHARS.search(response):
            errors[t["key"]] = "kontrol karakteri (LaTeX komutu JSON kaçışı olarak okunmuş olabilir: \\text -> TAB+ext)"
        else:
            ok[t["key"]] = (instruction.strip(), response.strip())
    return ok, errors

# ---------------------------------------------------------------------------------------------------
# 4. Çalıştırma
# ---------------------------------------------------------------------------------------------------
def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description=__doc__.splitlines()[0]))
    parser.add_argument("--plan-only", action="store_true", help="API çağırmadan passage'ları ve planı yaz")
    parser.add_argument("--retry-failed", action="store_true",
                        help="Daha önce generation_error ile elenen görevleri yeniden dene (hata nedeni giderildiyse)")
    args = parser.parse_args()
    cfg = load_config(args.config)
    logger = setup_logger("09_generate_instructions", cfg)
    seed = set_seed(cfg)
    ic = cfg["instruction"]
    out_dir = resolve_path(cfg, "instruction_dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path, errors_path = out_dir / "generated_raw.jsonl", out_dir / "generation_errors.jsonl"

    registry = load_registry(cfg)
    final = registry[registry["status"] == "final"]
    allowed = set(final.loc[final["external_api_ok"] != "no", "document_id"])
    source_types = dict(zip(final["document_id"], final["source_type"]))
    records = [r for split in SPLITS for r in read_jsonl(resolve_path(cfg, "final_dir") / f"{split}.jsonl")
               if r["document_id"] in allowed]
    count = token_counter(load_tokenizer(cfg))
    passages = build_passages(cfg, records, source_types, count)
    write_jsonl(out_dir / "passages.jsonl", passages)
    by_passage = {(p["document_id"], p["passage_idx"]): p for p in passages}

    base = plan_tasks(passages, cfg, seed, logger)
    extra = plan_top_up(passages, base, cfg, seed, logger)
    # Ek görevlerin grupları ana planın arkasına: ana plan önce biter, sırası değişmez.
    groups = execution_order(base, seed) + execution_order(extra, f"{seed}:topup")
    tasks = base + extra
    write_jsonl(out_dir / "plan.jsonl", [t for g in groups for t in g])
    type_dist = Counter(t["task_type"] for t in tasks)
    logger.info("Passage: %d | planlanan görev: %d (%d istek) | with_context: %.3f | türler: %s", len(passages),
                len(tasks), len(groups), sum(t["with_context"] for t in tasks) / len(tasks), dict(type_dist))
    if extra:
        logger.info("Ek plan (config.instruction.top_up): %d görev %s", len(extra),
                    dict(Counter(t["task_type"] for t in extra)))
    if args.plan_only:
        return

    common, task_rules, prompt_sha = load_prompts(cfg)
    done = {r["key"] for r in read_jsonl(raw_path)}
    attempts = Counter(e["key"] for e in read_jsonl(errors_path) if counts_as_attempt(e))
    given_up = {k for k, n in attempts.items() if n >= MAX_ATTEMPTS}
    if args.retry_failed and given_up:
        drop_exclusions(cfg, "instruction", given_up, "generate")
        logger.info("%d daha önce elenen görev yeniden denenecek", len(given_up - done))
        attempts = Counter({k: 0 for k in attempts})
        given_up = set()
    teacher = LLMClient(ic["teacher"], out_dir / "request_log.jsonl", logger, RESPONSE_SCHEMA)
    logger.info("Öğretmen: %s | bugün kullanılan istek: %d/%d | önceden üretilmiş: %d", teacher.model,
                teacher.used_today(), ic["teacher"]["requests_per_day"], len(done))

    limit = args.limit
    seen = new = failed = requests_made = 0
    stopped_for_quota = False
    for group in groups:
        if limit is not None and seen >= limit:
            break
        seen += len(group)
        todo = [t for t in group if t["key"] not in done and t["key"] not in given_up]
        if not todo:
            continue
        passage = by_passage.get((todo[0]["document_id"], todo[0]["passage_idx"])) if todo[0]["document_id"] else None
        prompt = build_prompt(todo, passage, task_rules)
        try:
            text = teacher.generate(common, prompt)
        except DailyQuotaExhausted:
            stopped_for_quota = True
            break
        except Exception as exc:  # yeniden denemelere rağmen API/ağ hatası: deneme sayılmaz, sonraki çalıştırmada
            stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")  # yeniden denenir
            append_jsonl(errors_path, [{"key": t["key"], "error": f"{type(exc).__name__}: {exc}"[:200], "kind": API_ERROR,
                                        "timestamp": stamp} for t in todo])
            logger.warning("API hatası, %d görev sonraki çalıştırmaya kaldı: %s", len(todo), str(exc)[:150])
            requests_made += 1
            continue
        else:
            ok, errors = parse_items(text, todo)
        requests_made += 1
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        out = []
        for t in todo:
            if t["key"] in ok:
                instruction, response = ok[t["key"]]
                out.append({"id": t["key"], "key": t["key"], "source_document": t["document_id"],
                            "passage_idx": t["passage_idx"], "task_type": t["task_type"], "subtype": t["subtype"],
                            "with_context": t["with_context"], "instruction": instruction, "response": response,
                            "passage": passage["text"] if passage else None, "topic": t.get("topic"),
                            "generation_method": "llm_sentetik", "generation_model": teacher.model,
                            "prompt_version": ic["prompt_version"], "prompt_sha": prompt_sha,
                            "temperature": ic["teacher"]["temperature"], "top_p": ic["teacher"]["top_p"],
                            "timestamp": stamp})
        append_jsonl(raw_path, out)
        new += len(out)
        done |= {r["key"] for r in out}
        bad = [{"key": k, "error": e, "timestamp": stamp} for k, e in errors.items()]
        if bad:
            append_jsonl(errors_path, bad)
            for b in bad:
                attempts[b["key"]] += 1
                if attempts[b["key"]] >= MAX_ATTEMPTS:
                    log_exclusion(cfg, "instruction", b["key"], "generate", "generation_error", b["error"])
                    failed += 1
            logger.warning("%d görev geçersiz çıktı: %s", len(bad), "; ".join(f"{b['key']}: {b['error']}" for b in bad))
        if requests_made % 25 == 0:
            logger.info("İlerleme: %d istek, %d yeni kayıt, toplam %d/%d", requests_made, new, len(done), len(tasks))

    if stopped_for_quota:
        logger.warning("Günlük istek kotası doldu (%s). Kota Pasifik saatiyle gece yarısı (Türkiye saatiyle "
                       "~10:00) sıfırlanır; script'i yeniden çalıştırınca kaldığı yerden devam eder.", teacher.model)
    logger.info("Bu çalıştırma: %d istek, %d yeni kayıt | toplam üretilmiş: %d/%d görev", requests_made, new,
                len(done & {t["key"] for t in tasks}), len(tasks))
    log_summary(logger, seen if limit is not None else len(tasks), new, failed, 0)

if __name__ == "__main__":
    main()
