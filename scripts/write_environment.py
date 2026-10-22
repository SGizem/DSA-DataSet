"""Python ve requirements.txt'teki paketlerin gerçek kurulu sürümlerini reports/environment.txt'ye yazar."""
from __future__ import annotations

import argparse
import platform
import re
import sys
from importlib import metadata
from pathlib import Path

from scripts.utils.config import PROJECT_ROOT, add_common_args, load_config, resolve_path
from scripts.utils.logging_utils import log_summary, setup_logger


def package_names(requirements: Path) -> list[str]:
    """requirements.txt'ten paket adlarını okur (sürüm belirteçlerini atar)."""
    names = []
    for line in requirements.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.append(re.split(r"[=<>~!\[ ]", line, maxsplit=1)[0])
    return names


def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description=__doc__))
    args = parser.parse_args()
    cfg = load_config(args.config)
    logger = setup_logger("write_environment", cfg)

    names = package_names(PROJECT_ROOT / "requirements.txt")
    if args.limit:
        names = names[: args.limit]

    lines = [f"python: {sys.version.split()[0]}", f"platform: {platform.platform()}", ""]
    ok = failed = 0
    for name in names:
        try:
            lines.append(f"{name}=={metadata.version(name)}")
            ok += 1
        except metadata.PackageNotFoundError:
            lines.append(f"{name}: NOT INSTALLED")
            failed += 1

    out = resolve_path(cfg, "environment_txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Yazıldı: %s", out)
    log_summary(logger, len(names), ok, failed, 0)


if __name__ == "__main__":
    main()
