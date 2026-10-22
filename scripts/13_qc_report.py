"""FAZ 9: Doldurulmuş manuel kontrol CSV'lerinden kalite kontrol raporunu üretir ve instruction setine uygular.

Çalıştırma (proje kökünden):
    python -m scripts.13_qc_report --reviewer-name "<ad>" [--config ...] [--allow-partial] [--no-rebuild]

1. reports/manual_qc_corpus.csv ve reports/manual_qc_instruction.csv okunur. Kontrol sütunları 1 ya da 0 olmalı;
   boş satır varsa script durur (--allow-partial ile yalnızca dolu satırlar sayılır).
2. Kontrol bazında başarı oranları, kaynak / görev türü bazında tamamen başarılı oranı ve başarısız kontrol
   sayıları (hata türleri) -> reports/quality_report.md (rehber §15: kalite kontrol raporu).
   manual_qc.corpus_round1_csv varsa (aynı dokümanların önceki sürümdeki incelemesi) iki tur yan yana yazılır.
3. Instruction: beş kontrolün hepsi 1 olan örnekler onaylanır (verified=true, verified_by="manual:<ad>");
   herhangi biri 0 olanlar manual_rejected sebebiyle elenir (reports/exclusions.csv, aşama manual_qc).
   Kararlar data/instruction/manual_review.jsonl'e yazılır; ardından 11_build_instruction_dataset ve
   08_statistics yeniden çalıştırılır (--no-rebuild ile çalıştırılmaz).
"""
from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from scripts.utils.config import PROJECT_ROOT, add_common_args, load_config, resolve_path
from scripts.utils.llm import write_jsonl
from scripts.utils.logging_utils import log_summary, setup_logger
from scripts.utils.registry import drop_exclusions, log_exclusion

qc = importlib.import_module("scripts.12_sample_for_manual_qc")
STAGE = "manual_qc"


def pct(part: int, whole: int) -> str:
    return f"%{100 * part / whole:.1f}".replace(".", ",") if whole else "—"


def table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    return ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(str(c) for c in row) + " |" for row in rows), ""]


def load_filled(path, checks: list[str], allow_partial: bool) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"{path} yok: önce scripts.12_sample_for_manual_qc.")
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    for c in checks:
        df[c] = df[c].str.strip()
    invalid = df[~df[checks].isin(["0", "1", ""]).all(axis=1)]
    if len(invalid):
        raise SystemExit(f"{path.name}: kontrol sütunlarında 0/1 dışında değer var (satır {list(invalid.index[:5] + 2)}).")
    filled = df[checks].ne("").all(axis=1)
    partial = df[checks].ne("").any(axis=1) & ~filled
    if partial.any():
        raise SystemExit(f"{path.name}: bazı kontrolleri boş bırakılmış satırlar var (satır {list(df.index[partial][:5] + 2)}).")
    if not filled.all() and not allow_partial:
        raise SystemExit(f"{path.name}: {int((~filled).sum())}/{len(df)} satır doldurulmamış. Hepsini doldurun ya da "
                         "--allow-partial ile yalnızca dolu satırları sayın.")
    out = df[filled].copy()
    for c in checks:
        out[c] = out[c].astype(int)
    return out


def check_rows(df: pd.DataFrame, checks: list[str]) -> list[list[Any]]:
    rows = [[c, f"{int(df[c].sum())}/{len(df)}", pct(int(df[c].sum()), len(df))] for c in checks]
    all_ok = int(df[checks].all(axis=1).sum())
    return rows + [["**hepsi başarılı**", f"{all_ok}/{len(df)}", pct(all_ok, len(df))]]


def group_rows(df: pd.DataFrame, by: str, checks: list[str]) -> list[list[Any]]:
    rows = []
    for g, part in df.groupby(by):
        ok = int(part[checks].all(axis=1).sum())
        failed = {c: int((part[c] == 0).sum()) for c in checks if (part[c] == 0).any()}
        rows.append([g, len(part), f"{ok} ({pct(ok, len(part))})", ", ".join(f"{c} {n}" for c, n in failed.items()) or "—"])
    return rows


def failures(df: pd.DataFrame, id_col: str, checks: list[str], extra: str) -> list[list[Any]]:
    bad = df[~df[checks].all(axis=1)]
    return [[r[id_col], r[extra], ", ".join(c for c in checks if r[c] == 0), r.get("notes", "") or "—"]
            for _, r in bad.iterrows()]


def round_rows(before: pd.DataFrame, after: pd.DataFrame, checks: list[str]) -> list[list[Any]]:
    """Aynı dokümanların iki inceleme turu: kontrol başına başarılı sayısı ve oranı."""
    if set(before["document_id"]) != set(after["document_id"]):
        raise SystemExit("Corpus 1. tur ve 2. tur farklı dokümanları içeriyor; turlar karşılaştırılamaz.")
    rows = []
    for c in checks + ["hepsi"]:
        b = int(before[checks].all(axis=1).sum()) if c == "hepsi" else int(before[c].sum())
        a = int(after[checks].all(axis=1).sum()) if c == "hepsi" else int(after[c].sum())
        name = "**hepsi başarılı**" if c == "hepsi" else c
        rows.append([name, f"{b}/{len(before)} ({pct(b, len(before))})", f"{a}/{len(after)} ({pct(a, len(after))})"])
    return rows


def corpus_section(df: pd.DataFrame, round1: pd.DataFrame | None = None) -> list[str]:
    checks = qc.CORPUS_CHECKS
    lines = ["## Domain corpus", "", f"İncelenen doküman: {len(df)}", ""]
    if round1 is not None:
        lines += ["### İki inceleme turu", "",
                  "Aynı dokümanları önce corpus v0.9'da inceledim, bulduğum hataları pipeline'da düzelttim, sonra "
                  "v1.0'da yeniden inceledim. Aşağıdaki diğer tablolar 2. turun (v1.0) sonuçlarıdır.", ""]
        lines += table(["Kontrol", "1. tur (v0.9)", "2. tur (v1.0)"], round_rows(round1, df, checks))
    lines += ["### Kontrol bazında başarı", ""] + table(["Kontrol", "Başarılı", "Oran"], check_rows(df, checks))
    lines += ["### Kaynak bazında", ""] + table(["Kaynak", "İncelenen", "Hepsi başarılı", "Başarısız kontroller"],
                                                 group_rows(df, "source_name", checks))
    bad = failures(df, "document_id", checks, "source_name")
    lines += ["### Hatalı dokümanlar", ""]
    lines += table(["Doküman", "Kaynak", "Başarısız kontroller", "Not"], bad) if bad else ["Hatalı doküman yok.", ""]
    return lines


def instruction_section(df: pd.DataFrame) -> list[str]:
    checks = qc.INSTRUCTION_CHECKS
    lines = ["## Instruction dataset", "", f"İncelenen örnek: {len(df)}", ""]
    lines += ["### Kontrol bazında başarı", ""] + table(["Kontrol", "Başarılı", "Oran"], check_rows(df, checks))
    lines += ["### Görev türü bazında", ""] + table(["Görev türü", "İncelenen", "Hepsi başarılı", "Başarısız kontroller"],
                                                     group_rows(df, "task_type", checks))
    bad = failures(df, "key", checks, "task_type")
    lines += ["### Setten çıkarılan örnekler", ""]
    lines += table(["Örnek", "Görev türü", "Başarısız kontroller", "Not"], bad) if bad else ["Çıkarılan örnek yok.", ""]
    return lines


def apply_instruction_review(cfg: dict[str, Any], df: pd.DataFrame, reviewer: str) -> tuple[int, int]:
    checks = qc.INSTRUCTION_CHECKS
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    reviews, rejected = [], 0
    drop_exclusions(cfg, "instruction", set(df["key"]), STAGE)
    for _, r in df.sort_values("key").iterrows():
        approved = bool(r[checks].all())
        reviews.append({"key": r["key"], "approved": approved, "reviewer": reviewer, "timestamp": stamp})
        if not approved:
            failed = ", ".join(c for c in checks if r[c] == 0)
            note = f"; not: {r['notes']}" if r.get("notes") else ""
            log_exclusion(cfg, "instruction", r["key"], STAGE, "manual_rejected", f"başarısız: {failed}{note}"[:300])
            rejected += 1
    write_jsonl(resolve_path(cfg, "instruction_dir") / "manual_review.jsonl", reviews)
    return len(reviews) - rejected, rejected


def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description=__doc__.splitlines()[0]))
    parser.add_argument("--reviewer-name", required=True, help="Manuel kontrolü yapan kişi (verified_by'a yazılır)")
    parser.add_argument("--allow-partial", action="store_true", help="Doldurulmamış satırları sayma")
    parser.add_argument("--no-rebuild", action="store_true", help="11 ve 08'i yeniden çalıştırma")
    args = parser.parse_args()
    cfg = load_config(args.config)
    logger = setup_logger("13_qc_report", cfg)
    q = cfg["manual_qc"]
    corpus = load_filled(PROJECT_ROOT / q["corpus_csv"], qc.CORPUS_CHECKS, args.allow_partial)
    round1_path = PROJECT_ROOT / q["corpus_round1_csv"] if q.get("corpus_round1_csv") else None
    round1 = (load_filled(round1_path, qc.CORPUS_CHECKS, args.allow_partial)
              if round1_path is not None and round1_path.exists() else None)
    instruction = load_filled(PROJECT_ROOT / q["instruction_csv"], qc.INSTRUCTION_CHECKS, args.allow_partial)

    approved, rejected = apply_instruction_review(cfg, instruction, args.reviewer_name)
    lines = ["# Kalite kontrol raporu", "",
             f"`python -m scripts.13_qc_report` üretir. İnceleyen: {args.reviewer_name}. Tarih: "
             f"{datetime.now().strftime('%d.%m.%Y')}. Örneklemi `scripts/12_sample_for_manual_qc.py` seed "
             f"{cfg['project']['random_seed']} ile çekti: corpus kaynağa, instruction seti görev türüne göre orantılı "
             "tabakalı. Her kontrol 1 (başarılı) ya da 0 (başarısız).", "",
             "Kontrol tanımları:", "",
             "- Corpus: readable (metin okunabiliyor), in_domain (veri yapıları ve algoritmalar alanında), "
             "extraction_ok (metin eksiksiz ve doğru sırada çıkarılmış), header_footer_clean (başlık/altbilgi, sayfa "
             "numarası, menü kalıntısı yok), no_broken_chars (bozuk karakter yok), metadata_ok (başlık, kaynak, dil, "
             "yıl, alt konu doğru).",
             "- Instruction: instruction_clear (talimat anlaşılır), response_correct (cevap doğru), grounded_in_source "
             "(cevap kaynak metinle tutarlı), answers_instruction (cevap talimatı karşılıyor), task_type_ok (örnek "
             "görev türüne uyuyor).", ""]
    lines += corpus_section(corpus, round1) + instruction_section(instruction)
    lines += ["## Uygulanan işlem", "",
              f"Instruction setinde incelenen {len(instruction)} örnekten {approved} tanesi onaylandı "
              f"(verified=true, verified_by=manual:{args.reviewer_name}); {rejected} tanesi manual_rejected sebebiyle "
              "setten çıkarıldı (reports/exclusions.csv, aşama manual_qc). Corpus'ta inceleme yalnızca ölçüm için; "
              "hatalı dokümanların listesi yukarıda.", ""]
    report = PROJECT_ROOT / q["quality_report"]
    report.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Kalite raporu: %s | corpus %d doküman, hepsi başarılı %s | instruction %d örnek, onay %d, ret %d",
                qc.rel(report), len(corpus), pct(int(corpus[qc.CORPUS_CHECKS].all(axis=1).sum()), len(corpus)),
                len(instruction), approved, rejected)

    if not args.no_rebuild:
        for script in ("scripts.11_build_instruction_dataset", "scripts.08_statistics"):
            logger.info("Çalıştırılıyor: %s", script)
            subprocess.run([sys.executable, "-m", script, "--config", args.config], check=True, cwd=PROJECT_ROOT)
    log_summary(logger, len(corpus) + len(instruction), len(corpus) + approved, 0, rejected)


if __name__ == "__main__":
    main()
