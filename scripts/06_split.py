"""FAZ 6: Dokümanları doküman düzeyinde train/validation/test olarak ayırır ve corpus JSONL dosyalarını yazar.

Çalıştırma (proje kökünden): python -m scripts.06_split [--config ...] [--limit N]

Ayrım doküman düzeyindedir (chunk ya da örnek düzeyinde değil): bir dokümanın bütün metni tek kümeye düşer,
böylece aynı metnin parçası hem eğitimde hem testte olamaz (data leakage, rehber §10). Dokümanlar
config.split.stratify_by (kaynak) bazında gruplanır; her grup kendi seed'iyle karıştırılır ve oranlara göre
bölünür. Böylece her kaynak her kümede temsil edilir ve bir kaynağın ataması diğer kaynaklardan bağımsızdır.

Her çalıştırma dedup'tan geçen bütün dokümanları baştan atar; sonuç deterministiktir.
Çıktı: data/final/{train,validation,test}.jsonl, registry.split ve status=final.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from typing import Any

import pandas as pd

from scripts.utils.config import PROJECT_ROOT, add_common_args, load_config, resolve_path, set_seed
from scripts.utils.logging_utils import log_summary, setup_logger
from scripts.utils.registry import load_registry, reached, save_registry

STAGE = "split"
SPLITS = ["train", "validation", "test"]
RECORD_FIELDS = ["document_id", "title", "source", "url", "license", "language", "document_type",
                 "publication_year", "subtopic", "split", "char_count", "word_count", "token_count", "text"]


def split_counts(n: int, ratios: dict[str, float]) -> dict[str, int]:
    """Bir gruptaki n dokümanın kümelere dağılımı. Validation ve test yukarı yuvarlanır (en az 0,5 olanlar 1
    olur), kalan train'e gider: 10 bölümlük bir kitap da validation ve testte birer bölümle temsil edilir."""
    validation = int(n * ratios["validation"] + 0.5)
    test = int(n * ratios["test"] + 0.5)
    while validation + test >= n and validation + test > 0:  # çok küçük grup: train'de en az bir doküman kalsın
        if test >= validation:
            test -= 1
        else:
            validation -= 1
    return {"train": n - validation - test, "validation": validation, "test": test}


def rank_key(seed: int, group: str, doc_id: str) -> str:
    """Dokümanın grup içindeki seed'li sırası: kimliğin özeti. Başka dokümanlara bağlı değildir."""
    return hashlib.sha256(f"{seed}:{group}:{doc_id}".encode("utf-8")).hexdigest()


def assign_splits(groups: dict[str, list[str]], ratios: dict[str, float], seed: int) -> dict[str, str]:
    """{grup: [document_id]} -> {document_id: split}.

    Her grupta dokümanlar seed'li özetlerine göre sıralanır; sıranın başı test, sonra validation, kalanı
    train. Sıra her doküman için ayrı hesaplandığından bir kaynağa doküman eklemek ya da çıkarmak yalnızca
    küme sınırındaki bir iki dokümanı yer değiştirtir; test kümesi corpus sürümleri arasında kararlı kalır.
    (v0.9'da grup listesi seed'le karıştırılıyordu: 22.10.2026'da tek bir doküman eklenince İngilizce
    Vikipedi'nin 117 dokümanı küme değiştirdi.) Başka kaynakların ataması hiç değişmez.
    """
    assignment = {}
    for group, ids in sorted(groups.items()):
        order = sorted(ids, key=lambda d: (rank_key(seed, group, d), d))
        counts = split_counts(len(order), ratios)
        start = 0
        for split in ("test", "validation", "train"):
            for doc_id in order[start:start + counts[split]]:
                assignment[doc_id] = split
            start += counts[split]
    return assignment


def to_record(row: pd.Series, split: str) -> dict[str, Any]:
    text = (PROJECT_ROOT / row["cleaned_path"]).read_text(encoding="utf-8")
    year = row["publication_year"]
    token = row.get("token_count", "")
    return {"document_id": row["document_id"], "title": row["title"], "source": row["source_name"],
            "url": row["url"], "license": row["license"], "language": row["language"],
            "document_type": row["document_type"], "publication_year": int(year) if year else None,
            "subtopic": row["subtopic"], "split": split, "char_count": len(text), "word_count": len(text.split()),
            "token_count": int(token) if token else None, "text": text}


def write_jsonl(records: list[dict[str, Any]], path) -> None:
    """Atomik yazım: önce .tmp, sonra yer değiştirme (yarıda kalan dosya eski dosyayı bozmasın)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        for record in records:
            f.write(json.dumps({k: record[k] for k in RECORD_FIELDS}, ensure_ascii=False) + "\n")
    tmp.replace(path)


def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description=__doc__.splitlines()[0]))
    args = parser.parse_args()
    cfg = load_config(args.config)
    logger = setup_logger("06_split", cfg)
    seed = set_seed(cfg)
    s = cfg["split"]
    if abs(sum(s["ratios"].values()) - 1) > 1e-9 or set(s["ratios"]) != set(SPLITS):
        raise ValueError(f"config.split.ratios {SPLITS} için toplamı 1 olmalı: {s['ratios']}")

    registry = load_registry(cfg)
    if "token_count" not in registry.columns:
        registry["token_count"] = ""
    pending = registry.index[reached(registry, STAGE) & (registry["status"] != "excluded")].tolist()
    if args.limit is not None:
        pending = pending[: args.limit]
    rows = registry.loc[pending]
    groups = rows.groupby(s["stratify_by"])["document_id"].apply(list).to_dict()
    assignment = assign_splits(groups, s["ratios"], seed)

    records: dict[str, list[dict[str, Any]]] = {split: [] for split in SPLITS}
    for idx in pending:
        row = registry.loc[idx]
        split = assignment[row["document_id"]]
        records[split].append(to_record(row, split))
        registry.loc[idx, ["status", "split"]] = ["final", split]
    final_dir = resolve_path(cfg, "final_dir")
    for split in SPLITS:
        write_jsonl(sorted(records[split], key=lambda r: r["document_id"]), final_dir / f"{split}.jsonl")
    save_registry(registry, cfg)

    table = pd.crosstab(rows[s["stratify_by"]], rows["document_id"].map(assignment))[SPLITS]
    logger.info("Kaynak x küme:\n%s", table.to_string())
    sizes = Counter(assignment.values())
    logger.info("Küme boyutları: %s (oran %s)", {k: sizes[k] for k in SPLITS},
                {k: round(sizes[k] / len(assignment), 3) for k in SPLITS})
    log_summary(logger, len(pending), len(pending), 0, 0)


if __name__ == "__main__":
    main()
