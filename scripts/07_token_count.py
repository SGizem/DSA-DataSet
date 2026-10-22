"""FAZ 7a: Final dokümanların token sayısını config.tokens.tokenizer ile hesaplar.

Çalıştırma (proje kökünden): python -m scripts.07_token_count [--config ...] [--limit N]

Her dokümanın metni (data/final JSONL'deki `text`, yani data/cleaned dosyası) özel token eklenmeden
(add_special_tokens=False) sayılır. Sonuç registry.token_count'a ve JSONL kayıtlarının token_count alanına
yazılır. reports/token_stats.json: genel ve split bazında min, medyan, ortalama, 95. yüzdelik, max;
long_doc_warning_tokens'ı aşan dokümanlar uyarı olarak.
"""
from __future__ import annotations

import argparse
import json
from typing import Any

import pandas as pd
from transformers import AutoTokenizer
from transformers.utils import logging as hf_logging

from scripts.utils.config import add_common_args, load_config, resolve_path, set_seed
from scripts.utils.logging_utils import log_summary, setup_logger
from scripts.utils.registry import load_registry, save_registry

SPLITS = ["train", "validation", "test"]


def describe(values: pd.Series) -> dict[str, Any]:
    """Doküman başına token dağılımı (rehber §10: min, medyan, ortalama, 95. yüzdelik, max)."""
    if values.empty:
        return {"documents": 0, "total": 0, "min": None, "median": None, "mean": None, "p95": None, "max": None}
    return {"documents": int(len(values)), "total": int(values.sum()), "min": int(values.min()),
            "median": float(values.median()), "mean": round(float(values.mean()), 1),
            "p95": round(float(values.quantile(0.95)), 1), "max": int(values.max())}


def load_tokenizer(cfg: dict[str, Any]):
    t = cfg["tokens"]
    hf_logging.set_verbosity_error()  # "sequence length is longer than max" uyarısı: model girişi değil, sayım
    return AutoTokenizer.from_pretrained(t["tokenizer"], revision=t.get("tokenizer_revision"))


def count_tokens(tokenizer, text: str) -> int:
    return len(tokenizer.encode(text, add_special_tokens=False))


def update_jsonl(path, counts: dict[str, int]) -> int:
    """JSONL kayıtlarının token_count alanını günceller (alan sırası ve diğer alanlar aynen kalır). Atomik."""
    lines = path.read_text(encoding="utf-8").splitlines()
    updated = 0
    out = []
    for line in lines:
        record = json.loads(line)
        if record["document_id"] in counts:
            record["token_count"] = counts[record["document_id"]]
            updated += 1
        out.append(json.dumps(record, ensure_ascii=False))
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(line + "\n" for line in out), encoding="utf-8", newline="\n")
    tmp.replace(path)
    return updated


def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description=__doc__.splitlines()[0]))
    args = parser.parse_args()
    cfg = load_config(args.config)
    logger = setup_logger("07_token_count", cfg)
    set_seed(cfg)

    registry = load_registry(cfg)
    final_dir = resolve_path(cfg, "final_dir")
    texts = {}
    for split in SPLITS:
        for line in (final_dir / f"{split}.jsonl").read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            texts[record["document_id"]] = record["text"]
    pending = registry.index[registry["status"] == "final"].tolist()
    if args.limit is not None:
        pending = pending[: args.limit]
    missing = [registry.at[i, "document_id"] for i in pending if registry.at[i, "document_id"] not in texts]
    if missing:
        raise SystemExit(f"Registry'de final olup JSONL'de olmayan doküman: {missing[:5]} (06_split'i çalıştırın)")

    tokenizer = load_tokenizer(cfg)
    counts = {}
    for idx in pending:
        doc_id = registry.at[idx, "document_id"]
        counts[doc_id] = count_tokens(tokenizer, texts[doc_id])
        registry.at[idx, "token_count"] = str(counts[doc_id])
    for split in SPLITS:
        update_jsonl(final_dir / f"{split}.jsonl", counts)
    save_registry(registry, cfg)

    final = registry[registry["status"] == "final"].copy()
    final = final[final["token_count"] != ""]
    final["tokens"] = final["token_count"].astype(int)
    limit = cfg["tokens"]["long_doc_warning_tokens"]
    long_docs = final[final["tokens"] > limit].sort_values("tokens", ascending=False)
    stats = {"tokenizer": cfg["tokens"]["tokenizer"], "tokenizer_revision": cfg["tokens"].get("tokenizer_revision"),
             "add_special_tokens": False, "overall": describe(final["tokens"]),
             "by_split": {split: describe(final.loc[final["split"] == split, "tokens"]) for split in SPLITS},
             "long_doc_warning_tokens": limit,
             "long_documents": [{"document_id": r.document_id, "title": r.title, "tokens": int(r.tokens)}
                                for r in long_docs.itertuples()]}
    path = resolve_path(cfg, "token_stats")
    path.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    o = stats["overall"]
    logger.info("Toplam token: %d | doküman başına min %s, medyan %s, ortalama %s, p95 %s, max %s",
                o["total"], o["min"], o["median"], o["mean"], o["p95"], o["max"])
    if len(long_docs):
        logger.warning("%d doküman %d token'dan uzun: %s", len(long_docs), limit,
                       ", ".join(f"{r.document_id} ({r.tokens})" for r in long_docs.itertuples()))
    log_summary(logger, len(pending), len(pending), 0, 0)


if __name__ == "__main__":
    main()
