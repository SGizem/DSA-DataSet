"""FAZ 9: Manuel kalite kontrolü için seed'li örneklem ve okuma dosyaları üretir.

Çalıştırma (proje kökünden):
    python -m scripts.12_sample_for_manual_qc [--config ...] [--only corpus|instruction] [--force]

(a) Corpus: final dokümanlardan config.manual_qc.corpus_size doküman, kaynağa göre orantılı tabakalı (her kaynaktan
    en az min_per_source) -> reports/manual_qc_corpus.csv. Her doküman için reports/manual_qc_view/<id>.txt:
    metadata, metnin başı, ortası ve sonu (header/footer kalıntısı sayfa geçişlerinde ve sonda görülür).
(b) Instruction: instruction_v1.0'dan config.manual_qc.instruction_size örnek, görev türüne göre orantılı tabakalı
    (her türden en az min_per_task) -> reports/manual_qc_instruction.csv (passage metni dahil) ve okunması kolay
    reports/manual_qc_instruction_view.md.

Doldurulacak sütunlar 1 (evet) / 0 (hayır). Corpus: readable, in_domain, extraction_ok, header_footer_clean,
no_broken_chars, metadata_ok. Instruction: instruction_clear, response_correct, grounded_in_source,
answers_instruction, task_type_ok. notes serbest metin.
Doldurulmaya başlanmış bir CSV'nin üzerine yazılmaz (--force gerekir): elle yapılan iş kaybolmasın.
"""
from __future__ import annotations

import argparse
import json
import random
from typing import Any

import pandas as pd

from scripts.utils.config import PROJECT_ROOT, add_common_args, load_config, resolve_path, set_seed
from scripts.utils.llm import read_jsonl
from scripts.utils.logging_utils import log_summary, setup_logger
from scripts.utils.registry import load_registry

SPLITS = ["train", "validation", "test"]
CORPUS_CHECKS = ["readable", "in_domain", "extraction_ok", "header_footer_clean", "no_broken_chars", "metadata_ok"]
INSTRUCTION_CHECKS = ["instruction_clear", "response_correct", "grounded_in_source", "answers_instruction",
                      "task_type_ok"]
VIEW_HEAD, VIEW_MIDDLE, VIEW_TAIL = 1500, 700, 500  # okuma dosyasındaki karakter sayıları


def rel(path) -> str:
    """Proje köküne göre yol (CSV'de ve logda); kökün dışındaysa olduğu gibi."""
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def allocate(sizes: dict[str, int], total: int, minimum: int) -> dict[str, int]:
    """Gruplara orantılı pay (en büyük kalan yöntemi); her grup en az min(minimum, grup boyu) alır."""
    total = min(total, sum(sizes.values()))
    alloc = {g: min(minimum, s) for g, s in sizes.items()}
    rest = total - sum(alloc.values())
    if rest < 0:
        raise SystemExit(f"Örneklem {total} gruplara en az {minimum} vermeye yetmiyor.")
    room = {g: sizes[g] - alloc[g] for g in sizes}
    pool = sum(room.values())
    if pool and rest:
        exact = {g: rest * room[g] / pool for g in sizes}
        for g in sizes:
            alloc[g] += int(exact[g])
        left = total - sum(alloc.values())
        for g in sorted(sizes, key=lambda g: (-(exact[g] - int(exact[g])), g))[:left]:
            alloc[g] += 1
    return alloc


def stratified_sample(items: list[dict[str, Any]], key: str, total: int, minimum: int, seed: int,
                      id_field: str) -> list[dict[str, Any]]:
    groups: dict[str, list] = {}
    for item in sorted(items, key=lambda x: x[id_field]):
        groups.setdefault(item[key], []).append(item)
    alloc = allocate({g: len(v) for g, v in groups.items()}, total, minimum)
    chosen = []
    for g in sorted(groups):
        chosen += random.Random(f"{seed}:qc:{g}").sample(groups[g], alloc[g])
    return sorted(chosen, key=lambda x: x[id_field])


def already_filled(path, checks: list[str]) -> bool:
    if not path.exists():
        return False
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    return bool(df[[c for c in checks if c in df.columns]].ne("").any().any()) or bool(df.get("notes", pd.Series(dtype=str)).ne("").any())


def corpus_view(record: dict[str, Any], meta: dict[str, str]) -> str:
    text = record["text"]
    header = "\n".join(f"{k}: {meta.get(k, '')}" for k in ["document_id", "title", "source_name", "url", "language",
                                                          "document_type", "publication_year", "subtopic", "split",
                                                          "char_count", "token_count"])
    parts = [header, "", f"===== BAŞ (ilk {VIEW_HEAD} karakter) =====", text[:VIEW_HEAD]]
    if len(text) > VIEW_HEAD + VIEW_TAIL:
        mid = len(text) // 2
        parts += ["", f"===== ORTA ({mid}. karakterden {VIEW_MIDDLE} karakter) =====", text[mid:mid + VIEW_MIDDLE],
                  "", f"===== SON (son {VIEW_TAIL} karakter) =====", text[-VIEW_TAIL:]]
    return "\n".join(parts) + "\n"


def sample_corpus(cfg: dict[str, Any], seed: int, force: bool, logger, refresh: bool = False) -> int:
    q = cfg["manual_qc"]
    out = PROJECT_ROOT / q["corpus_csv"]
    if already_filled(out, CORPUS_CHECKS) and not force and not refresh:
        raise SystemExit(f"{out} doldurulmaya başlanmış; üzerine yazmak için --force.")
    registry = load_registry(cfg)
    meta = {r["document_id"]: r for r in registry[registry["status"] == "final"].to_dict("records")}
    records = [r for s in SPLITS for r in read_jsonl(resolve_path(cfg, "final_dir") / f"{s}.jsonl")]
    for r in records:
        r["source_name"] = meta[r["document_id"]]["source_name"]
    if refresh:
        # Aynı dokümanlar, güncel metin: düzeltmelerden sonra aynı örneklem yeniden incelenir. Kontrol sütunları
        # boşaltılır (yeni metin yeniden işaretlenecek), eski işaretler round1 sütunlarında kalır.
        old = pd.read_csv(out, encoding="utf-8-sig", dtype=str, keep_default_na=False)
        missing = set(old["document_id"]) - set(meta)
        if missing:
            raise SystemExit(f"Örneklemdeki dokümanlar artık final değil: {sorted(missing)}")
        by_id = {r["document_id"]: r for r in records}
        chosen = [by_id[d] for d in old["document_id"]]
    else:
        chosen = stratified_sample(records, "source_name", q["corpus_size"], q["min_per_source"], seed, "document_id")
    view_dir = PROJECT_ROOT / q["view_dir"]
    view_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in chosen:
        m = meta[r["document_id"]]
        view = view_dir / f"{r['document_id']}.txt"
        view.write_text(corpus_view(r, m), encoding="utf-8")
        rows.append({"document_id": r["document_id"], "source_name": m["source_name"], "title": m["title"],
                     "language": m["language"], "document_type": m["document_type"],
                     "publication_year": m["publication_year"], "subtopic": m["subtopic"], "url": m["url"],
                     "view_file": rel(view), **{c: "" for c in CORPUS_CHECKS},
                     "notes": ""})
    pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8-sig")
    by_source = pd.Series([r["source_name"] for r in rows]).value_counts().to_dict()
    logger.info("Corpus QC örneklemi: %d doküman -> %s | kaynaklar: %s", len(rows), rel(out), by_source)
    return len(rows)


def show_response(record: dict[str, Any]) -> str:
    if record["task_type"] != "coktan_secmeli_soru_uretimi":
        return record["response"]
    quiz = json.loads(record["response"])
    options = "\n".join(f"{k}) {quiz['options'][k]}" for k in "ABCD")
    return f"Soru: {quiz['question']}\n{options}\nDoğru şık: {quiz['correct']}\nAçıklama: {quiz['explanation']}"


def sample_instruction(cfg: dict[str, Any], seed: int, force: bool, logger) -> int:
    q = cfg["manual_qc"]
    out = PROJECT_ROOT / q["instruction_csv"]
    if already_filled(out, INSTRUCTION_CHECKS) and not force:
        raise SystemExit(f"{out} doldurulmaya başlanmış; üzerine yazmak için --force.")
    path = resolve_path(cfg, "final_dir") / "instruction_v1.0.jsonl"
    if not path.exists():
        raise SystemExit("instruction_v1.0.jsonl yok: önce 11_build_instruction_dataset.")
    data = read_jsonl(path)
    passages = {(p["document_id"], p["passage_idx"]): p for p in read_jsonl(resolve_path(cfg, "instruction_dir") / "passages.jsonl")}
    chosen = stratified_sample(data, "task_type", q["instruction_size"], q["min_per_task"], seed, "key")
    rows, view = [], ["# Instruction manuel kontrolü — okuma dosyası", "",
                      f"`python -m scripts.12_sample_for_manual_qc` üretti. {len(chosen)} örnek, görev türüne göre "
                      f"tabakalı, seed {seed}. İşaretlemeler `{q['instruction_csv']}` dosyasına (no sütunu bu "
                      "dosyadaki numara).", "",
                      "Kontroller (1 = evet, 0 = hayır): instruction_clear (talimat anlaşılır mı), response_correct "
                      "(cevap doğru mu), grounded_in_source (cevap kaynak metinle tutarlı mı), answers_instruction "
                      "(cevap talimatı karşılıyor mu), task_type_ok (örnek görev türüne uyuyor mu).", ""]
    for no, r in enumerate(chosen, start=1):
        p = passages.get((r["source_document"], r["passage_idx"])) if r["source_document"] else None
        passage = p["text"] if p else ""
        title = p["title"] if p else ""
        rows.append({"no": no, "id": r["id"], "key": r["key"], "task_type": r["task_type"], "subtype": r["subtype"],
                     "with_context": r["with_context"], "source_document": r["source_document"] or "", "title": title,
                     "passage": passage, "instruction": r["instruction"], "response": show_response(r),
                     **{c: "" for c in INSTRUCTION_CHECKS}, "notes": ""})
        sub = f" / {r['subtype']}" if r["subtype"] else ""
        origin = f"{r['source_document']} — {title}, passage {r['passage_idx']}" if p else f"kaynak yok (alan dışı konu: {r.get('topic')})"
        view += [f"## {no}. {r['task_type']}{sub} — {'bağlamlı' if r['with_context'] else 'bağlamsız'} ({r['key']})", "",
                 f"Kaynak: {origin}", ""]
        if passage:
            view += ["<details><summary>Kaynak metin (passage)</summary>", "", "```text", passage, "```", "", "</details>", ""]
        view += ["**Talimat:**", "", r["instruction"], "", "**Cevap:**", "", show_response(r), ""]
    pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8-sig")
    (PROJECT_ROOT / q["instruction_view"]).write_text("\n".join(view), encoding="utf-8")
    by_type = pd.Series([r["task_type"] for r in rows]).value_counts().to_dict()
    logger.info("Instruction QC örneklemi: %d örnek -> %s | türler: %s", len(rows), rel(out), by_type)
    return len(rows)


def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description=__doc__.splitlines()[0]))
    parser.add_argument("--only", choices=["corpus", "instruction"], default=None)
    parser.add_argument("--force", action="store_true", help="Doldurulmaya başlanmış CSV'nin üzerine yaz")
    parser.add_argument("--refresh-corpus", action="store_true",
                        help="Corpus örneklemindeki aynı dokümanların okuma dosyalarını güncel metinle yeniden yaz; "
                             "kontrol sütunları yeni tur için boşaltılır")
    args = parser.parse_args()
    cfg = load_config(args.config)
    logger = setup_logger("12_sample_for_manual_qc", cfg)
    seed = set_seed(cfg)
    total = 0
    if args.only in (None, "corpus"):
        total += sample_corpus(cfg, seed, args.force, logger, refresh=args.refresh_corpus)
    if args.only in (None, "instruction"):
        total += sample_instruction(cfg, seed, args.force, logger)
    log_summary(logger, total, total, 0, 0)


if __name__ == "__main__":
    main()
