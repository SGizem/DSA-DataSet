"""02_extract yardımcılarının testleri: başlık ve eleme sebebi."""
import importlib

from bs4 import BeautifulSoup

extract = importlib.import_module("scripts.02_extract")
CFG = {"extract": {"min_extracted_chars": 200, "replacement_char_max_ratio": 0.02}}


def test_site_suffix_is_dropped_only_when_page_heading_matches():
    html = BeautifulSoup('<html><h1 id="firstHeading"><span><i>d</i>-ary heap</span></h1></html>', "html.parser")
    assert extract.html_title(html, "d-ary heap - Wikipedia") == "d-ary heap"
    # h1 sekme başlığıyla örtüşmüyorsa başlık olduğu gibi kalır (site adı tahmin edilmez).
    other = BeautifulSoup("<html><h1>An Open Guide</h1><h1>Graphs</h1></html>", "html.parser")
    assert extract.html_title(other, "Algorithms - Big-O") == "Algorithms - Big-O"


def test_short_web_page_is_too_short_but_short_pdf_is_extraction_error():
    short = "Kısa ama gerçek bir madde. " * 5
    assert extract.failure_reason(short, "html", CFG)[0] == "too_short"
    assert extract.failure_reason(short, "pdf", CFG)[0] == "extraction_error"
    assert extract.failure_reason("   ", "html", CFG)[0] == "extraction_error"
    assert extract.failure_reason("", "pdf", CFG)[0] == "needs_ocr"


def test_last_edit_year_is_read_from_wiki_footer_in_both_languages():
    en = BeautifulSoup('<li id="footer-info-lastmod"> This page was last edited on 10 August 2026, at 11:19</li>',
                       "html.parser")
    tr = BeautifulSoup('<li id="footer-info-lastmod"> Sayfa en son 09.01, 8 Mayıs 2024 tarihinde değiştirildi.</li>',
                       "html.parser")
    assert extract.last_edit_year(en) == "2026"
    assert extract.last_edit_year(tr) == "2024"  # "09.01" saat, yıl sanılmaz
    assert extract.last_edit_year(BeautifulSoup("<p>Copyright 2019</p>", "html.parser")) == ""  # alt bilgi yok


def test_html_exponents_and_indices_are_marked_but_footnotes_are_not():
    html = BeautifulSoup('<p>2<sup>n</sup> ve log<sub>2</sub> n, x<sub>i+1</sub>, n<sup>2</sup>'
                         '<sup class="reference">[1]</sup><sup class="noprint Inline-Template">[citation needed]'
                         '</sup></p>', "html.parser")
    assert extract.mark_html_scripts(html) == 4
    assert html.get_text() == "2^n ve log_2 n, x_{i+1}, n^2[1][citation needed]"


def test_garbage_characters_fail_extraction():
    text = "a" * 900 + "�" * 100
    assert extract.failure_reason(text, "pdf", CFG)[0] == "extraction_error"
    assert extract.failure_reason("a" * 1000, "pdf", CFG) is None


def test_wikipedia_math_is_kept_as_tex():
    html = r"""<p>Quicksort takes <span class="mwe-math-element mwe-math-element-inline"
        data-mw='{"name":"math","body":{"extsrc":"O(n\\log n)"}}'><math alttext="{\displaystyle O(n\log n)}">
        <mi>O</mi></math><img alt="x"></span> comparisons.</p>
        <span class="mwe-math-element mwe-math-element-block"><math alttext="{\displaystyle T(n)=2T(n/2)+n}">
        </math></span>"""
    soup = BeautifulSoup(html, "html.parser")
    assert extract.replace_wiki_math(soup) == 2
    text = soup.get_text()
    assert r"takes $O(n\log n)$ comparisons." in text  # yazarın kaynağı (data-mw)
    assert "$$T(n)=2T(n/2)+n$$" in text  # data-mw yoksa alttext; \displaystyle sarmalayıcısı atılır


def test_empty_anchor_does_not_swallow_the_paragraph():
    html = ('<p><span class="anchor" id="Selection"></span>The secondary hash function should have '
            'several characteristics.</p>')
    soup = BeautifulSoup(html, "html.parser")
    assert extract.remove_empty_anchors(soup) == 1
    assert soup.get_text() == "The secondary hash function should have several characteristics."


def test_numbered_pseudocode_image_becomes_text():
    alt = "1 function countOccurrences(x, s) 2 set count to 0 3 for each character c in s 4 return count"
    html = f'<div class="wp-nocaption"><img src="a.png" alt="{alt}"></div><p><img alt="image"></p>'
    soup = BeautifulSoup(html, "html.parser")
    assert extract.pseudocode_images_to_text(soup) == 1  # "image" açıklamalı resim dokunulmaz
    assert soup.find("pre").get_text() == ("1 function countOccurrences(x, s)\n2 set count to 0\n"
                                           "3 for each character c in s\n4 return count")
    assert soup.find("img", alt="image") is not None


def test_numbers_inside_code_do_not_split_lines():
    assert extract.split_numbered_lines("1 set x to 3 2 return x") == ["1 set x to 3", "2 return x"]


def test_wiki_heading_box_is_opened_and_edit_link_dropped():
    html = ('<div class="mw-heading mw-heading2"><h2 id="History">History</h2>'
            '<span class="mw-editsection">[<a href="/w/index.php">edit</a>]</span></div><p>Text.</p>')
    soup = BeautifulSoup(html, "html.parser")
    assert extract.unwrap_wiki_headings(soup) == 1
    assert str(soup) == '<h2 id="History">History</h2><p>Text.</p>'


def test_fallback_id_span_does_not_swallow_turkish_heading():
    soup = BeautifulSoup('<h2 id="Kaynakça"><span id="Kaynak.C3.A7a" typeof="mw:FallbackId"></span>Kaynakça</h2>',
                         "html.parser")
    assert extract.remove_empty_anchors(soup) == 1
    assert str(soup) == '<h2 id="Kaynakça">Kaynakça</h2>'


def test_superscript_is_written_with_a_caret():
    assert extract.mark_superscript("2") == "^2"            # O(n2) -> O(n^2)
    assert extract.mark_superscript("n−1 ") == "^{n−1} "     # çok karakterli üs süslü parantezle, boşluk dışarıda
    assert extract.mark_superscript("′") == "′"              # asal işareti üs değildir
    assert extract.mark_superscript("  ") == "  "
