"""FAZ 8b: Doğrulanmış instruction örneklerinden Instruction Dataset v1.0'ı derler.

Çalıştırma (proje kökünden):
    python -m scripts.11_build_instruction_dataset [--config ...] [--allow-pending]

Girdi: data/instruction/verified.jsonl (10_verify_instructions), data/registry.csv (dokümanların corpus split'i),
data/instruction/manual_review.jsonl (13_qc_report yazar; varsa).
Çıktı:
- data/final/instruction_v1.0.jsonl: bütün metadata ile tek dosya.
- data/final/instruction_{train,validation,test}.jsonl: SFT'ye hazır {"id", "messages": [user, assistant]}.

Kurallar:
- Split, kaynak dokümanın corpus split'ini miras alır: aynı dokümandan üretilen örnekler aynı kümede kalır, corpus
  test dokümanından üretilen örnek instruction train'e girmez (data leakage yok). Kaynağı olmayan alan dışı
  örnekler seed'li rastgele, split.ratios oranlarıyla atanır.
- Örnekler corpus v0.9'un passage'larından üretildi. passage'ı v1.0 temizliğinde metinden silinen (ör. kaynakça
  bölümü) örnek artık yayımlanan corpus'a dayanmaz: not_grounded sebebiyle, aşama "build" olarak çıkarılır.
  Ölçü: passage'ın instruction.build.passage_ngram kelimelik dizilerinden kaynak dokümanın v1.0 metninde
  bulunanların oranı; instruction.build.min_passage_overlap'in altındaysa passage silinmiş sayılır.
- Manuel incelemede reddedilen örnekler çıkarılır; onaylananlara verified=true, verified_by="manual:<ad>" yazılır.
- Çoktan seçmeli sorularda öğretmen model doğru şıkkı çoğunlukla B'ye koydu (403 sorunun 244'ü, D yalnızca 12).
  Model "cevap B" kalıbını öğrenmesin diye doğru şık, anahtarın seed'li özetinden seçilen harfe taşınır: o
  harfteki şıkla yer değiştirir, açıklamadaki şık atıflarında ("A şıkkı", "B ve C seçenekleri") iki harf
  karşılıklı değişir. Harf soruda, şıklarda ya da açıklamada içerik olarak da geçiyorsa ("A matrisi",
  "D böleni", "C'den") soru olduğu gibi kalır.
- id'ler anahtar sırasıyla INS_00001'den başlar.
- with_context=true örneklerde kullanıcı mesajı "Ders içeriği:\\n{passage}\\n\\n{instruction}" şablonuyla kurulur.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
from collections import Counter
from typing import Any

from scripts.utils.chunking import load_tokenizer, token_counter
from scripts.utils.config import add_common_args, load_config, resolve_path, set_seed
from scripts.utils.llm import read_jsonl, write_jsonl
from scripts.utils.logging_utils import log_summary, setup_logger
from scripts.utils.registry import drop_exclusions, load_registry, log_exclusion

assign_splits = importlib.import_module("scripts.06_split").assign_splits

SPLITS = ["train", "validation", "test"]
DATASET_FILE = "instruction_v1.0.jsonl"
MANUAL_REVIEW = "manual_review.jsonl"
BUILD_STAGE = "build"  # exclusions.csv aşama adı
WORD = re.compile(r"\w+")
QUIZ_TASK = "coktan_secmeli_soru_uretimi"
OPTIONS = "ABCD"
# Tek başına duran şık harfi (A[j], B-ağacı, T.min, D=P/R, A* değil). Kesme işaretli harf ("C'den") de sayılır:
# çoğu içerik olduğu için bu tür soru taşınmaz.
LETTER = re.compile(r"(?<![\w*\[\]\-=/.'’])[A-D](?![\w*\[\]\-=/])")
# Açıklamada şık atfı: harf ya da harf listesi ("A, C ve D") ardından şık/seçenek/yanlış/doğru/ise.
OPTION_REF = re.compile(r"(?<![\w*\[\]\-=/.'’])[A-D](?:\s*,\s*[A-D])*(?:\s+ve\s+[A-D])?"
                        r"(?=\s*(?:şık|seçene|\)|yanlış|doğru|ise\b|de\s+yanlış|da\s+yanlış))")
CONTEXT_TEMPLATE = "Ders içeriği:\n{passage}\n\n{instruction}"
FIELDS = ["id", "key", "source_document", "passage_idx", "task_type", "subtype", "with_context", "instruction",
          "response", "topic", "generation_method", "generation_model", "prompt_version", "prompt_sha",
          "temperature", "top_p", "verified_by", "verified", "judge_model", "token_count", "split"]


def user_content(record: dict[str, Any]) -> str:
    if record["with_context"]:
        return CONTEXT_TEMPLATE.format(passage=record["passage"], instruction=record["instruction"])
    return record["instruction"]


def assign_instruction_splits(records: list[dict[str, Any]], doc_splits: dict[str, str],
                              ratios: dict[str, float], seed: int) -> dict[str, str]:
    """{anahtar: split}. Kaynaklı örnek dokümanının split'ini alır; kaynaksızlar seed'li oranlarla dağıtılır."""
    out = {}
    orphans = []
    for r in records:
        doc = r.get("source_document")
        if doc:
            if doc not in doc_splits:
                raise SystemExit(f"{r['key']}: kaynak doküman {doc} final corpus'ta yok ya da split'i boş.")
            out[r["key"]] = doc_splits[doc]
        else:
            orphans.append(r["key"])
    out.update(assign_splits({"instruction_alan_disi": orphans}, ratios, seed))
    return out


def ngrams(text: str, n: int) -> set[tuple[str, ...]]:
    words = WORD.findall(text.lower())
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def passage_overlap(passage: str, doc_ngrams: set[tuple[str, ...]], n: int) -> float:
    """passage'ın n kelimelik dizilerinden doküman metninde de bulunanların oranı (kaynak işareti, satır sonu ve
    tire farkları birkaç diziyi bozar; silinmiş bir bölümde oran sıfıra iner)."""
    grams = ngrams(passage, n)
    return len(grams & doc_ngrams) / len(grams) if grams else 1.0


def drop_removed_passages(records: list[dict[str, Any]], doc_texts: dict[str, str], n: int,
                          threshold: float) -> tuple[list[dict], list[tuple[str, float]]]:
    """passage'ı final corpus metninde artık bulunmayan örnekleri ayırır. Döner: (kalanlar, [(anahtar, oran)])."""
    doc_grams: dict[str, set] = {}
    kept, dropped = [], []
    for r in records:
        doc, passage = r.get("source_document"), r.get("passage")
        if not doc or not passage:
            kept.append(r)
            continue
        if doc not in doc_grams:
            doc_grams[doc] = ngrams(doc_texts.get(doc, ""), n)
        overlap = passage_overlap(passage, doc_grams[doc], n)
        if overlap < threshold:
            dropped.append((r["key"], overlap))
        else:
            kept.append(r)
    return kept, dropped


def option_ref_spans(quiz: dict[str, Any]) -> list[tuple[int, int]] | None:
    """Açıklamadaki şık atıflarının yerleri. Soruda ya da şıklarda tek başına harf varsa, ya da açıklamada şık
    atfı olmayan bir harf varsa (harf içerik olarak kullanılmış) None: soru güvenle taşınamaz."""
    if any(LETTER.search(text) for text in [quiz["question"], *quiz["options"].values()]):
        return None
    explanation = quiz["explanation"]
    spans = [m.span() for m in OPTION_REF.finditer(explanation)]
    covered = {i for start, end in spans for i in range(start, end)}
    if any(m.start() not in covered for m in LETTER.finditer(explanation)):
        return None
    return spans


def quiz_target(key: str, seed: int) -> str:
    return OPTIONS[int(hashlib.sha256(f"{seed}:quiz:{key}".encode("utf-8")).hexdigest(), 16) % len(OPTIONS)]


def balance_quiz(record: dict[str, Any], seed: int) -> tuple[dict[str, Any], str]:
    """Doğru şıkkı anahtara bağlı hedef harfe taşır. Döner: (kayıt, "moved" | "kept" | "unsafe")."""
    quiz = json.loads(record["response"])
    correct, target = quiz["correct"], quiz_target(record["key"], seed)
    spans = option_ref_spans(quiz)
    if spans is None:
        return record, "unsafe"
    if target == correct:
        return record, "kept"
    swap = {correct: target, target: correct}
    options = dict(quiz["options"])
    options[correct], options[target] = quiz["options"][target], quiz["options"][correct]
    explanation = list(quiz["explanation"])
    for start, end in spans:
        for i in range(start, end):
            explanation[i] = swap.get(explanation[i], explanation[i])
    moved = {"question": quiz["question"], "options": {k: options[k] for k in OPTIONS}, "correct": target,
             "explanation": "".join(explanation)}
    return record | {"response": json.dumps(moved, ensure_ascii=False)}, "moved"


def balance_quizzes(records: list[dict[str, Any]], seed: int) -> tuple[list[dict[str, Any]], Counter]:
    out, outcome = [], Counter()
    for r in records:
        if r["task_type"] == QUIZ_TASK:
            r, result = balance_quiz(r, seed)
            outcome[result] += 1
        out.append(r)
    return out, outcome


def apply_manual_review(records: list[dict[str, Any]], reviews: list[dict[str, Any]]) -> tuple[list[dict], int]:
    """Reddedilenleri çıkarır, onaylananları manuel doğrulanmış işaretler. Döner: (kalanlar, reddedilen sayısı)."""
    decision = {r["key"]: r for r in reviews}
    kept, rejected = [], 0
    for r in records:
        review = decision.get(r["key"])
        if review is None:
            kept.append(r)
        elif review["approved"]:
            kept.append(r | {"verified": True, "verified_by": f"manual:{review['reviewer']}"})
        else:
            rejected += 1
    return kept, rejected


def build(records: list[dict[str, Any]], splits: dict[str, str], count) -> list[dict[str, Any]]:
    out = []
    for i, r in enumerate(sorted(records, key=lambda r: r["key"]), start=1):
        row = r | {"id": f"INS_{i:05d}", "split": splits[r["key"]],
                   "token_count": count(user_content(r)) + count(r["response"])}
        out.append({f: row.get(f) for f in FIELDS})
    return out


def messages(dataset: list[dict[str, Any]], records: list[dict[str, Any]], split: str) -> list[dict[str, Any]]:
    """SFT biçimi. Passage metni instruction_v1.0'da tutulmaz (source_document + passage_idx yeter); bağlamlı
    örneğin kullanıcı mesajı için doğrulanmış kayıttan alınır."""
    passages = {r["key"]: r.get("passage") for r in records}
    return [{"id": r["id"], "messages": [{"role": "user", "content": user_content(r | {"passage": passages[r["key"]]})},
                                         {"role": "assistant", "content": r["response"]}]}
            for r in dataset if r["split"] == split]


def check_leakage(dataset: list[dict[str, Any]], doc_splits: dict[str, str]) -> None:
    """Her kaynak doküman tek kümede ve o küme corpus'taki split'i; id'ler benzersiz."""
    seen: dict[str, set[str]] = {}
    for r in dataset:
        if r["source_document"]:
            seen.setdefault(r["source_document"], set()).add(r["split"])
    bad = {d: s for d, s in seen.items() if s != {doc_splits[d]}}
    if bad:
        raise SystemExit(f"Split sızıntısı: {dict(list(bad.items())[:5])}")
    if len({r["id"] for r in dataset}) != len(dataset):
        raise SystemExit("Aynı id iki kez verilmiş.")


def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description=__doc__.splitlines()[0]))
    parser.add_argument("--allow-pending", action="store_true",
                        help="Yargıç kararı bekleyen örnekler varken de derle (deneme amaçlı)")
    args = parser.parse_args()
    cfg = load_config(args.config)
    logger = setup_logger("11_build_instruction_dataset", cfg)
    seed = set_seed(cfg)
    in_dir, final_dir = resolve_path(cfg, "instruction_dir"), resolve_path(cfg, "final_dir")

    state_path = in_dir / "verify_state.json"
    if not state_path.exists():
        raise SystemExit("verify_state.json yok: önce scripts.10_verify_instructions çalıştırılmalı.")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state["pending"] and not args.allow_pending:
        raise SystemExit(f"{state['pending']} örnek yargıç kararı bekliyor; 10_verify_instructions'ı yeniden "
                         "çalıştırın (ya da deneme için --allow-pending).")

    records = read_jsonl(in_dir / "verified.jsonl")
    if args.limit is not None:
        records = records[:args.limit]
    doc_texts = {d["document_id"]: d["text"] for split in SPLITS for d in read_jsonl(final_dir / f"{split}.jsonl")}
    build_cfg = cfg["instruction"]["build"]
    records, removed = drop_removed_passages(records, doc_texts, build_cfg["passage_ngram"],
                                             build_cfg["min_passage_overlap"])
    drop_exclusions(cfg, "instruction", {r["key"] for r in records} | {k for k, _ in removed}, BUILD_STAGE)
    for key, overlap in removed:
        log_exclusion(cfg, "instruction", key, BUILD_STAGE, "not_grounded",
                      f"passage v1.0 corpus metninde yok (temizlikte silinmiş): {build_cfg['passage_ngram']} "
                      f"kelimelik dizilerin %{overlap * 100:.1f}'i bulundu")
    records, rejected = apply_manual_review(records, read_jsonl(in_dir / MANUAL_REVIEW))
    before = Counter(json.loads(r["response"])["correct"] for r in records if r["task_type"] == QUIZ_TASK)
    records, quiz_outcome = balance_quizzes(records, seed)
    after = Counter(json.loads(r["response"])["correct"] for r in records if r["task_type"] == QUIZ_TASK)
    logger.info("Çoktan seçmeli doğru şık: önce %s, sonra %s | taşınan %d, yerinde kalan %d, harf içerik "
                "olduğu için dokunulmayan %d", dict(sorted(before.items())), dict(sorted(after.items())),
                quiz_outcome["moved"], quiz_outcome["kept"], quiz_outcome["unsafe"])
    registry = load_registry(cfg)
    final = registry[registry["status"] == "final"]
    doc_splits = dict(zip(final["document_id"], final["split"]))
    splits = assign_instruction_splits(records, doc_splits, cfg["split"]["ratios"], seed)
    dataset = build(records, splits, token_counter(load_tokenizer(cfg)))
    check_leakage(dataset, doc_splits)

    final_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(final_dir / DATASET_FILE, dataset)
    for split in SPLITS:
        write_jsonl(final_dir / f"instruction_{split}.jsonl", messages(dataset, records, split))

    by_split = Counter(r["split"] for r in dataset)
    logger.info("Instruction Dataset: %d örnek | split: %s | görev türü: %s | passage'ı silinmiş: %d | "
                "manuel reddedilen: %d", len(dataset), {s: by_split[s] for s in SPLITS},
                dict(Counter(r["task_type"] for r in dataset)), len(removed), rejected)
    log_summary(logger, len(records) + rejected + len(removed), len(dataset), 0, rejected + len(removed))


if __name__ == "__main__":
    main()
