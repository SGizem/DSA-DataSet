"""04_filter ölçümlerinin ve eleme sırasının testleri."""
import importlib
import random

import pandas as pd

from scripts.utils.text_utils import tr_lower

f = importlib.import_module("scripts.04_filter")
CFG = {"filter": {"min_chars": {"prose": 500, "code": 150}, "allowed_languages": ["tr", "en"],
                  "max_noise_ratio": 0.15, "domain_score_threshold": 10.0, "language_samples": 5,
                  "language_sample_chars": 1000, "language_min_prose_chars": 200,
                  "out_of_scope_urls": {"https://x.org/wiki/T-tree": "veritabanı iç yapısı"}}}


def row(source_type: str = "html", url: str = "https://x.org/wiki/Quicksort") -> pd.Series:
    return pd.Series({"document_id": "DOC_000001", "source_type": source_type, "url": url})


def metrics(**kw) -> dict:
    base = {"language": "en", "char_count": 5000, "word_count": 800, "noise_ratio": 0.0, "domain_score": 50.0}
    return {**base, **kw}


def test_turkish_lowercase():
    assert tr_lower("İKİLİ ARAMA AĞACI") == "ikili arama ağacı"
    assert tr_lower("ISIL") == "ısıl"


def test_math_symbols_are_not_noise_but_decorations_are():
    assert f.noise_ratio("O(n²) ≤ ∑ x_i → ∞, $O(n^2)$") == 0.0
    assert f.noise_ratio("▲♕") == 1.0


def test_exclusion_order_follows_brief():
    # Hem kısa hem yanlış dilde: ilk kural (too_short) yazılır.
    assert f.exclusion(row(), metrics(char_count=100, language="de"), CFG)[0] == "too_short"
    assert f.exclusion(row(), metrics(language="de"), CFG)[0] == "wrong_language"
    assert f.exclusion(row(), metrics(noise_ratio=0.2), CFG)[0] == "too_much_noise"
    assert f.exclusion(row(), metrics(domain_score=3.0), CFG)[0] == "out_of_domain"
    assert f.exclusion(row(), metrics(), CFG) is None


def test_code_has_its_own_length_limit_and_no_domain_score():
    assert f.exclusion(row("code"), metrics(char_count=200, language="code", domain_score=""), CFG) is None
    assert f.exclusion(row("code"), metrics(char_count=120, language="code"), CFG)[0] == "too_short"


def test_manually_reviewed_out_of_scope_page_is_excluded_with_its_reason():
    reason, detail = f.exclusion(row(url="https://x.org/wiki/T-tree"), metrics(), CFG)
    assert reason == "out_of_domain" and "veritabanı iç yapısı" in detail


def test_domain_terms_match_word_starts_and_count_overlaps_once():
    pattern = f.term_pattern(["hash table", "hash", "algoritma"])
    assert len(pattern.findall("a hash table uses hashing")) == 2       # "hash table" bir kez, "hashing" bir kez
    assert len(pattern.findall("algoritmaları ve logaritma")) == 1      # "logaritma" kelime başında değil


def test_language_is_majority_vote_and_reproducible():
    text = ("Bu bir sıralama algoritmasıdır ve diziyi küçükten büyüğe doğru sıralar. " * 40)
    first = f.detect_language(text, random.Random("42:DOC_1"), 5, 1000)
    again = f.detect_language(text, random.Random("42:DOC_1"), 5, 1000)
    assert first == again == "tr"


def test_subtopic_prefers_title_and_breaks_title_ties_with_body():
    s = f.Scorer({"paths": {"domain_keywords": "config/domain_keywords.yaml", "subtopics": "config/subtopics.yaml"}})
    recursion_chapter = "recursion tree " * 3 + "tree " * 20
    assert s.subtopic(recursion_chapter, "en", "Recursion") == "ozyineleme_ve_dp"  # gövdede "tree" çok olsa da
    heapsort = "sıralama algoritması " * 10 + "yığın " * 3
    assert s.subtopic(heapsort, "tr", "Yığın sıralaması") == "siralama_ve_arama"   # başlık eşit: gövde karar verir
    assert s.subtopic("a b c", "en", "Something") == "genel"
