"""FAZ 5: Filtreden geçen dokümanlarda birebir aynı (exact) ve çok benzer (near) kopyaları eler.

Çalıştırma (proje kökünden): python -m scripts.05_deduplicate [--config ...] [--limit N] [--calibrate]
                                                            [--calibration-report]

Exact: normalize metnin (küçük harf, boşluklar teke) SHA-256'sı aynı olan gruplar -> biri kalır, diğerleri
`duplicate`. Near: kelime 5-gram shingle + MinHash + LSH ile aday çiftler, adaylar gerçek Jaccard ile
doğrulanır, eşiği geçenler union-find ile kümelenir -> kümeden biri kalır, diğerleri `near_duplicate`.
Kalan doküman seçimi: config.dedup.source_priority sırası, sonra uzun metin, sonra küçük document_id.

Kopya bulmak bütün dokümanları birlikte görmeyi gerektirdiği için her çalıştırma filtreden geçen
dokümanların tamamını (önceki dedup sonuçları dahil) baştan değerlendirir; sonuç deterministiktir,
tekrar çalıştırmak aynı kararları verir.

--calibrate: tahmini Jaccard'ı config.dedup.calibration_range içinde olan çiftlerden tabakalı örneklem ->
reports/calibration_dedup.csv (same_content sütunu etiketleme için boş). Registry'ye dokunmaz.
--calibration-report: etiketli CSV'den her aday eşiğin hata sayıları -> reports/calibration_dedup_report.md.
"""
from __future__ import annotations

import argparse
import hashlib
import random
import re
import sys
from collections import Counter, defaultdict
from typing import Any

import pandas as pd
from datasketch import MinHash, MinHashLSH

from scripts.utils.config import PROJECT_ROOT, add_common_args, load_config, resolve_path, set_seed
from scripts.utils.logging_utils import log_summary, setup_logger
from scripts.utils.registry import drop_exclusions, load_registry, log_exclusion, reached, save_registry, stages_from
from scripts.utils.text_utils import tr_lower

STAGE = "dedup"
NEAR_COLUMNS = ["cluster_id", "document_id", "kept", "jaccard", "match_type", "source", "title"]
CALIBRATION_COLUMNS = ["doc_a", "doc_b", "a_title", "b_title", "pool", "estimated_jaccard", "jaccard",
                       "a_first_300", "b_first_300", "same_content", "label_note"]
WORD = re.compile(r"\w+")


def normalize(text: str, language: str) -> str:
    """Küçük harf (Türkçe için İ/I kuralıyla) ve bütün boşluk dizileri tek boşluk."""
    low = tr_lower(text) if language == "tr" else text.lower()
    return " ".join(low.split())


def content_hash(normalized: str) -> str:
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def shingles(normalized: str, k: int, is_code: bool) -> set[str]:
    """Kelime k-gram'ları. Düzyazıda kelime = harf/rakam dizisi (noktalama farkı benzerliği bozmasın);
    kodda boşlukla bölünmüş token (`a[i]=b` gibi ifadeler tek parça kalsın)."""
    tokens = normalized.split() if is_code else WORD.findall(normalized)
    if len(tokens) < k:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i:i + k]) for i in range(len(tokens) - k + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def minhash(items: set[str], num_perm: int, seed: int) -> MinHash:
    m = MinHash(num_perm=num_perm, seed=seed)
    m.update_batch([s.encode("utf-8") for s in sorted(items)])
    return m


def keep_order(source_priority: list[str]):
    """Kümeden kalacak dokümanı seçen sıralama anahtarı: kaynak önceliği, uzun metin, küçük id."""
    rank = {name: i for i, name in enumerate(source_priority)}

    def key(doc: dict[str, Any]) -> tuple:
        return rank.get(doc["source_name"], len(rank)), -doc["char_count"], doc["document_id"]
    return key


class UnionFind:
    def __init__(self, items: list[str]) -> None:
        self.parent = {x: x for x in items}

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def make_doc(document_id: str, source_name: str, title: str, text: str, language: str, is_code: bool,
             k: int) -> dict[str, Any]:
    norm = normalize(text, language)
    return {"document_id": document_id, "source_name": source_name, "title": title, "char_count": len(text),
            "text": text, "hash": content_hash(norm), "language": language, "is_code": is_code,
            "shingles": shingles(norm, k, is_code)}


def load_docs(rows: pd.DataFrame, k: int) -> dict[str, dict[str, Any]]:
    docs = {}
    for _, row in rows.iterrows():
        text = (PROJECT_ROOT / row["cleaned_path"]).read_text(encoding="utf-8")
        docs[row["document_id"]] = make_doc(row["document_id"], row["source_name"], row["title"], text,
                                            row["language"], row["source_type"] == "code", k)
    return docs


def exact_groups(docs: dict[str, dict[str, Any]]) -> list[list[str]]:
    """Aynı SHA-256'ya sahip, birden çok üyeli gruplar (id sırasıyla)."""
    by_hash: dict[str, list[str]] = defaultdict(list)
    for doc_id in sorted(docs):
        by_hash[docs[doc_id]["hash"]].append(doc_id)
    return [ids for ids in by_hash.values() if len(ids) > 1]


def candidate_pairs(docs: dict[str, dict[str, Any]], ids: list[str], cfg: dict[str, Any],
                    seed: int) -> dict[tuple[str, str], float]:
    """LSH aday çiftleri ve MinHash tahmini Jaccard'ları. Anahtar (küçük id, büyük id)."""
    d = cfg["dedup"]
    lsh = MinHashLSH(threshold=d["lsh_threshold"], num_perm=d["minhash_num_perm"])
    hashes = {}
    for doc_id in ids:
        hashes[doc_id] = minhash(docs[doc_id]["shingles"], d["minhash_num_perm"], seed)
        lsh.insert(doc_id, hashes[doc_id])
    pairs = {}
    for doc_id in ids:
        for other in lsh.query(hashes[doc_id]):
            if other != doc_id:
                pair = tuple(sorted((doc_id, other)))
                pairs[pair] = round(hashes[pair[0]].jaccard(hashes[pair[1]]), 4)
    return pairs


def deduplicate(docs: dict[str, dict[str, Any]], cfg: dict[str, Any], seed: int):
    """Döner: (kararlar {id: (sebep, kalan_id, jaccard)}, near_duplicates satırları, istatistik)."""
    d = cfg["dedup"]
    key = keep_order(d.get("source_priority") or [])
    decisions: dict[str, tuple[str, str, float]] = {}
    report_rows: list[dict[str, Any]] = []

    for n, ids in enumerate(exact_groups(docs), start=1):
        kept = min((docs[i] for i in ids), key=key)["document_id"]
        for doc_id in ids:
            if doc_id != kept:
                decisions[doc_id] = ("duplicate", kept, 1.0)
            report_rows.append(_report_row(f"E{n:03d}", docs[doc_id], kept, 1.0, "exact"))

    survivors = sorted(i for i in docs if i not in decisions)
    pairs = candidate_pairs(docs, survivors, cfg, seed)
    verified = {}
    for (a, b) in pairs:
        score = jaccard(docs[a]["shingles"], docs[b]["shingles"])
        if score >= d["jaccard_threshold"]:
            verified[(a, b)] = score
    uf = UnionFind(survivors)
    for a, b in verified:
        uf.union(a, b)
    clusters: dict[str, list[str]] = defaultdict(list)
    for doc_id in survivors:
        clusters[uf.find(doc_id)].append(doc_id)
    multi = sorted((ids for ids in clusters.values() if len(ids) > 1), key=lambda ids: ids[0])
    for n, ids in enumerate(multi, start=1):
        kept = min((docs[i] for i in ids), key=key)["document_id"]
        for doc_id in ids:
            score = 1.0 if doc_id == kept else round(jaccard(docs[doc_id]["shingles"], docs[kept]["shingles"]), 4)
            if doc_id != kept:
                decisions[doc_id] = ("near_duplicate", kept, score)
            report_rows.append(_report_row(f"N{n:03d}", docs[doc_id], kept, score, "near"))
    stats = {"candidate_pairs": len(pairs), "verified_pairs": len(verified),
             "exact_groups": sum(1 for r in report_rows if r["match_type"] == "exact" and r["kept"] == "yes"),
             "near_clusters": len(multi)}
    return decisions, report_rows, stats


def _report_row(cluster: str, doc: dict[str, Any], kept: str, score: float, match_type: str) -> dict[str, Any]:
    return {"cluster_id": cluster, "document_id": doc["document_id"],
            "kept": "yes" if doc["document_id"] == kept else f"no ({kept})",
            "jaccard": "" if doc["document_id"] == kept else score, "match_type": match_type,
            "source": doc["source_name"], "title": doc["title"]}


def all_pair_jaccards(docs: dict[str, dict[str, Any]], ids: list[str]) -> dict[tuple[str, str], float]:
    """En az bir ortak shingle'ı olan bütün çiftlerin gerçek Jaccard'ı (ters indeksle; tahmin yok).

    Yalnızca kalibrasyonda kullanılır: aralıkta yeterli çift yoksa örneklem en benzer gerçek çiftlerle
    tamamlanır ve LSH'nin eşiğin üstünde bir çifti kaçırmadığı da buradan görülür.
    """
    postings: dict[str, list[str]] = defaultdict(list)
    for doc_id in ids:
        for s in docs[doc_id]["shingles"]:
            postings[s].append(doc_id)
    shared: Counter = Counter()
    for members in postings.values():
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                shared[(members[i], members[j])] += 1
    return {pair: n / (len(docs[pair[0]]["shingles"]) + len(docs[pair[1]]["shingles"]) - n)
            for pair, n in shared.items()}


def calibrate(docs: dict[str, dict[str, Any]], cfg: dict[str, Any], seed: int, logger) -> None:
    """Tahmini Jaccard'ı kalibrasyon aralığında olan çiftlerden eşit genişlikte 5 dilimde tabakalı örneklem.

    Bir dilimde yeterli çift yoksa eksik kalan kota diğer dilimlerden seed'li rastgele doldurulur. Aralıkta
    toplam çift örneklemden azsa hepsi alınır, kalan yer aralığın altındaki en benzer gerçek çiftlerle
    doldurulur (`pool` sütunu hangisi olduğunu söyler): eşiğin alt tarafındaki risk, yani benzer konulu
    ama farklı dokümanların kopya sayılması, ancak bu çiftlerle ölçülebilir.
    """
    d = cfg["dedup"]
    path = resolve_path(cfg, "calibration_dedup")
    if path.exists():
        existing = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
        if (existing.get("same_content", pd.Series(dtype=str)) != "").any():
            logger.error("%s etiketli; üzerine yazılmadı. Yeni örneklem için dosyayı elle taşıyın/silin.",
                         path.relative_to(PROJECT_ROOT).as_posix())
            sys.exit(1)
    exact = {i for ids in exact_groups(docs) for i in ids[1:]}  # birebir kopyalar zaten Jaccard 1
    ids = sorted(i for i in docs if i not in exact)
    lo, hi = d["calibration_range"]
    pool = sorted((pair, est) for pair, est in candidate_pairs(docs, ids, cfg, seed).items() if lo <= est <= hi)
    size, bins = d["calibration_size"], 5
    width = (hi - lo) / bins
    by_bin: dict[int, list] = defaultdict(list)
    for item in pool:
        by_bin[min(int((item[1] - lo) / width), bins - 1)].append(item)
    rng = random.Random(seed)
    chosen = []
    for b in range(bins):
        quota = size // bins + (1 if b < size % bins else 0)
        chosen += rng.sample(by_bin[b], min(quota, len(by_bin[b])))
    rest = [item for item in pool if item not in chosen]
    chosen += rng.sample(rest, min(size - len(chosen), len(rest)))
    selected = [(pair, "aralik_ici") for pair, _ in chosen]
    exact_scores = all_pair_jaccards(docs, ids)
    if len(selected) < size:
        taken = {pair for pair, _ in selected}
        below = sorted((p for p, j in exact_scores.items() if j < lo and p not in taken),
                       key=lambda p: (-exact_scores[p], p))
        selected += [(pair, "aralik_alti_en_benzer") for pair in below[: size - len(selected)]]
    rows = []
    for (a, b), pool_name in sorted(selected, key=lambda x: -exact_scores.get(x[0], 0)):
        est = minhash(docs[a]["shingles"], d["minhash_num_perm"], seed).jaccard(
            minhash(docs[b]["shingles"], d["minhash_num_perm"], seed))
        rows.append({"doc_a": a, "doc_b": b, "a_title": docs[a]["title"], "b_title": docs[b]["title"],
                     "pool": pool_name, "estimated_jaccard": round(est, 4),
                     "jaccard": round(jaccard(docs[a]["shingles"], docs[b]["shingles"]), 4),
                     "a_first_300": " ".join(docs[a]["text"][:300].split()),
                     "b_first_300": " ".join(docs[b]["text"][:300].split()),
                     "same_content": "", "label_note": ""})
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=CALIBRATION_COLUMNS).to_csv(path, index=False, encoding="utf-8-sig")
    counts = [len(by_bin[b]) for b in range(bins)]
    top = max(exact_scores.values(), default=0.0)
    logger.info("Kalibrasyon: aralık [%s, %s] içinde %d aday çift (dilim başına %s); bütün çiftlerde en yüksek "
                "gerçek Jaccard %.4f; %d çift -> %s", lo, hi, len(pool), counts, top, len(rows),
                path.relative_to(PROJECT_ROOT).as_posix())
    if len(pool) < size:
        logger.warning("Aralıkta %d çift var; örneklem aralığın altındaki en benzer %d gerçek çiftle tamamlandı.",
                       len(pool), size - len(pool))


# Kontrollü değişiklik deneyi: gerçek bir dokümanın kopyası bilinen bir biçimde değiştirilir ve orijinalle
# Jaccard'ı ölçülür. Gerçek kopya çifti az ya da hiç yoksa eşiğin hangi kopyaları yakaladığını bu gösterir.
APPENDED_LINE = "Kaynak: ornek-site.org, erişim tarihi 01.10.2026. Sayfa 3."
SITE_FRAME = ("Ana sayfa | Dersler | Hakkımızda | İletişim | Giriş yap. Bu sayfa en son 12 Mart 2024 tarihinde "
              "düzenlendi. Tüm hakları saklıdır. Gizlilik politikası | Çerez ayarları | Site haritası | "
              "Bizi sosyal medyada takip edin.")
VARIANTS = [("Sona tek satır kaynak bilgisi eklendi", "append", 0),
            ("Başa ve sona site menüsü/altbilgisi eklendi (~30 kelime)", "frame", 0),
            ("Satırların %5'i silindi", "drop_lines", 0.05), ("Satırların %10'u silindi", "drop_lines", 0.10),
            ("Satırların %20'si silindi", "drop_lines", 0.20), ("Satırların %30'u silindi", "drop_lines", 0.30),
            ("Kelimelerin %1'i değiştirildi", "edit_words", 0.01),
            ("Kelimelerin %3'ü değiştirildi", "edit_words", 0.03),
            ("Kelimelerin %5'i değiştirildi", "edit_words", 0.05)]
VARIATION_SAMPLE = {"prose": (20, 300), "code": (10, 200)}  # grup: (doküman sayısı, en az kelime/token)


def make_variant(text: str, kind: str, amount: float, rng: random.Random) -> str:
    if kind == "append":
        return text + "\n" + APPENDED_LINE
    if kind == "frame":
        return SITE_FRAME + "\n" + text + "\n" + SITE_FRAME
    if kind == "drop_lines":
        lines = text.split("\n")
        filled = [i for i, line in enumerate(lines) if line.strip()]
        drop = set(rng.sample(filled, max(1, round(len(filled) * amount))))
        return "\n".join(line for i, line in enumerate(lines) if i not in drop)
    words = text.split(" ")
    for i in rng.sample(range(len(words)), max(1, round(len(words) * amount))):
        words[i] = rng.choice(words)
    return " ".join(words)


def variation_rows(docs: dict[str, dict[str, Any]], cfg: dict[str, Any], seed: int) -> list[str]:
    """Seed'li örneklem dokümanlarda her değişiklik türünün orijinale Jaccard'ı: medyan, en düşük ve eşiği
    geçen oran (eşiği geçen = near_duplicate olarak yakalanır)."""
    k, t = cfg["dedup"]["shingle_words"], cfg["dedup"]["jaccard_threshold"]
    rng = random.Random(seed)
    groups = {}
    for group, (count, min_tokens) in VARIATION_SAMPLE.items():
        ids = sorted(i for i, doc in docs.items() if doc["is_code"] == (group == "code")
                     and len(doc["text"].split()) >= min_tokens)
        groups[group] = rng.sample(ids, min(count, len(ids)))
    lines = [f"| Değişiklik | Grup | Doküman | Medyan Jaccard | En düşük | En yüksek | Eşiği (≥ {t:g}) geçen |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for label, kind, amount in VARIANTS:
        for group, ids in groups.items():
            scores = []
            for doc_id in ids:
                doc = docs[doc_id]
                variant = make_variant(doc["text"], kind, amount, random.Random(f"{seed}:{doc_id}:{kind}:{amount}"))
                other = shingles(normalize(variant, doc["language"]), k, doc["is_code"])
                scores.append(jaccard(doc["shingles"], other))
            s = pd.Series(scores)
            lines.append(f"| {label} | {'kod' if group == 'code' else 'düzyazı'} | {len(s)} | {s.median():.3f} | "
                         f"{s.min():.3f} | {s.max():.3f} | {int((s >= t).sum())}/{len(s)} |")
    sample = "; ".join(f"{'kod' if g == 'code' else 'düzyazı'}: {' '.join(ids)}" for g, ids in groups.items())
    return lines + ["", f"Örneklem (seed {seed}) {sample}."]


def calibration_report(cfg: dict[str, Any], docs: dict[str, dict[str, Any]], seed: int, logger) -> None:
    """Etiketli çiftlerden eşik tablosu ve kontrollü değişiklik deneyi. Eşiği seçmez; seçim ve gerekçesi
    experiments.md'ye yazılır."""
    df = pd.read_csv(resolve_path(cfg, "calibration_dedup"), encoding="utf-8-sig", dtype=str, keep_default_na=False)
    if df.empty:
        logger.error("Kalibrasyon CSV'si boş.")
        sys.exit(1)
    if not df["same_content"].isin(["0", "1"]).all():
        logger.error("same_content her satırda 0 ya da 1 olmalı.")
        sys.exit(1)
    df["score"] = df["jaccard"].astype(float)
    df["same"] = df["same_content"] == "1"
    t0 = cfg["dedup"]["jaccard_threshold"]
    exact = {i for ids in exact_groups(docs) for i in ids[1:]}
    top = max(all_pair_jaccards(docs, sorted(i for i in docs if i not in exact)).values(), default=0.0)
    pools = df["pool"].value_counts().to_dict() if "pool" in df.columns else {}
    diff_max = f"{df.loc[~df['same'], 'score'].max():g}" if (~df["same"]).any() else "-"
    same_min = f"{df.loc[df['same'], 'score'].min():g}" if df["same"].any() else "-"
    lines = ["# Near-duplicate eşik kalibrasyonu", "",
             "`python -m scripts.05_deduplicate --calibration-report` üretir.", "",
             "## 1. Gerçek çiftler", "",
             f"Kaynak: `reports/calibration_dedup.csv` (etiket 1 = aynı içerik, 0 = farklı içerik). Havuz: {pools}.",
             "", f"Dedup'a giren {len(docs)} dokümanın en az bir ortak shingle'ı olan bütün çiftlerinde gerçek "
             f"Jaccard'ın en yüksek değeri: {top:.4f}.", "",
             f"Etiketli çift: {len(df)} (aynı içerik {int(df['same'].sum())}, farklı {int((~df['same']).sum())}). "
             f"Farklı içerikli çiftlerde en yüksek Jaccard: {diff_max}; aynı içerikli çiftlerde en düşük: {same_min}.",
             "", "Eşik t için: gerçek Jaccard'ı t ve üstünde olan çift kopya sayılır, biri elenir.", "",
             "| Eşik | Yanlış eleme (farklı içerik, kopya sayıldı) | Kaçan kopya (aynı içerik, elenmedi) | Doğru karar |",
             "| --- | --- | --- | --- |"]
    grid = {0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, t0}
    grid |= set(df.loc[df["same"], "score"])  # aynı içerikli çiftlerin skorları da sınır noktasıdır
    for t in sorted(grid):
        wrong = int((~df["same"] & (df["score"] >= t)).sum())
        missed = int((df["same"] & (df["score"] < t)).sum())
        mark = " (config)" if t == t0 else ""
        lines.append(f"| {t:g}{mark} | {wrong} | {missed} | {len(df) - wrong - missed}/{len(df)} |")
    lines += ["", "## 2. Kontrollü değişiklik deneyi", "",
              "Gerçek dokümanların kopyası bilinen bir biçimde değiştirilip orijinalle karşılaştırıldı (seed'li; "
              "eklenen metinler sabit). Satır silme: boş olmayan satırlardan rastgele; kelime değiştirme: "
              "rastgele kelimenin yerine aynı dokümandan rastgele bir kelime.", ""]
    lines += variation_rows(docs, cfg, seed)
    lines += ["", "## 3. Etiketli çiftler", ""]
    lines += [f"- {r.doc_a} / {r.doc_b} ({r.a_title} / {r.b_title}), Jaccard {r.score:g}, "
              f"etiket {r.same_content}: {r.label_note}" for r in df.sort_values("score", ascending=False).itertuples()]
    path = resolve_path(cfg, "calibration_dedup_report")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Kalibrasyon raporu: %s", path.relative_to(PROJECT_ROOT).as_posix())


def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description=__doc__.splitlines()[0]))
    parser.add_argument("--calibrate", action="store_true", help="Near-duplicate eşiği için etiketleme CSV'si üret")
    parser.add_argument("--calibration-report", action="store_true",
                        help="Etiketli kalibrasyon CSV'sinden eşik tablosu üret (reports/calibration_dedup_report.md)")
    args = parser.parse_args()
    cfg = load_config(args.config)
    logger = setup_logger("05_deduplicate", cfg)
    seed = set_seed(cfg)

    registry = load_registry(cfg)
    # Filtreden geçen herkes, önceki dedup/split sonuçları dahil: kopya bulmak hepsini birlikte görmeyi ister.
    pending = registry.index[reached(registry, STAGE)].tolist()
    if args.limit is not None:
        pending = pending[: args.limit]
    docs = load_docs(registry.loc[pending], cfg["dedup"]["shingle_words"])
    if args.calibrate:
        calibrate(docs, cfg, seed, logger)
        return
    if args.calibration_report:
        calibration_report(cfg, docs, seed, logger)
        return
    if not cfg["dedup"].get("source_priority"):
        logger.warning("config.dedup.source_priority boş: kümede kalan doküman yalnızca uzunluk ve id ile seçilir.")

    decisions, report_rows, stats = deduplicate(docs, cfg, seed)
    drop_exclusions(cfg, "document", set(docs), stages_from(STAGE))
    for idx in pending:
        doc_id = registry.at[idx, "document_id"]
        if doc_id in decisions:
            reason, kept, score = decisions[doc_id]
            detail = f"kept={kept}" + ("" if reason == "duplicate" else f" jaccard={score}")
            registry.loc[idx, ["status", "exclusion_stage", "exclusion_reason", "exclusion_detail", "split"]] = \
                ["excluded", STAGE, reason, detail, ""]
            log_exclusion(cfg, "document", doc_id, STAGE, reason, detail)
        else:
            registry.loc[idx, ["status", "exclusion_stage", "exclusion_reason", "exclusion_detail", "split"]] = \
                ["deduped", "", "", "", ""]
    save_registry(registry, cfg)
    pd.DataFrame(report_rows, columns=NEAR_COLUMNS).to_csv(resolve_path(cfg, "near_duplicates"), index=False,
                                                           encoding="utf-8-sig")
    reasons = Counter(r for r, _, _ in decisions.values())
    logger.info("LSH aday çift: %d | Jaccard >= %s doğrulanan: %d | exact grup: %d | near küme: %d",
                stats["candidate_pairs"], cfg["dedup"]["jaccard_threshold"], stats["verified_pairs"],
                stats["exact_groups"], stats["near_clusters"])
    logger.info("Eleme sebepleri: %s", dict(reasons))
    log_summary(logger, len(pending), len(pending) - len(decisions), 0, len(decisions))


if __name__ == "__main__":
    main()
