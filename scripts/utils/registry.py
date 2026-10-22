"""registry.csv (tek doğruluk kaynağı) ve exclusions.csv okuma/yazma.

Yazma atomiktir: geçici dosyaya yaz, sonra `os.replace` ile yer değiştir.
"""
from __future__ import annotations

import csv
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.utils.config import resolve_path

REGISTRY_COLUMNS = [
    "document_id", "source_name", "source_type", "url", "license", "external_api_ok",
    "original_path", "extracted_path", "cleaned_path", "language", "document_type",
    "title", "publication_year", "subtopic", "status", "exclusion_stage",
    "exclusion_reason", "exclusion_detail", "split", "char_count", "word_count",
    "token_count",
]
EXCLUSION_COLUMNS = ["scope", "id", "stage", "reason", "detail", "timestamp"]

DOC_REASONS = {"extraction_error", "needs_ocr", "too_short", "wrong_language",
               "too_much_noise", "out_of_domain", "duplicate", "near_duplicate"}
INSTRUCTION_REASONS = {"schema_error", "invalid_json_quiz", "too_short", "too_long",
                       "wrong_language", "too_much_noise", "duplicate_instruction", "task_mismatch",
                       "not_grounded", "judge_rejected", "manual_rejected", "generation_error"}
STATUSES = ["downloaded", "extracted", "cleaned", "filtered", "deduped", "final", "excluded"]


def _atomic_write_csv(df: pd.DataFrame, path: Path) -> None:
    """Önce .tmp dosyasına yaz, sonra rename: yarıda kesilirse eski dosya bozulmaz."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False, encoding="utf-8")
    # Windows'ta hedef dosya başka bir programca (editör, antivirüs taraması) anlık açıksa
    # rename PermissionError verir; kilit kısa sürer, birkaç kez yeniden dene.
    for attempt in range(10):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.3)


def load_registry(cfg: dict[str, Any]) -> pd.DataFrame:
    """Registry'yi okur; dosya yoksa doğru sütunlarla boş DataFrame döndürür."""
    path = resolve_path(cfg, "registry")
    if not path.exists():
        return pd.DataFrame(columns=REGISTRY_COLUMNS)
    # dtype=str: document_id gibi alanlar ve boş hücreler bozulmasın.
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")


def save_registry(df: pd.DataFrame, cfg: dict[str, Any]) -> None:
    """Registry'yi sütun sırasını koruyarak atomik yazar."""
    for col in REGISTRY_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    extra = [c for c in df.columns if c not in REGISTRY_COLUMNS]  # sonraki fazların ek sütunları
    _atomic_write_csv(df[REGISTRY_COLUMNS + extra], resolve_path(cfg, "registry"))


def format_document_id(n: int) -> str:
    """1 -> 'DOC_000001' (6 hane)."""
    return f"DOC_{n:06d}"


def log_exclusion(cfg: dict[str, Any], scope: str, item_id: str, stage: str,
                  reason: str, detail: str = "") -> None:
    """Elenen doküman/örneği sebep koduyla reports/exclusions.csv'ye ekler (sessiz silme yok)."""
    if scope not in {"document", "instruction"}:
        raise ValueError(f"Geçersiz scope: {scope}")
    valid = DOC_REASONS if scope == "document" else INSTRUCTION_REASONS
    if reason not in valid:
        raise ValueError(f"Geçersiz sebep kodu '{reason}' (scope={scope})")

    path = resolve_path(cfg, "exclusions_csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(EXCLUSION_COLUMNS)
        writer.writerow([scope, item_id, stage, reason, detail,
                         datetime.now().isoformat(timespec="seconds")])


# Doküman adımları sırasıyla ve her adımın girdi durumu (registry.status).
STAGE_ORDER = ["download", "extract", "clean", "filter", "dedup", "split"]
STAGE_INPUT = {"extract": "downloaded", "clean": "extracted", "filter": "cleaned", "dedup": "filtered",
               "split": "deduped"}


def stages_from(stage: str) -> list[str]:
    """Bu adım ve sonrası: bir adım yeniden çalışınca bunların eski kararları geçersizdir."""
    return STAGE_ORDER[STAGE_ORDER.index(stage):]


def excluded_before(registry: pd.DataFrame, stage: str) -> pd.Series:
    """Bu adımdan önceki bir adımda elenmiş dokümanlar (bu adım onları hiç görmez)."""
    earlier = STAGE_ORDER[:STAGE_ORDER.index(stage)]
    return (registry["status"] == "excluded") & registry["exclusion_stage"].isin(earlier)


def reached(registry: pd.DataFrame, stage: str) -> pd.Series:
    """--redo kümesi: bu adımın girdisine ulaşmış bütün dokümanlar. Girdi durumunda ya da ilerisinde
    olanlar ve bu adımda veya sonraki bir adımda elenmiş olanlar; önceki adımda elenenler hariç.

    Böylece bir adımı yeniden çalıştırmak, pipeline'ı o adımdan baştan çalıştırmakla aynı dokümanları işler.
    """
    first, last = STATUSES.index(STAGE_INPUT[stage]), STATUSES.index("final")
    in_flow = registry["status"].isin(STATUSES[first:last + 1])
    excluded_later = (registry["status"] == "excluded") & registry["exclusion_stage"].isin(stages_from(stage))
    return in_flow | excluded_later


def drop_exclusions(cfg: dict[str, Any], scope: str, item_ids: set[str], stage: str | list[str]) -> int:
    """Bir adım yeniden çalıştırılırken o adımın (liste verilirse o adımların) eski eleme kayıtlarını siler.

    Aksi hâlde aynı doküman için eski ve yeni sebep birlikte kalır, erime tablosu iki kez sayar.
    Döner: silinen satır sayısı.
    """
    path = resolve_path(cfg, "exclusions_csv")
    if not path.exists() or not item_ids:
        return 0
    stages = [stage] if isinstance(stage, str) else list(stage)
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    stale = (df["scope"] == scope) & df["stage"].isin(stages) & df["id"].isin(item_ids)
    if stale.any():
        _atomic_write_csv(df[~stale], path)
    return int(stale.sum())
