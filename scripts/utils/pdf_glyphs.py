"""PDF'te Unicode karşılığı tanımlı olmayan glifleri fontun kendi glif adından çözer.

Neden gerekli: TeX ile üretilmiş PDF'lerde matematik fontlarının bir kısmı (büyük toplam işareti,
uzun parantez parçaları, ≠ gibi) Unicode tablosu taşımaz. Metin çıkarıcı bu glifleri ya atlar ya da
yanlış bir harfe çevirir (ör. toplam işareti yerine 'X'). Glifin ne olduğu ise gömülü Type1 font
programında adıyla yazılıdır (summationdisplay, parenleftbig, nequal ...); burada o ad okunur.
"""
from __future__ import annotations

import re

import pymupdf

UNMAPPED = "�"  # çözülemeyen glif: sayılır, raporlanır, FAZ 3'te silinir

# TeX matematik fontlarındaki glif adı (boyut eki atılmış hâli) -> metin karşılığı.
GLYPH_TEXT = {
    "summation": "∑", "integral": "∫", "union": "⋃", "logicalor": "⋁", "logicaland": "⋀",
    "radical": "√", "parenleft": "(", "parenright": ")", "bracketleft": "[", "bracketright": "]",
    "braceleft": "{", "braceright": "}", "floorleft": "⌊", "floorright": "⌋",
    "ceilingleft": "⌈", "ceilingright": "⌉", "slash": "/", "barex": "|",
    "shortrightarrow": "→", "nequal": "≠", "nelement": "∉",
}
# Aynı işaretin boyut çeşitleri: summationdisplay, parenleftbig6, parenleftBigg, radicallow ...
SIZE_SUFFIX = re.compile(r"(text|display|low|big|Big|bigg|Bigg)\d*$")
# Çok parçalı uzun ayraçlar: üst parça (tp) ayracın kendisi sayılır, uzatma/orta/alt parçalar atılır.
DELIMITER_PIECE = re.compile(r"(paren|bracket|brace)(left|right)(tp|ex|bt|mid)")
# Yalnızca çizim iskelesi olan parçalar: yatay süslü parantez uçları ve uzatmaları.
SCAFFOLDING = re.compile(r"bracehtip\w*|bracehext|braceex")


def glyph_text(name: str) -> str:
    """Glif adını metne çevirir; iskele parçaları için boş string, bilinmeyen için UNMAPPED döner."""
    if SCAFFOLDING.fullmatch(name):
        return ""
    if piece := DELIMITER_PIECE.fullmatch(name):
        return GLYPH_TEXT[piece.group(1) + piece.group(2)] if piece.group(3) == "tp" else ""
    # Tabloda olmayan ad tahmin edilmez: UNMAPPED olarak sayılır; raporda görülünce tabloya eklenir.
    return GLYPH_TEXT.get(SIZE_SUFFIX.sub("", name), UNMAPPED)


def _eexec_decrypt(data: bytes) -> bytes:
    """Type1 fontların şifreli bölümünü açar (Adobe Type 1 Font Format, bölüm 7.2)."""
    r, out = 55665, bytearray()
    for byte in data:
        out.append(byte ^ (r >> 8))
        r = ((byte + r) * 52845 + 22719) & 0xFFFF
    return bytes(out[4:])  # ilk 4 bayt rastgele dolgudur


def type1_glyph_names(font_program: bytes) -> list[str]:
    """Type1 font programındaki glif adlarını glif kimliği sırasıyla döndürür; okunamazsa boş liste."""
    start = font_program.find(b"eexec")
    if start < 0:
        return []
    encrypted = font_program[start + 5:].lstrip(b" \r\n\t")
    if re.fullmatch(rb"[0-9A-Fa-f\s]{8}", encrypted[:8]):  # .pfa: şifreli bölüm hex olarak yazılır
        hex_digits = re.sub(rb"[^0-9A-Fa-f]", b"", encrypted.split(b"cleartomark")[0])
        encrypted = bytes.fromhex(hex_digits[: len(hex_digits) // 2 * 2].decode("ascii"))
    plain = _eexec_decrypt(encrypted)
    charstrings = plain[max(plain.find(b"/CharStrings"), 0):]
    names = [m.decode("ascii") for m in re.findall(rb"/([A-Za-z0-9._]+)\s+\d+\s+(?:RD|-\|)\s", charstrings)]
    # Yazı tipi motoru .notdef'i her zaman 0 numaraya alır; programda başka yerdeyse 0. glifle yer değiştirir.
    if ".notdef" in names and names[0] != ".notdef":
        k = names.index(".notdef")
        names[0], names[k] = names[k], names[0]
    return names


def font_glyph_names(doc: pymupdf.Document, pages: range) -> dict[str, list[list[str]]]:
    """Verilen sayfalardaki gömülü Type1 fontlar için: font adı -> glif adı listeleri.

    Aynı ada birden fazla font programı düşebilir (liste bu yüzden iç içe); çözüm sırasında
    hepsi aynı adı veriyorsa kullanılır.
    """
    xrefs: dict[int, str] = {}
    for pno in pages:
        for xref, _ext, font_type, basefont, *_ in doc.get_page_fonts(pno):
            if font_type == "Type1":
                xrefs[xref] = basefont.split("+")[-1]  # "ABCDEF+" alt küme önekini at
    names: dict[str, list[list[str]]] = {}
    for xref, font_name in xrefs.items():
        glyphs = type1_glyph_names(doc.extract_font(xref)[3])
        if glyphs:
            names.setdefault(font_name, []).append(glyphs)
    return names


def resolve_glyph(font_names: dict[str, list[list[str]]], trace_font: str, gid: int) -> str:
    """Çıkarıcının bildirdiği (font adı, glif kimliği) çiftini metne çevirir.

    Çıkarıcı uzun font adlarını kısaltır; bu yüzden adı o kısaltmayla başlayan tüm fontlara bakılır.
    Adaylar farklı sonuç veriyorsa tahmin yürütülmez, UNMAPPED döner.
    """
    results = {glyph_text(glyphs[gid])
               for name, programs in font_names.items() if name.startswith(trace_font)
               for glyphs in programs if gid < len(glyphs)}
    return results.pop() if len(results) == 1 else UNMAPPED
