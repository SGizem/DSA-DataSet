"""Config yükleyici ve seed ayarlayıcı.

Tüm script'ler yolları, eşikleri ve model adlarını buradan okur (kodda sabit değer yok).
"""
from __future__ import annotations

import argparse
import os
import random
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Proje kökü: bu dosya scripts/utils/ altında olduğu için iki üst klasör.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """config.yaml'ı okur, .env'i yükler ve {CONTACT_EMAIL} yer tutucusunu doldurur."""
    load_dotenv(PROJECT_ROOT / ".env")
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with cfg_path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # user_agent içindeki e-posta koda gömülmez, .env'den gelir.
    # .env'de yoksa yer tutucu olduğu gibi kalır; 01_download bunu görüp anlamlı hatayla durur.
    ua = cfg.get("download", {}).get("user_agent")
    email = os.getenv("CONTACT_EMAIL")
    if ua and email:
        cfg["download"]["user_agent"] = ua.replace("{CONTACT_EMAIL}", email)
    return cfg


def resolve_path(cfg: dict[str, Any], key: str) -> Path:
    """cfg['paths'][key] değerini proje köküne göre mutlak Path'e çevirir."""
    return PROJECT_ROOT / cfg["paths"][key]


def set_seed(cfg: dict[str, Any]) -> int:
    """Python `random` seed'ini config.project.random_seed ile sabitler ve seed'i döndürür."""
    seed = int(cfg["project"]["random_seed"])
    random.seed(seed)
    return seed


def add_common_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Her script'in ortak argümanları: --config ve --limit (Sözleşme madde 6)."""
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH),
                        help="config.yaml yolu")
    parser.add_argument("--limit", type=int, default=None,
                        help="Hızlı deneme için işlenecek en fazla öğe sayısı")
    return parser
