"""Dosyaya + konsola logging ve bitiş özet satırı (Sözleşme madde 6)."""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from scripts.utils.config import resolve_path

_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def setup_logger(name: str, cfg: dict[str, Any]) -> logging.Logger:
    """`reports/logs/<name>.log` dosyasına ve konsola yazan logger döndürür."""
    log_dir = resolve_path(cfg, "log_dir")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if logger.handlers:  # aynı süreçte tekrar çağrılırsa handler çoğalmasın
        return logger

    formatter = logging.Formatter(_FORMAT)
    file_handler = logging.FileHandler(log_dir / f"{name}.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    if hasattr(sys.stdout, "reconfigure"):
        # Çıktı dosyaya yönlendirildiğinde Windows cp1254 kullanır; "ů" gibi karakterler log satırını düşürmesin.
        sys.stdout.reconfigure(errors="replace")
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console)
    return logger


def log_summary(logger: logging.Logger, processed: int, succeeded: int,
                failed: int, excluded: int) -> None:
    """Script bitişinde işlenen / başarılı / başarısız / elenen özet satırı."""
    logger.info("ÖZET | işlenen=%d | başarılı=%d | başarısız=%d | elenen=%d",
                processed, succeeded, failed, excluded)
