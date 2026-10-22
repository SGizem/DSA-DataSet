"""FAZ 4: Temizlenmiş dokümanları uzunluk, dil, gürültü ve alan skoruna göre filtreler.

Çalıştırma (proje kökünden): python -m scripts.04_filter [--config ...] [--limit N] [--redo] [--calibrate]

Her doküman için hesaplanır ve registry'ye yazılır: language, subtopic, char_count, word_count,
domain_score, noise_ratio. Eleme sırası (ilk eşleşen sebep yazılır):
too_short -> wrong_language -> too_much_noise -> out_of_domain.

--calibration-report: etiketli CSV'den her aday eşiğin hata sayılarını reports/calibration_domain_report.md'ye yazar.
--calibrate: reports/calibration_domain.csv üretir (domain_score çeyreklerine göre tabakalı 50 doküman,
label_in_domain sütunu etiketleme için boş). Registry'ye dokunmaz. Eşik (config.filter.domain_score_threshold)
null ise ve --calibrate verilmemişse script çalışmaz.
"""
from __future__ import annotations

import argparse
import random
import re
import sys
import unicodedata
from pathlib import PurePosixPath
from collections import Counter
from typing import Any

import pandas as pd
import yaml
from langdetect import DetectorFactory, detect
from langdetect.lang_detect_exception import LangDetectException

from scripts.utils.config import PROJECT_ROOT, add_common_args, load_config, resolve_path, set_seed
from scripts.utils.logging_utils import log_summary, setup_logger
from scripts.utils.registry import (drop_exclusions, load_registry, log_exclusion, reached, save_registry,
                                    stages_from)
from scripts.utils.text_utils import is_code_like, tr_lower

# langdetect içinde rastgelelik var; sabitlenmezse aynı metne farklı çalıştırmalarda farklı dil diyebilir.
DetectorFactory.seed = 0

# Gürültü sayılmayanlar: harf (L), rakam (N, ² dahil), boşluk (Z), noktalama (P), matematik sembolü (Sm: ≤ ∈ → ∑ ∞).
CLEAN_CATEGORIES = ("L", "N", "Z", "P")
# Unicode'da "diğer sembol" sayılan ama TeX ve kodda olağan karakterler: ^ $ ` (üs, formül sınırı, kod).
CLEAN_EXTRA = set("^$`")
CALIBRATION_COLUMNS = ["document_id", "title", "source", "domain_score", "first_300_chars", "label_in_domain"]


def read(stored: str) -> str:
    path = PROJECT_ROOT / stored
    return path.read_text(encoding="utf-8")


def lower(text: str, language: str) -> str:
    return tr_lower(text) if language == "tr" else text.lower()


def term_pattern(terms: list[str]) -> re.Pattern:
    """Kelime başında eşleşme: "algoritma" "algoritmaları"nı da sayar (Türkçe ekler), "logaritma"yı saymaz."""
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True)) + ")")


def noise_ratio(text: str) -> float:
    """Harf, rakam, boşluk, noktalama ve matematik sembolü olmayan karakterlerin oranı (▲ ♕ ■ gibi)."""
    if not text:
        return 0.0
    noisy = sum(1 for ch in text if not (ch.isspace() or ch in CLEAN_EXTRA or unicodedata.category(ch) == "Sm"
                                         or unicodedata.category(ch)[0] in CLEAN_CATEGORIES))
    return round(noisy / len(text), 4)


def detect_language(text: str, rng: random.Random, samples: int, size: int) -> str:
    """Dokümandan en fazla `samples` adet `size` karakterlik parça; çoğunluk oyu.

    Tek parça yerine birkaç parça: Türkçe bir maddedeki İngilizce kod bloğu tek başına sonucu belirlemesin.
    """
    if len(text) <= size:
        chunks = [text]
    else:
        starts = sorted(rng.sample(range(len(text) - size + 1), samples))
        chunks = [text[s:s + size] for s in starts]
    votes: Counter = Counter()
    for chunk in chunks:
        try:
            votes[detect(chunk)] += 1
        except LangDetectException:  # harf içermeyen parça (formül, sayı dizisi)
            continue
    # Eşitlikte alfabetik ilk dil: sonuç parça sırasına bağlı olmasın.
    return min(votes, key=lambda lang: (-votes[lang], lang)) if votes else "unknown"


class Scorer:
    """Alan skoru ve alt konu için derlenmiş kalıplar."""

    def __init__(self, cfg: dict[str, Any]) -> None:
        with resolve_path(cfg, "domain_keywords").open(encoding="utf-8") as f:
            terms = yaml.safe_load(f)["terms"]
        with resolve_path(cfg, "subtopics").open(encoding="utf-8") as f:
            subtopics = yaml.safe_load(f)
        self.domain = {lang: term_pattern(words) for lang, words in terms.items()}
        self.domain_any = term_pattern([w for words in terms.values() for w in words])
        # "title:" önekli terimler yalnızca başlıkta sayılır: "search", "list" gibi genel kelimeler başlıkta konuyu
        # belirler ("Ternary search", "Doubly linked list") ama gövdede her konuda geçer (Python'da list[int]).
        self.subtopics = {name: term_pattern([w.removeprefix("title:") for w in words])
                          for name, words in subtopics.items()}
        self.subtopics_body = {name: term_pattern([w for w in words if not w.startswith("title:")])
                               for name, words in subtopics.items()}

    def domain_score(self, text: str, language: str) -> float:
        """Alan terimi eşleşmesi x 1000 / kelime sayısı. Dili listede yoksa iki dilin terimleri birlikte."""
        words = len(text.split())
        if not words:
            return 0.0
        hits = len(self.domain.get(language, self.domain_any).findall(lower(text, language)))
        return round(hits * 1000 / words, 2)

    def subtopic(self, text: str, language: str, title: str = "") -> str:
        """Alt konu: önce başlık, sonra gövde. Hiç eşleşme yoksa "genel".

        Neden başlık önce: "tree" kelimesi her konuda geçiyor (recursion tree, spanning tree); yalnız gövde
        sayımı Erickson'ın Recursion ve Dynamic Programming bölümlerini "agaclar" yapıyordu.
        Başlıkta birden çok alt konu geçerse en sonda biten eşleşme kazanır, aynı yerde bitenlerden uzun olan:
        Türkçe ve İngilizce tamlamalarda asıl ad sondadır ("Yığın sıralaması", "Bucket queue", "Random Binary
        Search Trees"). Parantezli açıklama başlıktan atılır ("Tree (graph theory)" bir ağaç maddesidir).
        Manuel kontrolde (22.10.2026) eski kural (başlıkta eşitlikte gövde sayımı) 150 dokümandan 27'sinde
        yanlış alt konu verdi; çoğu "Yığın sıralaması" -> yigin_ve_kuyruk gibi başlık eşitliklerindendi.
        """
        low = lower(text, language)
        body = {name: len(pattern.findall(low)) for name, pattern in self.subtopics_body.items()}
        head = lower(re.sub(r"\([^)]*\)", " ", title.replace("_", " ")), language)
        last = {}
        for name, pattern in self.subtopics.items():
            spans = [(m.end(), m.end() - m.start()) for m in pattern.finditer(head)]
            if spans:
                last[name] = max(spans)
        if last:
            return max(last, key=lambda name: last[name])  # eşitlikte ilk: yaml sırası
        best = max(body, key=lambda name: body[name])
        return best if body[best] else "genel"


def measure(row: pd.Series, text: str, scorer: Scorer, cfg: dict[str, Any], seed: int) -> dict[str, Any]:
    f = cfg["filter"]
    is_code = row["source_type"] == "code"
    # Doküman başına ayrı seed: sonuç, dokümanların işlenme sırasından ve --limit'ten bağımsız.
    rng = random.Random(f"{seed}:{row['document_id']}")
    # Dil düzyazıdan tespit edilir: Türkçe bir maddedeki İngilizce kod blokları sonucu belirlemesin
    # (A* arama algoritması maddesinin %70'i İngilizce sözde kod). Düzyazı çok azsa bütün metin kullanılır.
    prose = "\n".join(line for line in text.split("\n") if not is_code_like(line))
    sample_text = prose if len(prose.strip()) >= f["language_min_prose_chars"] else text
    language = "code" if is_code else detect_language(sample_text, rng, f["language_samples"],
                                                      f["language_sample_chars"])
    return {
        "language": language,
        "char_count": len(text),
        "word_count": len(text.split()),
        "noise_ratio": noise_ratio(text),
        "domain_score": "" if is_code else scorer.domain_score(text, language),
        "subtopic": scorer.subtopic(text, language, subtopic_title(row)),
    }


def subtopic_title(row: pd.Series) -> str:
    """Alt konu için başlık. Kod dosyasında başlık yalnızca dosya adı ("kd_node.py"); depodaki klasör yolu
    konuyu taşıyor ("data_structures/kd_tree/", "dynamic_programming/", "sorts/"). Bu yüzden kodda klasör
    yolu + dosya adı kullanılır: "data structures kd tree kd node"."""
    if row["source_type"] != "code":
        return row["title"]
    parts = list(PurePosixPath(row["original_path"].replace("\\", "/")).with_suffix("").parts)
    if row["source_name"] in parts:
        parts = parts[parts.index(row["source_name"]) + 1:]
    return " ".join(parts).replace("_", " ")


def exclusion(row: pd.Series, m: dict[str, Any], cfg: dict[str, Any]) -> tuple[str, str] | None:
    """Eleme sırası: too_short -> wrong_language -> too_much_noise -> out_of_domain. Döner: (sebep, ayrıntı)."""
    f = cfg["filter"]
    is_code = row["source_type"] == "code"
    minimum = f["min_chars"]["code" if is_code else "prose"]
    if m["char_count"] < minimum:
        return "too_short", f"chars={m['char_count']} < {minimum}"
    if not is_code and m["language"] not in f["allowed_languages"]:
        return "wrong_language", f"language={m['language']}"
    if m["noise_ratio"] > f["max_noise_ratio"]:
        return "too_much_noise", f"noise_ratio={m['noise_ratio']} > {f['max_noise_ratio']}"
    manual = f.get("out_of_scope_urls") or {}
    if row["url"] in manual:
        return "out_of_domain", f"elle inceledim: {manual[row['url']]}"
    threshold = f["domain_score_threshold"]
    if not is_code and threshold is not None and m["domain_score"] < threshold:
        return "out_of_domain", f"domain_score={m['domain_score']} < {threshold}"
    return None


def calibrate(registry: pd.DataFrame, scorer: Scorer, cfg: dict[str, Any], seed: int, logger) -> None:
    """Eşik belirlemek için etiketlenecek örneklem: domain_score çeyreklerinden eşit sayıda, seed'li.

    Yalnızca eşikten önceki kuralları (kısalık, dil, gürültü, elle kapsam dışı) geçen metin dokümanları;
    eşik zaten yalnızca onlara uygulanır.
    """
    rows = []
    candidates = registry[(registry["status"].isin(["cleaned", "filtered"])) & (registry["source_type"] != "code")]
    for _, row in candidates.iterrows():
        text = read(row["cleaned_path"])
        m = measure(row, text, scorer, cfg, seed)
        if exclusion(row, m, {**cfg, "filter": {**cfg["filter"], "domain_score_threshold": None}}):
            continue
        rows.append({"document_id": row["document_id"], "title": row["title"], "source": row["source_name"],
                     "domain_score": m["domain_score"], "first_300_chars": " ".join(text[:300].split()),
                     "label_in_domain": ""})
    path = resolve_path(cfg, "calibration_domain")
    if path.exists():
        existing = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
        if (existing.get("label_in_domain", pd.Series(dtype=str)) != "").any():
            logger.error("%s etiketli; üzerine yazılmadı. Yeni örneklem için dosyayı elle taşıyın/silin.",
                         path.relative_to(PROJECT_ROOT).as_posix())
            sys.exit(1)
    pool = pd.DataFrame(rows)
    size = cfg["filter"]["calibration_size"]
    pool["quartile"] = pd.qcut(pool["domain_score"].rank(method="first"), 4, labels=False)
    rng = random.Random(seed)
    chosen = []
    for q in range(4):
        ids = sorted(pool.loc[pool["quartile"] == q, "document_id"])
        chosen += rng.sample(ids, min(size // 4 + (1 if q < size % 4 else 0), len(ids)))
    sample = pool[pool["document_id"].isin(chosen)].sort_values("document_id")[CALIBRATION_COLUMNS]
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig: Excel Türkçe karakterleri ancak BOM'lu UTF-8'de doğru gösterir; pandas iki türlü de okur.
    sample.to_csv(path, index=False, encoding="utf-8-sig")
    bounds = pool.groupby("quartile")["domain_score"].agg(["min", "max"]).round(2).values.tolist()
    logger.info("Kalibrasyon: %d aday içinden %d doküman -> %s | çeyrek sınırları %s",
                len(pool), len(sample), path.relative_to(PROJECT_ROOT).as_posix(), bounds)


def calibration_report(cfg: dict[str, Any], logger) -> None:
    """Etiketli kalibrasyon CSV'sinden eşik tablosu: her aday eşikte kaç alan içi doküman yanlışlıkla
    elenir, kaç alan dışı doküman kaçar. Eşiği seçmez; seçim ve gerekçesi experiments.md'ye yazılır."""
    df = pd.read_csv(resolve_path(cfg, "calibration_domain"), encoding="utf-8-sig", dtype=str, keep_default_na=False)
    if (df["label_in_domain"] == "").any() or not df["label_in_domain"].isin(["0", "1"]).all():
        logger.error("label_in_domain her satırda 0 ya da 1 olmalı.")
        sys.exit(1)
    df["score"] = df["domain_score"].astype(float)
    df["in_domain"] = df["label_in_domain"] == "1"
    lines = ["# Alan skoru kalibrasyonu", "", "`python -m scripts.04_filter --calibration-report` üretir. Kaynak: "
             "`reports/calibration_domain.csv` (etiket 1 = alan içi, 0 = alan dışı).", "",
             f"Etiketli doküman: {len(df)} (alan içi {int(df['in_domain'].sum())}, "
             f"alan dışı {int((~df['in_domain']).sum())}).", "",
             "Eşik t için: skoru t'nin altındaki doküman elenir.", "",
             "| Eşik | Elenen alan içi (yanlış eleme) | Kalan alan dışı (kaçan) | Doğru karar |",
             "| --- | --- | --- | --- |"]
    for t in sorted({0.0, *df["score"]}):
        wrong_out = int((df["in_domain"] & (df["score"] < t)).sum())
        missed = int((~df["in_domain"] & (df["score"] >= t)).sum())
        lines.append(f"| {t:g} | {wrong_out} | {missed} | {len(df) - wrong_out - missed}/{len(df)} |")
    lines += ["", "Alan dışı etiketlenenler:", ""]
    notes = df["label_note"] if "label_note" in df.columns else pd.Series("", index=df.index)
    lines += [f"- {df.at[i, 'document_id']} {df.at[i, 'title']} (skor {df.at[i, 'score']:g}): {notes[i]}"
              for i in df.index[~df["in_domain"]]]
    path = resolve_path(cfg, "calibration_report")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Kalibrasyon raporu: %s", path.relative_to(PROJECT_ROOT).as_posix())


def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description=__doc__.splitlines()[0]))
    parser.add_argument("--redo", action="store_true", help="Filtrelenmiş ya da bu adımda elenmişleri de yeniden işle")
    parser.add_argument("--calibrate", action="store_true", help="Alan skoru eşiği için etiketleme CSV'si üret")
    parser.add_argument("--calibration-report", action="store_true",
                        help="Etiketli kalibrasyon CSV'sinden eşik tablosu üret (reports/calibration_domain_report.md)")
    args = parser.parse_args()
    cfg = load_config(args.config)
    logger = setup_logger("04_filter", cfg)
    seed = set_seed(cfg)
    registry = load_registry(cfg)
    scorer = Scorer(cfg)

    if args.calibrate:
        calibrate(registry, scorer, cfg, seed, logger)
        return
    if args.calibration_report:
        calibration_report(cfg, logger)
        return
    if cfg["filter"]["domain_score_threshold"] is None:
        logger.error("config.filter.domain_score_threshold boş. Önce `python -m scripts.04_filter --calibrate` "
                     "çalıştırın, reports/calibration_domain.csv dosyasını etiketleyin ve eşiği config.yaml'a yazın.")
        sys.exit(1)

    todo = registry["status"] == "cleaned"
    if args.redo:  # ileri adımlara geçmiş ya da ileride elenmiş olanlar da yeniden filtrelenir
        todo |= reached(registry, "filter")
    pending = registry.index[todo].tolist()
    if args.limit is not None:
        pending = pending[: args.limit]
    drop_exclusions(cfg, "document", set(registry.loc[pending, "document_id"]), stages_from("filter"))

    for col in ("domain_score", "noise_ratio"):
        if col not in registry.columns:
            registry[col] = ""
    ok = excluded = 0
    reasons: Counter = Counter()
    mismatched = []
    for idx in pending:
        row = registry.loc[idx]
        m = measure(row, read(row["cleaned_path"]), scorer, cfg, seed)
        for key, value in m.items():
            registry.loc[idx, key] = str(value)
        if row["source_type"] != "code" and m["language"] != row["language"]:
            mismatched.append(f"{row['document_id']}:{row['language']}->{m['language']}")
        failure = exclusion(row, m, cfg)
        if failure:
            reason, detail = failure
            registry.loc[idx, ["status", "exclusion_stage", "exclusion_reason", "exclusion_detail", "split"]] = \
                ["excluded", "filter", reason, detail, ""]
            log_exclusion(cfg, "document", row["document_id"], "filter", reason, detail)
            reasons[reason] += 1
            excluded += 1
        else:
            registry.loc[idx, ["status", "exclusion_stage", "exclusion_reason", "exclusion_detail", "split"]] = \
                ["filtered", "", "", "", ""]
            ok += 1

    save_registry(registry, cfg)
    if mismatched:  # kaynak listesindeki dil ile tespit edilen dil farklı: gözle kontrol için
        logger.info("Dili kaynak listesinden farklı tespit edilen %d doküman: %s", len(mismatched), ", ".join(mismatched))
    logger.info("Eleme sebepleri: %s", dict(reasons))
    log_summary(logger, len(pending), ok, 0, excluded)


if __name__ == "__main__":
    main()
