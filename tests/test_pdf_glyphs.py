"""PDF glif adı -> metin çevirisinin testleri (scripts/utils/pdf_glyphs.py)."""
from scripts.utils.pdf_glyphs import UNMAPPED, glyph_text, resolve_glyph


def test_math_symbols_resolve_regardless_of_size_variant():
    assert glyph_text("summationdisplay") == "∑"
    assert glyph_text("summationtext") == "∑"
    assert glyph_text("radicallow") == "√"
    assert glyph_text("radicalbig1") == "√"
    assert glyph_text("nequal") == "≠"
    assert glyph_text("shortrightarrow") == "→"


def test_big_delimiters_become_plain_delimiters():
    assert glyph_text("parenleftbig6") == "("
    assert glyph_text("parenrightBigg") == ")"
    assert glyph_text("bracketleftbig1") == "["
    assert glyph_text("floorleftbig1") == "⌊"


def test_multi_piece_delimiter_keeps_only_top_piece():
    # Uzun bir sol süslü parantez dört parçadan çizilir; metinde tek '{' kalmalı.
    pieces = ["bracelefttp", "braceex", "braceleftmid", "braceex", "braceleftbt"]
    assert "".join(glyph_text(p) for p in pieces) == "{"


def test_scaffolding_is_dropped_and_unknown_is_flagged():
    assert glyph_text("bracehext") == ""
    assert glyph_text("bracehtipdownleft") == ""
    assert glyph_text("d15") == UNMAPPED  # bilinmeyen ad rastgele bir harfe dönüşmez


def test_resolve_uses_truncated_font_name_and_refuses_to_guess():
    fonts = {"MathDesign-CH-Regular-Extension-10": [["parenleftbig1", "summationdisplay"]]}
    assert resolve_glyph(fonts, "MathDesign-CH-Regular-Ex", 1) == "∑"
    # Kısaltılmış ada iki font uyuyor ve aynı glif kimliği için farklı şey söylüyorsa çözülmez.
    ambiguous = {"Font-MathA": [["nequal"]], "Font-MathB": [["summationtext"]]}
    assert resolve_glyph(ambiguous, "Font-Math", 0) == UNMAPPED
    assert resolve_glyph(fonts, "Bilinmeyen-Font", 0) == UNMAPPED
