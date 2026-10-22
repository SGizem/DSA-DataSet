"""05_deduplicate testleri: exact, near, kalan doküman seçimi ve shingle kuralları."""
import importlib
import random

d = importlib.import_module("scripts.05_deduplicate")
CFG = {"dedup": {"shingle_words": 5, "minhash_num_perm": 128, "jaccard_threshold": 0.85, "lsh_threshold": 0.5,
                 "source_priority": ["kitap", "wiki"]}}
VOCAB = ("dizi liste yığın kuyruk ağaç düğüm kenar graf hash tablo anahtar değer sıralama arama ikili "
         "derinlik genişlik öncelik algoritma karmaşıklık zaman bellek eleman indeks işaretçi kök yaprak "
         "yol döngü tekrar birleştirme bölme pivot dengeli yükseklik dönüş ekleme silme bulma").split()


def words(n: int, seed: int) -> str:
    """Tekrarsız sayılabilecek kadar çeşitli, seed'li yapay metin (her satır 12 kelime)."""
    rng = random.Random(seed)
    tokens = [rng.choice(VOCAB) for _ in range(n)]
    return "\n".join(" ".join(tokens[i:i + 12]) for i in range(0, n, 12))


def doc(doc_id: str, text: str, source: str = "wiki", code: bool = False) -> dict:
    return d.make_doc(doc_id, source, doc_id, text, "tr", code, CFG["dedup"]["shingle_words"])


def run(*docs: dict) -> dict:
    decisions, _, _ = d.deduplicate({x["document_id"]: x for x in docs}, CFG, seed=42)
    return decisions


def test_same_text_twice_is_duplicate():
    text = words(320, seed=1)
    decisions = run(doc("DOC_000001", text), doc("DOC_000002", text))
    assert decisions == {"DOC_000002": ("duplicate", "DOC_000001", 1.0)}


def test_case_and_whitespace_differences_are_still_exact_duplicates():
    text = words(320, seed=1)
    tr_upper = text.replace("i", "İ").replace("ı", "I").upper()  # str.upper Türkçe i'yi I yapar, ı'ya döner
    noisy = "  " + tr_upper.replace(" ", "   \t ").replace("\n", "\n\n")
    decisions = run(doc("DOC_000001", text), doc("DOC_000002", noisy))
    assert [reason for reason, _, _ in decisions.values()] == ["duplicate"]


def test_appended_source_line_makes_near_duplicate():
    # ≥300 kelimelik metin + sonuna tek satır kaynak bilgisi -> near_duplicate.
    # Aynı kaynakta uzun olan kalır, bu yüzden elenen orijinal kısa metin.
    text = words(320, seed=1)
    copy = text + "\nKaynak: ornek-site.org, erişim tarihi 01.10.2026. Sayfa 3."
    decisions = run(doc("DOC_000001", text), doc("DOC_000002", copy))
    assert list(decisions) == ["DOC_000001"]
    reason, kept, score = decisions["DOC_000001"]
    assert reason == "near_duplicate" and kept == "DOC_000002" and score >= 0.85


def test_different_texts_on_same_topic_are_kept():
    assert run(doc("DOC_000001", words(320, seed=1)), doc("DOC_000002", words(320, seed=2))) == {}


def test_kept_document_follows_source_priority_then_length_then_id():
    text = words(320, seed=1)
    longer = text + "\nKaynak: ornek-site.org, erişim tarihi 01.10.2026. Sayfa 3."
    # Kitap önce gelir, kısa olsa da kalır.
    decisions = run(doc("DOC_000001", longer, "wiki"), doc("DOC_000002", text, "kitap"))
    assert decisions["DOC_000001"][1] == "DOC_000002"
    # Aynı kaynak: uzun olan kalır.
    decisions = run(doc("DOC_000001", text), doc("DOC_000002", longer))
    assert decisions["DOC_000001"][1] == "DOC_000002"
    # Aynı kaynak, aynı metin: küçük id kalır.
    assert run(doc("DOC_000002", text), doc("DOC_000001", text)) == {"DOC_000002": ("duplicate", "DOC_000001", 1.0)}


def test_near_duplicates_chain_into_one_cluster():
    base = words(320, seed=1)
    a = doc("DOC_000001", base)
    b = doc("DOC_000002", base + "\nKaynak: birinci site. Sayfa 3.")  # en uzun: kalır
    c = doc("DOC_000003", base + "\nKaynak: ikinci site. Sayfa 4.")
    decisions = run(a, b, c)
    assert {k: v[:2] for k, v in decisions.items()} == {"DOC_000001": ("near_duplicate", "DOC_000002"),
                                                         "DOC_000003": ("near_duplicate", "DOC_000002")}


def test_code_shingles_split_on_whitespace_only():
    # Kodda `a[i]=b` tek token kalır; düzyazıda noktalama ayırıcıdır.
    assert d.shingles("x a[i]=b y z w", 5, is_code=True) == {"x a[i]=b y z w"}
    assert d.shingles("x a[i]=b y z w", 5, is_code=False) == {"x a i b y", "a i b y z", "i b y z w"}


def test_turkish_lowercase_in_normalization():
    assert d.normalize("İKİLİ  ARAMA\nAĞACI", "tr") == "ikili arama ağacı"
