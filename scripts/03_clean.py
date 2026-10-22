"""FAZ 3: data/extracted/ altındaki metinleri kurallarla temizler, data/cleaned/ altına yazar.

Çalıştırma (proje kökünden): python -m scripts.03_clean [--config ...] [--limit N] [--redo]

- Kurallar ve gerekçeleri scripts/utils/text_utils.py içinde (RULES); kod dokümanlarına yalnızca R2.
- reports/cleaning_report.csv: doküman başına kural kural silinen karakter.
- reports/cleaning_rules.md: kural, ne yapar, neden, etkilenen doküman, silinen karakter (rapor CSV'sinden).
- reports/cleaning_examples/: seed'li 20 doküman için <id>_before.txt ve <id>_after.txt.
- Bu adımda doküman elenmez; temizlik sonrası kısa kalanları FAZ 4 (too_short) eler.
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.utils.config import PROJECT_ROOT, add_common_args, load_config, resolve_path, set_seed
from scripts.utils.logging_utils import log_summary, setup_logger
from scripts.utils.registry import (_atomic_write_csv, drop_exclusions, excluded_before, load_registry, reached,
                                    save_registry, stages_from)
from scripts.utils.text_utils import RULES, clean_text, word_counts

RULE_IDS = [rule_id for rule_id, _, _ in RULES]
REPORT_COLUMNS = ["document_id", "source_name", "source_type", "chars_before", "chars_after", "rules_changed",
                  *RULE_IDS]


def project_path(stored: str) -> Path:
    path = Path(stored)
    return path if path.is_absolute() else PROJECT_ROOT / path


def read(stored: str) -> str:
    # newline="": satır sonlarını olduğu gibi oku (CRLF dönüşümü R2'nin işi, sayılabilsin).
    with project_path(stored).open(encoding="utf-8", newline="") as f:
        return f.read()


def build_vocabulary(registry: pd.DataFrame) -> Any:
    """R6 için kelime sıklıkları: çıkarılmış bütün metin dokümanlarından (--limit'ten bağımsız, sonuç değişmesin).

    Yalnızca temizlemeden önce elenenler (indirme/çıkarma) dışarıda: sonraki adımlarda elenenler de sayılır,
    yoksa --redo ile temizlik, pipeline'ı baştan çalıştırmaktan farklı sözlükle yapılırdı.
    """
    rows = registry[(registry["extracted_path"] != "") & (registry["source_type"] != "code")
                    & ~excluded_before(registry, "clean")]
    return word_counts(read(path) for path in rows["extracted_path"])


def tr_number(value: float, decimals: int = 0) -> str:
    """Türkçe sayı biçimi: 1.026.266 ve 13,4 (yalnızca sayıya uygulanır, metne değil)."""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def write_rules_report(report: pd.DataFrame, registry: pd.DataFrame, cfg: dict[str, Any]) -> None:
    """cleaning_rules.md: yalnızca şu an temizlenmiş durumdaki dokümanların kayıtlarından üretilir."""
    current = report[report["document_id"].isin(registry.loc[registry["status"] == "cleaned", "document_id"])]
    lines = ["# Temizleme kuralları", "",
             "`scripts/03_clean.py` tarafından üretilir; elle düzenlemeyin. Kuralların kodu ve gerekçesi:",
             "`scripts/utils/text_utils.py`. Kod dokümanlarına yalnızca R2 uygulanır.", "",
             f"Temizlenen doküman: {len(current)}. Toplam karakter: {tr_number(current['chars_before'].sum())} -> "
             f"{tr_number(current['chars_after'].sum())}.",
             "", "| Kural | Ne yapar | Neden | Etkilenen doküman | Silinen karakter |", "| --- | --- | --- | --- | --- |"]
    for rule_id, what, why in RULES:
        affected = current["rules_changed"].str.split(";").apply(lambda rules, r=rule_id: r in rules).sum()
        lines.append(f"| {rule_id} | {what} | {why} | {affected} | {tr_number(current[rule_id].sum())} |")
    lines += ["", "Silinen karakter nettir: R1'de ligatür açılması metni uzatabilir (eksi değer).", "",
              "## Kaynak bazında", "", "| Kaynak | Doküman | Önce | Sonra | Silinen pay |", "| --- | --- | --- | --- | --- |"]
    for source, grp in current.groupby("source_name"):
        before, after = grp["chars_before"].sum(), grp["chars_after"].sum()
        lines.append(f"| {source} | {len(grp)} | {tr_number(before)} | {tr_number(after)} | "
                     f"%{tr_number((before - after) / before * 100, 1)} |")
    path = resolve_path(cfg, "cleaning_rules")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_examples(registry: pd.DataFrame, cfg: dict[str, Any], seed: int) -> list[str]:
    """Seed'li önce/sonra örnekleri: kod dışı her kaynaktan eşit sayıda (20 / kaynak sayısı)."""
    out_dir = resolve_path(cfg, "cleaning_examples_dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in list(out_dir.glob("*_before.txt")) + list(out_dir.glob("*_after.txt")):
        old.unlink()  # üretilmiş eski örnekler; seçim değişirse eskisi kalmasın
    cleaned = registry[(registry["status"] == "cleaned") & (registry["source_type"] != "code")]
    sources = sorted(cleaned["source_name"].unique())
    total = cfg["clean"]["example_count"]
    rng = random.Random(seed)
    chosen: list[str] = []
    for i, source in enumerate(sources):
        ids = sorted(cleaned.loc[cleaned["source_name"] == source, "document_id"])
        want = total // len(sources) + (1 if i < total % len(sources) else 0)
        chosen += rng.sample(ids, min(want, len(ids)))
    by_id = cleaned.set_index("document_id")
    for document_id in sorted(chosen):
        row = by_id.loc[document_id]
        (out_dir / f"{document_id}_before.txt").write_text(read(row["extracted_path"]), encoding="utf-8", newline="")
        (out_dir / f"{document_id}_after.txt").write_text(read(row["cleaned_path"]), encoding="utf-8", newline="")
    return sorted(chosen)


def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description=__doc__.splitlines()[0]))
    parser.add_argument("--redo", action="store_true", help="Temizlenmiş dokümanları da yeniden temizle")
    args = parser.parse_args()
    cfg = load_config(args.config)
    logger = setup_logger("03_clean", cfg)
    seed = set_seed(cfg)

    registry = load_registry(cfg)
    cleaned_dir = resolve_path(cfg, "cleaned_dir")
    report_path = resolve_path(cfg, "cleaning_report")
    report = (pd.read_csv(report_path, dtype={"document_id": str}, keep_default_na=False)
              .set_index("document_id").to_dict("index") if report_path.exists() else {})

    todo = registry["status"] == "extracted"
    if args.redo:  # ileri adımlara geçmiş ya da ileride elenmiş olanlar da: "cleaned"a döner, sonrakiler yeniden işler
        todo |= reached(registry, "clean")
    pending = registry.index[todo].tolist()
    if args.limit is not None:
        pending = pending[: args.limit]
    drop_exclusions(cfg, "document", set(registry.loc[pending, "document_id"]), stages_from("clean"))
    vocabulary = build_vocabulary(registry)
    logger.info("R6 kelime sözlüğü: %d farklı kelime", len(vocabulary))

    ok = failed = 0
    for idx in pending:
        row = registry.loc[idx]
        try:
            before = read(row["extracted_path"])
            after, removed, changed = clean_text(before, row["source_type"], row["url"], cfg, vocabulary)
        except Exception as exc:  # beklenmeyen hata: doküman atlanır, loglanır, script durmaz
            failed += 1
            logger.error("%s | temizlenemedi: %s: %s", row["document_id"], type(exc).__name__, exc)
            continue
        out = cleaned_dir / row["source_name"] / f"{row['document_id']}.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(after, encoding="utf-8", newline="")
        registry.loc[idx, ["status", "cleaned_path", "exclusion_stage", "exclusion_reason", "exclusion_detail",
                           "split"]] = ["cleaned", out.relative_to(PROJECT_ROOT).as_posix(), "", "", "", ""]
        report[row["document_id"]] = {"source_name": row["source_name"], "source_type": row["source_type"],
                                      "chars_before": len(before), "chars_after": len(after),
                                      "rules_changed": ";".join(r for r in RULE_IDS if r in changed),
                                      **{r: removed.get(r, 0) for r in RULE_IDS}}
        ok += 1

    save_registry(registry, cfg)
    report_df = pd.DataFrame.from_dict(report, orient="index").rename_axis("document_id").reset_index()
    if len(report_df):
        report_df = report_df.sort_values("document_id")[REPORT_COLUMNS]
        _atomic_write_csv(report_df, report_path)
        report_df["rules_changed"] = report_df["rules_changed"].fillna("").astype(str)
        for col in ["chars_before", "chars_after", *RULE_IDS]:
            report_df[col] = report_df[col].astype(int)
        write_rules_report(report_df, registry, cfg)
        examples = write_examples(registry, cfg, seed)
        logger.info("Önce/sonra örnekleri (%d): %s", len(examples), ", ".join(examples))
    log_summary(logger, len(pending), ok, failed, 0)


if __name__ == "__main__":
    main()
