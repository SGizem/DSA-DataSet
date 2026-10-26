"""Pipeline'ı sırasıyla çalıştırır ve teslim dosyalarını denetler.

Çalıştırma (proje kökünden):
    python -m scripts.run_all [--config ...] [--redo] [--with-instruction]
    python -m scripts.run_all --check-deliverables

- Varsayılan: 01_download -> 08_statistics. Bir adım hata verirse durur.
- --redo: 02, 03 ve 04'ü --redo ile çalıştırır (daha önce işlenmiş dokümanlar da baştan işlenir). 05-08 her
  çalıştırmada bütün dokümanları zaten yeniden işler. Depo `data/registry.csv`'yi işlenmiş hâliyle taşıyor,
  ara dosyalar (`data/extracted/`, `data/cleaned/`) ise depoda yok; işlenmiş görünen bir dokümanın ara dosyası
  eksikse (temiz bir kopya) --redo kendiliğinden açılır.
- --with-instruction: ardından 09 -> 11 ve istatistikler için yeniden 08. 09 günlük kota dolunca durur;
  o durumda 10 yargıç kararı bekleyen örnek bırakır ve 11 derlemeyi reddeder (run_all da durur).
- Kalibrasyon (04/05 --calibrate) ve manuel kalite kontrolü (12, 13) run_all dışındadır: insan kararı ister.
- --check-deliverables: rehber §15'teki teslim dosyalarının varlığı ve otomatik bütünlük
  kontrolleri (rehber §12: boş metin, benzersiz id, eksik kaynak, uzunluk, bozuk karakter, split sızıntısı).
"""
from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from typing import Any

import pandas as pd

from scripts.utils.config import PROJECT_ROOT, add_common_args, load_config, resolve_path
from scripts.utils.llm import read_jsonl
from scripts.utils.logging_utils import setup_logger

CORPUS_STEPS = ["01_download", "02_extract", "03_clean", "04_filter", "05_deduplicate", "06_split",
                "07_token_count", "08_statistics"]
INSTRUCTION_STEPS = ["09_generate_instructions", "10_verify_instructions", "11_build_instruction_dataset",
                     "08_statistics"]
REDO_STEPS = {"02_extract", "03_clean", "04_filter"}
SPLITS = ["train", "validation", "test"]
DELIVERABLES = [
    "data/final/train.jsonl", "data/final/validation.jsonl", "data/final/test.jsonl",
    "data/final/instruction_v1.0.jsonl", "data/final/instruction_train.jsonl",
    "data/final/instruction_validation.jsonl", "data/final/instruction_test.jsonl",
    "reports/statistics.md", "reports/exclusions.csv", "reports/cleaning_rules.md",
    "reports/manual_qc_corpus.csv", "reports/manual_qc_instruction.csv", "reports/quality_report.md",
    "config/sources.csv", "requirements.txt", "README.md", "DATASET_CARD.md", "INSTRUCTION_CARD.md", "experiments.md",
]


def check_thresholds(cfg: dict[str, Any]) -> None:
    missing = [name for name, value in [("filter.domain_score_threshold", cfg["filter"].get("domain_score_threshold")),
                                        ("dedup.jaccard_threshold", cfg["dedup"].get("jaccard_threshold"))]
               if value is None]
    if missing:
        raise SystemExit(f"Kalibrasyon eşiği boş: {', '.join(missing)}. Önce 04_filter --calibrate / "
                         "05_deduplicate --calibrate ile etiketleyip eşiği config.yaml'a yazın.")


def missing_intermediates(registry: pd.DataFrame) -> list[str]:
    """İşlenmiş görünen (extracted_path / cleaned_path dolu) ama ara dosyası diskte olmayan dokümanlar."""
    missing = []
    for _, row in registry.iterrows():
        for col in ("extracted_path", "cleaned_path"):
            path = row.get(col, "")
            if path and not (PROJECT_ROOT / path).exists():
                missing.append(row["document_id"])
                break
    return missing


def run_steps(steps: list[str], config: str, redo: bool, logger) -> None:
    for step in steps:
        cmd = [sys.executable, "-m", f"scripts.{step}", "--config", config]
        if redo and step in REDO_STEPS:
            cmd.append("--redo")
        logger.info("Çalıştırılıyor: %s", " ".join(cmd[2:]))
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        if result.returncode != 0:
            raise SystemExit(f"{step} hata verdi (çıkış kodu {result.returncode}); pipeline durdu.")


# ---------------------------------------------------------------------------------------------------
# Teslim denetimi
# ---------------------------------------------------------------------------------------------------
def corpus_problems(cfg: dict[str, Any]) -> list[str]:
    noise_ratio = importlib.import_module("scripts.04_filter").noise_ratio
    final_dir = resolve_path(cfg, "final_dir")
    problems, seen = [], {}
    min_chars = cfg["filter"]["min_chars"]
    registry = pd.read_csv(resolve_path(cfg, "registry"), dtype=str, keep_default_na=False)
    source_type = dict(zip(registry["document_id"], registry["source_type"]))
    for split in SPLITS:
        for r in read_jsonl(final_dir / f"{split}.jsonl"):
            doc = r.get("document_id")
            if doc in seen:
                problems.append(f"{doc} hem {seen[doc]} hem {split} içinde")
            seen[doc] = split
            if not str(r.get("text", "")).strip():
                problems.append(f"{doc}: boş metin")
            if not r.get("source") or not r.get("url"):
                problems.append(f"{doc}: kaynak ya da url eksik")
            limit = min_chars["code"] if source_type.get(doc) == "code" else min_chars["prose"]
            if len(r.get("text", "")) < limit:
                problems.append(f"{doc}: {len(r.get('text', ''))} karakter < {limit}")
            if noise_ratio(r.get("text", "")) > cfg["filter"]["max_noise_ratio"]:
                problems.append(f"{doc}: bozuk karakter oranı sınırın üstünde")
            if r.get("split") != split:
                problems.append(f"{doc}: split alanı {r.get('split')} ama {split}.jsonl içinde")
    final = registry[registry["status"] == "final"]
    if set(seen) != set(final["document_id"]):
        problems.append(f"final dosyalar ({len(seen)}) ile registry final ({len(final)}) farklı")
    return problems


def instruction_problems(cfg: dict[str, Any]) -> list[str]:
    final_dir = resolve_path(cfg, "final_dir")
    data = read_jsonl(final_dir / "instruction_v1.0.jsonl")
    problems = []
    registry = pd.read_csv(resolve_path(cfg, "registry"), dtype=str, keep_default_na=False)
    final = registry[registry["status"] == "final"]
    doc_split = dict(zip(final["document_id"], final["split"]))
    ids = [r["id"] for r in data]
    if len(set(ids)) != len(ids):
        problems.append("instruction_v1.0: aynı id birden çok kez")
    v = cfg["instruction"]["verify"]
    # Bir örneğin üst sınırı: passage + talimat + cevap sınırları ve şablonun birkaç token'ı.
    max_tokens = cfg["instruction"]["passage_tokens"]["max"] + v["instruction_tokens"]["max"] + v["response_tokens"]["max"] + 10
    for r in data:
        if not r["instruction"].strip() or not r["response"].strip():
            problems.append(f"{r['id']}: boş talimat ya da cevap")
        if r["subtype"] != "alan_disi" and not r["source_document"]:
            problems.append(f"{r['id']}: kaynak doküman eksik")
        if r["source_document"] and doc_split.get(r["source_document"]) != r["split"]:
            problems.append(f"{r['id']}: split {r['split']} ama kaynak doküman {doc_split.get(r['source_document'])}")
        if r["task_type"] == "coktan_secmeli_soru_uretimi":
            try:
                quiz = json.loads(r["response"])
                assert sorted(quiz["options"]) == list("ABCD") and quiz["correct"] in quiz["options"]
            except Exception:  # noqa: BLE001 - herhangi bir yapı hatası
                problems.append(f"{r['id']}: çoktan seçmeli cevap geçersiz")
        if not r.get("token_count") or r["token_count"] > max_tokens:
            problems.append(f"{r['id']}: token_count eksik ya da sınırın üstünde")
    by_split = {s: {m["id"] for m in read_jsonl(final_dir / f"instruction_{s}.jsonl")} for s in SPLITS}
    for s in SPLITS:
        expected = {r["id"] for r in data if r["split"] == s}
        if by_split[s] != expected:
            problems.append(f"instruction_{s}.jsonl id'leri instruction_v1.0 ile uyuşmuyor")
    return problems


def manual_review_problems(labels: pd.DataFrame, checks: list[str], data: list[dict[str, Any]]) -> list[str]:
    """Manuel etiketler veri setine yansımış mı: onaylanan örnek sette ve manual işaretli, reddedilen sette yok."""
    by_key = {r["key"]: r for r in data}
    problems = []
    for _, row in labels.iterrows():
        approved = all(row[c] == "1" for c in checks)
        record = by_key.get(row["key"])
        if approved and (record is None or not str(record.get("verified_by", "")).startswith("manual:")):
            problems.append(f"{row['key']}: onaylı ama sette manuel onaylı değil")
        if not approved and record is not None:
            problems.append(f"{row['key']}: reddedildi ama hâlâ sette")
    return problems


def check_deliverables(cfg: dict[str, Any]) -> int:
    failed = 0
    print("Teslim dosyaları:")
    for rel in DELIVERABLES:
        ok = (PROJECT_ROOT / rel).exists()
        failed += not ok
        print(f"  [{'OK' if ok else 'YOK'}] {rel}")
    for name, func, needs in [("Domain corpus", corpus_problems, "data/final/train.jsonl"),
                              ("Instruction dataset", instruction_problems, "data/final/instruction_v1.0.jsonl")]:
        if not (PROJECT_ROOT / needs).exists():
            continue
        problems = func(cfg)
        failed += bool(problems)
        print(f"{name} bütünlük kontrolleri: {'OK' if not problems else f'{len(problems)} sorun'}")
        for p in problems[:20]:
            print(f"  - {p}")
    for rel, checks in [(cfg["manual_qc"]["corpus_csv"], "corpus"), (cfg["manual_qc"]["instruction_csv"], "instruction")]:
        path = PROJECT_ROOT / rel
        if path.exists():
            qc = importlib.import_module("scripts.12_sample_for_manual_qc")
            cols = qc.CORPUS_CHECKS if checks == "corpus" else qc.INSTRUCTION_CHECKS
            df = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
            empty = int((df[cols] == "").any(axis=1).sum())
            failed += bool(empty)
            print(f"Manuel kontrol ({checks}): {'OK' if not empty else f'{empty}/{len(df)} satır doldurulmamış'}")
            final_set = resolve_path(cfg, "final_dir") / "instruction_v1.0.jsonl"
            if checks == "instruction" and not empty and final_set.exists():
                problems = manual_review_problems(df, cols, read_jsonl(final_set))
                failed += bool(problems)
                print("Manuel kararlar veri setine yansımış: " + ("OK" if not problems else
                      f"{len(problems)} sorun (etiket değiştiyse `python -m scripts.13_qc_report "
                      "--reviewer-name \"<ad>\"` yeniden çalıştırılmalı)"))
                for p in problems[:20]:
                    print(f"  - {p}")
    print("SONUÇ:", "hepsi tamam" if not failed else f"{failed} eksik/sorun")
    return failed


def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description=__doc__.splitlines()[0]))
    parser.add_argument("--redo", action="store_true", help="02-04'ü --redo ile çalıştır")
    parser.add_argument("--with-instruction", action="store_true", help="Ardından 09-11 ve 08")
    parser.add_argument("--check-deliverables", action="store_true", help="Yalnızca teslim denetimi")
    args = parser.parse_args()
    cfg = load_config(args.config)
    if args.check_deliverables:
        raise SystemExit(1 if check_deliverables(cfg) else 0)
    logger = setup_logger("run_all", cfg)
    check_thresholds(cfg)
    redo = args.redo
    registry_path = resolve_path(cfg, "registry")
    if not redo and registry_path.exists():
        missing = missing_intermediates(pd.read_csv(registry_path, dtype=str, keep_default_na=False))
        if missing:
            logger.info("%d dokümanın ara dosyası yok (ör. %s): 02-04 --redo ile baştan çalışacak.",
                        len(missing), missing[0])
            redo = True
    run_steps(CORPUS_STEPS, args.config, redo, logger)
    if args.with_instruction:
        run_steps(INSTRUCTION_STEPS, args.config, False, logger)
    logger.info("Pipeline tamamlandı.")


if __name__ == "__main__":
    main()
