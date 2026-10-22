"""Temizleme kurallarının testleri (FAZ 3'ün beş temel testi + ölçümlerde bulunan tuzaklar)."""
from collections import Counter

from scripts.utils.text_utils import (clean_text, is_code_like, r1_unicode, r2_control, r3_r4_pages,
                                      r6_hyphenation, r8_trailing_sections, r9_join_short_runs)

CFG = {"clean": {"repeated_line_min_pages": 5, "page_edge_lines": 2, "boilerplate_lines": ["Home", "Görünüm"],
                 "reference_section_domains": ["wikipedia.org"],
                 "trailing_sections": ["References", "See also", "Notes", "Kaynakça"],
                 "trailing_section_max_line_chars": 60, "short_line_max_chars": 3, "short_line_run_min": 4}}
WIKI = "https://en.wikipedia.org/wiki/Quicksort"
BOOK = "https://example.org/book.pdf"


def clean(text: str, source_type: str = "html", url: str = BOOK, vocabulary: Counter | None = None) -> str:
    return clean_text(text, source_type, url, CFG, vocabulary or Counter())[0]


# --- Temel testler ------------------------------------------------------------------
def test_complexity_notation_is_unchanged():
    sentence = "Zaman karmaşıklığı O(n²) ve O(n log n)'dir."
    assert clean(sentence + "\n") == sentence + "\n"


def test_python_indentation_is_kept():
    code = "def toplam(dizi):\n    s = 0\n    for x in dizi:\n        s += x\n    return s\n"
    assert clean("Örnek fonksiyon:\n" + code) == "Örnek fonksiyon:\n" + code


def test_standalone_page_number_is_removed_but_not_inside_a_sentence():
    pages = "Birinci sayfanın metni burada.\nSayfa 12\fBu cümlede Sayfa 12 geçiyor ve kalmalı.\n"
    assert clean(pages, "pdf") == "Birinci sayfanın metni burada.\nBu cümlede Sayfa 12 geçiyor ve kalmalı.\n"


def test_line_repeated_on_six_pages_is_removed_but_two_pages_is_kept():
    pages = []
    for i in range(6):
        heading = "Bölüm Özeti" if i < 2 else f"Gövde başlığı {i}"
        pages.append(f"Veri Yapıları Ders Notu\n{heading}\nSayfa {i + 1} üzerindeki açıklama cümlesi.")
    out = clean("\f".join(pages), "pdf")
    assert "Veri Yapıları Ders Notu" not in out   # 6 sayfanın başında: sayfa başlığı
    assert out.count("Bölüm Özeti") == 2          # yalnızca 2 sayfada: kalır


def test_line_end_hyphen_is_joined():
    assert clean("algo-\nritma") == "algoritma\n"


# --- Ölçümlerde bulunan tuzaklar ---------------------------------------------------------------
def test_repeated_body_lines_are_not_headers():
    # Erickson'da "mark v" gibi sözde kod satırları ve "∑" formül parçaları her sayfanın gövdesinde tekrar eder.
    # Sayfalar rakamla değil kelimeyle ayrışmalı: karşılaştırmada rakamlar # olur ("Page 12" ~ "Page 13").
    words = ["kök", "yaprak", "düğüm", "kenar", "yığın", "kuyruk"]
    pages = [f"Bölüm başı\nGiriş {w}.\nmark v\n∑\nAra {w}.\nSon {w}." for w in words]
    out, r3, r4 = r3_r4_pages("\f".join(pages), min_pages=5, edge=2)
    assert out.count("mark v") == 6 and out.count("∑") == 6
    assert "Bölüm başı" not in out and r4 == 6 * len("Bölüm başı") and r3 == 0


def test_numbers_inside_a_page_are_kept():
    # Gövdede tek başına duran sayı, alt alta dizilmiş bir kesrin paydası olabilir (n / 2).
    page = "Üst satır\nOrtalama maliyet\nn\n2\nolarak bulunur.\n17"
    out, r3, _ = r3_r4_pages(page + "\fİkinci sayfa", min_pages=5, edge=2)
    assert "n\n2\n" in out and "\n17" not in out and r3 == 2


def test_hyphen_is_kept_when_the_hyphenated_word_is_more_common():
    vocabulary = Counter({"b-tree": 12, "two-dimensional": 3})
    assert r6_hyphenation("a B-\ntree node", vocabulary) == "a B-tree node"
    assert r6_hyphenation("divide-and-\nconquer", Counter()) == "divide-and-conquer"
    assert r6_hyphenation("opera-\ntions", Counter({"operations": 4})) == "operations"
    assert r6_hyphenation("Kitap-\nBölüm", Counter()) == "Kitap-\nBölüm"  # büyük harfle başlıyor: birleşmez


def test_reference_sections_are_cut_only_when_no_prose_follows():
    text = "Giriş paragrafı.\nSee also\n- Heap\nReferences\n- Knuth, D. (1998). The Art of Computer Programming."
    assert r8_trailing_sections(text, {"See also", "References"}, 60) == "Giriş paragrafı."
    # Segment tree: "Notes" başlığından sonra içerik olan "History" bölümü geliyor -> oradan kesilmez.
    segment = ("Giriş.\nNotes\n- a note\nHistory\nThe segment tree was invented by Jon Bentley in 1977 "
               "in his solutions to Klee's rectangle problems.\nReferences\n- Bentley, J. (1977).")
    assert r8_trailing_sections(segment, {"Notes", "References"}, 60) == segment.rsplit("\nReferences", 1)[0]


def test_footnote_entries_left_in_place_are_dropped():
    # Kaynakça kesilemedi (arkasında içerik bölümü var) ama "↑" ile başlayan dipnot girdileri yine silinir.
    text = ("Giriş.\nNotes\n- ↑ Landau, E. (1924). Über die Anzahl.\n↑ Cormen et al. 2022, p. 57.\nHistory\n"
            "The structure was invented in 1977 by an author who also described its use.")
    out = r8_trailing_sections(text, {"Notes"}, 60)
    assert "Landau" not in out and "Cormen" not in out and "History\nThe structure" in out
    assert r8_trailing_sections("Okla gösterim: a ↑ b.", {"Notes"}, 60) == "Okla gösterim: a ↑ b."


def test_reference_rule_applies_only_to_wikipedia():
    text = "Giriş paragrafı.\nReferences\n- Knuth (1998)."
    assert "Knuth" not in clean(text, url=WIKI)
    assert "Knuth" in clean(text, url=BOOK)


def test_unicode_rule_keeps_superscripts_and_opens_ligatures():
    assert r1_unicode("O(n²) é ﬁle x​") == "O(n²) é file x"


def test_control_characters_and_unmapped_glyphs_are_removed():
    assert r2_control("a\x00b\r\nc\rd�\te\ff") == "ab\nc\nd\te\ff"


def test_code_documents_only_get_r2():
    code = "x  =  1   \r\n\r\n\r\n\r\n\r\ny = 2\n"
    assert clean(code, "code") == "x  =  1   \n\n\n\n\ny = 2\n"


def test_whitespace_is_collapsed_outside_code():
    assert clean("Erken     yaprak   lekesi.   \n\n\n\n\nSon.") == "Erken yaprak lekesi.\n\n\nSon.\n"
    assert is_code_like("    x = f(y)") and not is_code_like("For example, a list.")


def test_number_at_page_edge_is_kept_when_it_does_not_fit_page_numbering():
    # Erickson s. 79: dizinin son elemanı "9", sayfa numarası "61"in hemen üstüne düşüyor.
    pages = [f"Metin satırı {w}.\nikinci satır {w}\n{60 + k}" for k, w in enumerate(["bir", "iki", "üç"])]
    pages[1] = "Dizi şöyle:\n6\n9\n61"
    out, r3, _ = r3_r4_pages("\f".join(pages), min_pages=5, edge=2)
    assert "\n9\n" in out + "\n"  # 9 - 1 = 8, numaralama farkı 60 değil: içerik, kalır
    assert "60" not in out and "61" not in out and "62" not in out


def test_short_line_runs_are_joined_only_in_pdf_text():
    figure = "Recurse Right:\nI\nN\nO\nR\nS\nT\nMerge:\nA\nE"
    assert r9_join_short_runs(figure, 3, 4) == "Recurse Right:\nI N O R S T\nMerge:\nA\nE"  # 2 satırlık dizi kalır
    page = "Sayfa metni burada.\nS\nO\nR\nT\fİkinci sayfa metni."
    assert "S O R T" in clean(page, "pdf")
    ascii_tree = "Ağaç:\n1\n/\n2\n\\\n3"
    assert clean(ascii_tree, "html") == ascii_tree + "\n"  # HTML'de ASCII çizim bozulmaz
