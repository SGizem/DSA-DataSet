"""FAZ 2: data/raw/ altındaki dosyalardan metni çıkarır, data/extracted/ altına yazar.

Çalıştırma (proje kökünden): python -m scripts.02_extract [--config ...] [--limit N]
                              [--engine pymupdf|pdfplumber] [--compare-engines --sample 100]

- pdf: sayfalar arasına \\f (form feed) konur; FAZ 3'teki header/footer tespiti buna dayanır.
  Registry'de `pages` doluysa yalnızca o sayfa aralığı okunur.
- html: trafilatura (tablolar ve yorumlar hariç, hassasiyet öncelikli).
- txt ve code: dosya olduğu gibi okunur.
- Hata vermeden çöp üreten çıkarımlar sebep koduyla elenir (extraction_error, needs_ocr).
  OCR bu fazda yoktur.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd
import pdfplumber
import pymupdf
import trafilatura
from bs4 import BeautifulSoup

from scripts.utils.config import PROJECT_ROOT, add_common_args, load_config, resolve_path, set_seed
from scripts.utils.logging_utils import log_summary, setup_logger
from scripts.utils.pdf_glyphs import font_glyph_names, resolve_glyph
from scripts.utils.registry import (_atomic_write_csv, drop_exclusions, load_registry, log_exclusion, reached,
                                    save_registry, stages_from)

REPORT_COLUMNS = ["document_id", "engine", "pages", "chars", "seconds", "status", "reason"]
TITLE_MAX_CHARS = 120
# Sekme başlığını sayfa adından ayıran ekler: "Quicksort - Wikipedia", "Algoritma - Vikipedi".
TITLE_SITE_SEPARATORS = (" - ", " – ", " | ")
# Satır numaralı sözde kod içeren resim açıklaması: "1 function f(x) 2 set ..." (en az iki satır).
NUMBERED_CODE = re.compile(r"1 \S.*\s2 \S")
# Asal işaretleri üst simge olarak dizilir ama üs değildir: x′ olduğu gibi kalır.
PRIMES = set("′″‴'")
# Vikipedi'de madde metni olmayan kutular: gezinme, kaynakça, bilgi kutusu, içindekiler.
WIKI_NON_CONTENT = ["navbox", "reflist", "references", "sidebar", "infobox", "toc", "metadata", "hatnote"]
# IPA telaffuzu trafilatura'da düşünce kalan boş parantez: "trie (//, // ⓘ)" -> "trie". İçinde en az bir "/" ya
# da "ⓘ" olmalı: koddaki "remove()" gibi boş parantezlere dokunulmaz.
EMPTY_PRONUNCIATION = re.compile(r"\s?\((?=[^)\n]*[/ⓘ])[\s/,;ⓘ]*\)")
LEFTOVER_IPA = re.compile(r"\(//,?\s*")
# PyMuPDF'in varsayılan metin bayrakları, ligatür koruma hariç: ligatür (ﬀ ﬁ ﬂ ﬃ ﬄ) korununca
# kelime sonundaki ligatürden sonraki boşluk kayboluyor ("trade-oﬀbetween"); harflere açılınca kaybolmuyor.
PDF_TEXT_FLAGS = pymupdf.TEXTFLAGS_TEXT & ~pymupdf.TEXT_PRESERVE_LIGATURES


def page_span(pages: str, page_count: int) -> range:
    """'215-228' -> 0 tabanlı sayfa indisleri; boşsa tüm sayfalar."""
    if not pages:
        return range(page_count)
    start, end = (int(x) for x in pages.split("-"))
    return range(start - 1, min(end, page_count))


def is_unmapped(code: int) -> bool:
    """Çıkarıcının Unicode'a çeviremediği glif: U+FFFD ya da özel kullanım alanı (uzun ayraç parçaları)."""
    return code == 0xFFFD or 0xE000 <= code <= 0xF8FF


def mark_superscript(text: str) -> str:
    """Üst simgeyi TeX gösterimiyle yazar: "2" -> "^2", "n−1" -> "^{n−1}". Asal işaretleri (′) olduğu gibi kalır.

    Neden: PDF'te üs yalnızca küçük ve yukarıda dizilmiş yazıdır; düz metne "O(n2)", "2n" olarak geçer
    ve 2n (doğrusal) ile 2^n (üstel) ayırt edilemez.
    """
    core = text.strip()
    if not core or set(core) <= PRIMES:
        return text
    lead, trail = text[:len(text) - len(text.lstrip())], text[len(text.rstrip()):]
    return f"{lead}^{core if len(core) == 1 else '{' + core + '}'}{trail}"


def pymupdf_page_text(page: pymupdf.Page, font_names: dict[str, list[list[str]]],
                      superscripts: bool = True) -> str:
    """Sayfa metni, satır satır. Unicode karşılığı olmayan glifler fontun glif adından çözülür;
    üst simgeler ^ ile işaretlenir.

    Çözülemeyen glif asla rastgele bir harfe dönüşmez: U+FFFD olur, sayılır ve FAZ 3'te silinir.
    superscripts=False: üst simge işaretlemesi olmadan (yalnızca doğrulama için).
    """
    # Sorunlu gliflerin konumu -> (font, glif kimliği). Konum, aynı karakteri metin akışında bulmak için.
    unmapped = {(round(origin[0], 2), round(origin[1], 2)): (span["font"], gid)
                for span in page.get_texttrace()
                for code, gid, origin, _bbox in span["chars"] if is_unmapped(code)}
    lines = []
    for block in page.get_text("rawdict", flags=PDF_TEXT_FLAGS)["blocks"]:
        for line in block.get("lines", []):
            # Yan yana üst simge parçaları tek üs sayılır: "n" "−" "1" -> ^{n−1}
            groups: list[list[Any]] = []
            for span in line["spans"]:
                text = "".join(resolve_glyph(font_names, *unmapped[key]) if (key := (
                    round(ch["origin"][0], 2), round(ch["origin"][1], 2))) in unmapped else ch["c"]
                    for ch in span["chars"])
                raised = superscripts and bool(span["flags"] & pymupdf.TEXT_FONT_SUPERSCRIPT)
                if groups and groups[-1][0] == raised:
                    groups[-1][1] += text
                else:
                    groups.append([raised, text])
            lines.append("".join(mark_superscript(text) if raised else text for raised, text in groups))
    return "\n".join(lines) + "\n" if lines else ""


def extract_pdf(path: Path, pages: str, engine: str) -> tuple[str, int]:
    """PDF metnini sayfalar arasında \\f ile döndürür. Döner: (metin, okunan sayfa sayısı)."""
    if engine == "pymupdf":
        with pymupdf.open(path) as doc:
            span = page_span(pages, doc.page_count)
            font_names = font_glyph_names(doc, span)
            return "\f".join(pymupdf_page_text(doc[i], font_names) for i in span), len(span)
    with pdfplumber.open(path) as pdf:
        span = page_span(pages, len(pdf.pages))
        return "\f".join(pdf.pages[i].extract_text() or "" for i in span), len(span)


def pdf_title(path: Path, pages: str) -> str:
    """PDF meta başlığı; sayfa aralığı verilmişse o sayfada başlayan içindekiler girdisi eklenir.

    Bir kitabın bölümleri aynı meta başlığı paylaşır; bölüm adı içindekiler ağacından gelir.
    Meta başlık yoksa ilk sayfadaki en büyük puntolu yazı alınır: ilk satır çoğu kez başlık değil,
    bölüm başı alıntısıdır.
    """
    with pymupdf.open(path) as doc:
        meta = (doc.metadata.get("title") or "").strip()
        if pages:
            start = int(pages.split("-")[0])
            chapter = next((title.strip() for _, title, page in doc.get_toc() if page == start), "")
            return ": ".join(part for part in (meta, chapter) if part)
        if meta or not doc.page_count:
            return meta
        spans = [(span["size"], " ".join(span["text"].split()))
                 for block in doc[0].get_text("dict")["blocks"] for line in block.get("lines", [])
                 for span in line["spans"]]
        titles = [(size, text) for size, text in spans
                  if 3 <= len(text) <= TITLE_MAX_CHARS and any(ch.isalpha() for ch in text)]
        return max(titles)[1] if titles else ""


def unmapped_count(text: str) -> int:
    """Metne çevrilemeyen karakter sayısı: bilginin sessizce kaybolduğu yerler.

    U+FFFD: çözülemeyen bayt ya da glif. U+FFFF: PDF'in kendi tablosunda "karşılığı yok" diye
    işaretlenmiş glif. Kontrol ve özel kullanım karakterleri: fontun ham kodu metne sızmış demektir.
    """
    return sum(ch in "�￿" or (unicodedata.category(ch) in ("Cc", "Co") and ch not in "\n\t\f\r")
               for ch in text)


def wiki_math_tex(element: Any) -> str:
    r"""Bir Vikipedi matematik öğesinin TeX kaynağı ("O(n\log n)").

    Önce yazarın girdiği kaynak (data-mw), yoksa MathML'deki alttext ("{\displaystyle ...}" sarmalayıcısı atılır).
    """
    try:
        tex = json.loads(element.get("data-mw") or "{}").get("body", {}).get("extsrc") or ""
    except json.JSONDecodeError:
        tex = ""
    if not tex and (math := element.find("math")) is not None:
        tex = math.get("alttext") or ""
        wrapper = "{\\displaystyle"
        if tex.startswith(wrapper) and tex.endswith("}"):
            tex = tex[len(wrapper):-1]
    return " ".join(tex.split())


def replace_wiki_math(soup: BeautifulSoup) -> int:
    """Vikipedi matematik öğelerini TeX kaynaklarıyla değiştirir. Döner: değiştirilen öğe sayısı.

    Neden: Vikipedi formülleri MathML + resim olarak verir; trafilatura ikisini de atar ve
    "takes O(n log n) comparisons" cümlesi sessizce "takes comparisons" olur. Satır içi formül
    $...$, ayrı satırdaki formül $$...$$ olarak yazılır (LaTeX'in yaygın gösterimi).
    """
    elements = soup.select("span.mwe-math-element")
    for element in elements:
        tex = wiki_math_tex(element)
        block = "mwe-math-element-block" in (element.get("class") or [])
        element.replace_with(f"\n$${tex}$$\n" if block else f"${tex}$")
    return len(elements)


def mark_html_scripts(soup: BeautifulSoup) -> int:
    """Formül dışındaki <sup>/<sub> etiketlerini PDF'teki gibi TeX gösterimiyle yazar. Döner: işaretlenen sayısı.

    "2<sup>n</sup>" -> "2^n", "log<sub>2</sub>" -> "log_2", "x<sub>i+1</sub>" -> "x_{i+1}".
    Neden: Vikipedi üsleri ve indisleri çoğu zaman formül olarak değil bu etiketlerle yazar; trafilatura
    etiketi atıp metni bırakınca 2^n (üstel) ile 2n (doğrusal), n² ile n2 ayırt edilemez. Yalnızca sınıfsız
    etiketler işaretlenir: dipnot ("[1]", class="reference") ve şablon ("[citation needed]", class="noprint")
    işaretleri sınıflıdır ve olduğu gibi kalır.
    """
    tags = [t for t in soup.find_all(["sup", "sub"]) if not t.get("class") and t.get_text().strip()]
    for tag in tags:
        text = tag.get_text()
        marked = mark_superscript(text)
        if tag.name == "sub":
            marked = marked.replace("^", "_", 1)
        tag.replace_with(marked)
    return len(tags)


def remove_wiki_references(soup: BeautifulSoup) -> int:
    """Vikipedi'nin kaynak ve şablon işaretlerini siler: "[1]", "[4]: 459", "[a]", "[citation needed]",
    "[according to whom?]" ve ses dosyası işaretleri. Döner: silinen işaret sayısı.

    Neden: işaretlerin gösterdiği kaynakça listesi temizlemede (R8) kesiliyor; işaretler hiçbir şeye
    bağlanmadan metinde kalıyordu (manuel kontrolde 22.10.2026: corpus'ta 6.488 işaret, "örneğidir.[1]").
    """
    marks = soup.select("sup.reference, sup.mw-ref, sup.noprint, sup.Inline-Template, sup.ext-phonos-attribution")
    for mark in marks:
        mark.decompose()
    return len(marks)


def unwrap_list_links(soup: BeautifulSoup) -> int:
    """Vikipedi madde gövdesindeki liste öğelerinde bağlantıları düz metne çevirir (metin aynen kalır).

    Neden: trafilatura bağlantı yoğunluğu yüksek blokları gezinme menüsü sayıp atıyor; yalnızca bağlantılardan
    oluşan listeler ("Examples of addressable heaps include: Fibonacci heaps, Binomial heaps") kayboluyordu.
    Ölçüm (451 Vikipedi maddesi): ':' ile biten paragraftan sonraki listelerin 25/507'si kayıptı, bu işlemle
    10/507. Gezinme kutuları, kaynakça ve bilgi kutularına dokunulmaz. Döner: düz metne çevrilen bağlantı sayısı.
    """
    count = 0
    for item in soup.select("div.mw-parser-output li"):
        if item.find_parent(class_=WIKI_NON_CONTENT):
            continue
        for link in item.find_all("a"):
            link.unwrap()
            count += 1
    return count


def plain_wiki_code(soup: BeautifulSoup) -> int:
    """Vikipedi'nin sözdizimi renklendirilmiş kod bloklarını düz metne çevirir; satır numaralarını atar.

    Neden: renklendirme her belirteci ayrı <span>'a koyuyor; trafilatura bazı blokları (Batcher odd–even
    mergesort, Overlapping subproblems) tamamen atıyor, satır numaralı bloklarda (mw-highlight-lines) girintiyi
    siliyordu (İkili arama ağacı'nın Python kodu). Düz metin bloğu hem tam hem girintili geliyor.
    Döner: düz metne çevrilen blok sayısı.
    """
    blocks = soup.select("div.mw-highlight pre")
    for pre in blocks:
        for number in pre.select("span.linenos"):
            number.decompose()
        pre.string = pre.get_text()
    return len(blocks)


def unwrap_code_tables(soup: BeautifulSoup) -> int:
    """İçinde kod bloğu olan Vikipedi tablolarını açar: hücreler sırayla ayrı bloklar olur.

    Neden: bazı maddeler kodu yan yana göstermek için düzen tablosu kullanıyor (yinelemeli / özyinelemeli
    sürüm, farklı diller). Tablolar çıkarımda kapsam dışı (include_tables=False) olduğu için bu kodlar
    kayboluyordu: 9 maddede 40 tablo (AVL tree, Binary search tree, Recursion, Trie, İkili arama algoritması...).
    Veri tablolarına (karmaşıklık tabloları vb.) dokunulmaz. Döner: açılan tablo sayısı.
    """
    tables = [t for t in soup.select("div.mw-parser-output table") if t.find("pre") and not t.find_parent("table")]
    for table in tables:
        box = soup.new_tag("div")
        for cell in table.find_all(["th", "td"]):
            if cell.find_parent("table") is not table:
                continue
            block = soup.new_tag("div")
            for child in list(cell.children):
                block.append(child.extract())
            box.append(block)
            # Ayraç paragrafı: trafilatura art arda gelen iki kod bloğunu tek satırda birleştiriyordu
            # ("preorder(node.right) procedure iterativePreorder(node)"). Sıfır genişlikli boşluk R1'de silinir.
            separator = soup.new_tag("p")
            separator.string = "​"
            box.append(separator)
        table.replace_with(box)
    return len(tables)


def fix_wiki_radicals(soup: BeautifulSoup) -> int:
    """{{radic}} şablonunda kök altındaki ifadeyi korur: "√n", birden çok parçalıysa "√(n log n)".

    Neden: kök altı, üstü çizili (border-top) bir <span> içinde; trafilatura bu span'ı atıyor ve "O(√n)"
    metne "O(√)" olarak giriyordu (22 sayfa). Döner: düzeltilen kök sayısı.
    """
    spans = soup.find_all("span", style=re.compile(r"border-top"))
    for span in spans:
        inner = " ".join(span.get_text(" ").split())
        span.replace_with(inner if len(inner.split()) <= 1 else f"({inner})")
    return len(spans)


def remove_empty_anchors(soup: BeautifulSoup) -> int:
    """Vikipedi'nin içi boş çapa etiketlerini siler. Döner: silinen sayısı.

    İki tür: paragraf başındaki <span class="anchor" id="..."> ve Türkçe karakterli başlıkların
    ("Kaynakça") içindeki <span typeof="mw:FallbackId">. Neden: trafilatura bu etiketi atarken
    arkasından gelen metni de atıyor; paragraf ya da başlık sessizce kayboluyor. Etiket boş olduğu
    için silmek metne dokunmaz.
    """
    anchors = [a for a in soup.select('span.anchor, span[typeof="mw:FallbackId"]') if not a.get_text(strip=True)]
    for anchor in anchors:
        anchor.decompose()
    return len(anchors)


def unwrap_wiki_headings(soup: BeautifulSoup) -> int:
    """Vikipedi bölüm başlıklarını (h2, h3 ...) saran kutuyu açar, yanındaki "[düzenle]" bağlantısını siler.

    Neden: trafilatura başlıkları saran <div class="mw-heading"> kutusunu süs öğesi sayıp başlıkla
    birlikte atıyor; "History", "References" gibi başlıklar metne hiç girmiyordu. Başlıklar hem
    kaynakça bölümlerini ayırmak (FAZ 3, R8) hem de bölüm sınırında parçalama (chunk) için gerekli.
    Döner: açılan başlık sayısı.
    """
    for edit in soup.select("span.mw-editsection"):
        edit.decompose()
    headings = soup.select("div.mw-heading")
    for box in headings:
        box.unwrap()
    return len(headings)


def split_numbered_lines(alt: str) -> list[str]:
    """"1 function f(x) 2 set c to 0 3 return c" -> ["1 function f(x)", "2 set c to 0", "3 return c"].

    Satır numaraları sırayla aranır (2, 3, 4 ...); kodun içindeki sayılar sıradaki numara değilse bölünmez.
    """
    starts, number = [0], 2
    while match := re.search(rf"\s{number}\s", alt[starts[-1]:]):
        starts.append(starts[-1] + match.start() + 1)
        number += 1
    return [alt[a:b].strip() for a, b in zip(starts, starts[1:] + [len(alt)])]


def pseudocode_images_to_text(soup: BeautifulSoup) -> int:
    """Sözde kodu resim olarak veren sayfalarda resmi, açıklama metnindeki (alt) kodla değiştirir.

    Neden: Open Guide sözde kodları resim olarak veriyor; metne hiç girmiyorlardı. Resmin alt metni
    kodun satır numaralı tam yazımı. Yalnızca "1 ... 2 ..." biçimindeki alt metinler sayılır;
    "image" ya da şekil açıklamaları dokunulmadan kalır. Girinti alt metinde olmadığı için kaybolur.
    Döner: metne çevrilen resim sayısı.
    """
    count = 0
    for img in soup.find_all("img"):
        alt = " ".join((img.get("alt") or "").split())
        if not NUMBERED_CODE.match(alt):
            continue
        block = soup.new_tag("pre")
        block.string = "\n".join(split_numbered_lines(alt))
        # Resmi saran kutu, trafilatura'da süs öğesi sayılıp atılıyor; kutuda yalnızca resim varsa kutu değişir.
        wrapper = img.parent
        target = wrapper if wrapper is not None and wrapper.name in ("div", "figure", "p") \
            and not wrapper.get_text(strip=True) and len(wrapper.find_all("img")) == 1 else img
        target.replace_with(block)
        count += 1
    return count


def html_title(soup: BeautifulSoup, title: str) -> str:
    """Sekme başlığındaki site adı ekini atar ("Quicksort - Wikipedia" -> "Quicksort").

    Site adını koda gömmemek için sayfanın kendi ana başlıklarına (h1) bakılır: sekme başlığı
    bir h1 metni + ayırıcı + ek biçimindeyse h1 alınır; değilse başlık olduğu gibi kalır.
    """
    for h1 in soup.find_all("h1"):
        heading = " ".join(h1.get_text().split())  # ayırıcısız: "<i>d</i>-ary heap" -> "d-ary heap"
        if heading and any(title.startswith(heading + sep) for sep in TITLE_SITE_SEPARATORS):
            return heading
    return title


def first_meaningful_line(text: str) -> str:
    """Harf içeren ve başlık olabilecek kadar kısa ilk satır."""
    for line in text.replace("\f", "\n").splitlines():
        line = " ".join(line.split())
        if 3 <= len(line) <= TITLE_MAX_CHARS and any(ch.isalpha() for ch in line):
            return line
    return ""


YEAR = re.compile(r"\b(?:19|20)\d{2}\b")


def last_edit_year(soup: BeautifulSoup) -> str:
    """MediaWiki sayfasının alt bilgisindeki son düzenleme yılı: indirilen sürümün yayımlandığı yıl.

    "This page was last edited on 10 August 2026" / "Sayfa en son 09.01, 8 Mayıs 2024 tarihinde değiştirildi."
    Alt bilgi yoksa (wiki olmayan sayfa) boş döner; yıl tahmin edilmez.
    """
    footer = soup.find(id="footer-info-lastmod")
    match = YEAR.search(footer.get_text(" ")) if footer else None
    return match.group(0) if match else ""


def extract_document(path: Path, source_type: str, pages: str, engine: str) -> dict[str, Any]:
    """Tek dosyadan metin ve başlık çıkarır. Döner: text, title, pages, engine, detail, year."""
    if source_type == "pdf":
        text, page_count = extract_pdf(path, pages, engine)
        unmapped = unmapped_count(text)
        return {"text": text, "title": pdf_title(path, pages), "pages": page_count, "engine": engine,
                "detail": f"unmapped_chars={unmapped}" if unmapped else "", "year": ""}
    if source_type == "html":
        html = path.read_bytes()
        soup = BeautifulSoup(html, "html.parser")
        changes = {"refs": remove_wiki_references(soup), "math": replace_wiki_math(soup),
                   "radicals": fix_wiki_radicals(soup), "code": plain_wiki_code(soup),
                   "code_tables": unwrap_code_tables(soup),
                   "scripts": mark_html_scripts(soup),
                   "anchors": remove_empty_anchors(soup), "list_links": unwrap_list_links(soup),
                   "headings": unwrap_wiki_headings(soup), "code_images": pseudocode_images_to_text(soup)}
        # Değişiklik yoksa orijinal bayt verilir: çıktı, sayfanın yeniden yazılmasından hiç etkilenmez.
        doc = trafilatura.bare_extraction(str(soup) if any(changes.values()) else html, include_tables=False,
                                          include_comments=False, favor_precision=True, with_metadata=True)
        text = EMPTY_PRONUNCIATION.sub("", (doc.text or "") if doc else "")
        text = LEFTOVER_IPA.sub("(", text)  # "(//, DYKE-strəz)" -> "(DYKE-strəz)": okunuş ipucu kalır
        return {"text": text, "title": html_title(soup, doc.title or "") if doc else "",
                "pages": "", "engine": "trafilatura",
                "detail": ";".join(f"{k}={v}" for k, v in changes.items() if v), "year": last_edit_year(soup)}
    # txt ve code: çıkarım yok, dosya olduğu gibi okunur. UTF-8 olmayan baytlar � olur ve sayılır.
    text = path.read_bytes().decode("utf-8", errors="replace")
    replaced = text.count("�")
    # Kodda ilk satır (import, shebang) başlık değildir; dosya adı dokümanı daha iyi tanıtır.
    return {"text": text, "title": path.name if source_type == "code" else "", "pages": "", "engine": "raw",
            "detail": f"replaced_bytes={replaced}" if replaced else "", "year": ""}


def failure_reason(text: str, source_type: str, cfg: dict[str, Any]) -> tuple[str, str] | None:
    """Hata vermeyen ama kullanılamaz çıktıyı yakalar. Döner: (sebep kodu, ayrıntı) veya None."""
    ex = cfg["extract"]
    stripped = text.strip()
    if source_type == "pdf" and not stripped:
        return "needs_ocr", "metin katmanı boş (taranmış görüntü olabilir)"
    if source_type == "html" and not stripped:
        return "extraction_error", "sayfadan metin çıkmadı"
    # Kısalık eşiği yalnızca gerçekten çıkarım yapılan türlerde: txt/code'da kısa dosya hata değil,
    # FAZ 4'ün too_short kuralının işidir.
    if source_type in ("pdf", "html") and len(stripped) < ex["min_extracted_chars"]:
        # Bir kitap bölümünden 200 karakter çıkması çıkarımın bozulduğunu gösterir. Bir web sayfasında
        # ise metin çıkmış ama sayfa gerçekten kısa olabilir (taslak madde): sebep kodu bunu ayırır.
        reason = "extraction_error" if source_type == "pdf" else "too_short"
        return reason, f"chars={len(stripped)} < {ex['min_extracted_chars']}"
    ratio = unmapped_count(text) / len(text) if text else 0.0
    if ratio > ex["replacement_char_max_ratio"]:
        return "extraction_error", f"replacement_char_ratio={ratio:.4f} > {ex['replacement_char_max_ratio']}"
    return None


def raw_path(original_path: str) -> Path:
    path = Path(original_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def stored_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def compare_engines(registry: pd.DataFrame, cfg: dict[str, Any], sample: int, seed: int, logger) -> None:
    """Seed'li rastgele PDF örnekleminde iki motoru çalıştırır; registry'ye dokunmaz."""
    pdfs = registry[registry["source_type"] == "pdf"].to_dict("records")
    chosen = random.Random(seed).sample(pdfs, min(sample, len(pdfs)))
    rows = []
    for engine in ("pymupdf", "pdfplumber"):
        success = unmapped = 0
        started = time.perf_counter()
        for row in chosen:
            try:
                text, _ = extract_pdf(raw_path(row["original_path"]), row["pages"], engine)
                success += failure_reason(text, "pdf", cfg) is None
                unmapped += unmapped_count(text)
            except Exception:  # bozuk PDF: bu motor için başarısız sayılır
                pass
        rows.append({"engine": engine, "sample_size": len(chosen), "success_count": success,
                     "total_seconds": round(time.perf_counter() - started, 2), "unmapped_chars": unmapped})
        logger.info("%s | örneklem=%d | başarılı=%d | %.2f sn | çevrilemeyen karakter=%d",
                    engine, len(chosen), success, rows[-1]["total_seconds"], unmapped)
    _atomic_write_csv(pd.DataFrame(rows), resolve_path(cfg, "engine_comparison"))


def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description=__doc__.splitlines()[0]))
    parser.add_argument("--engine", choices=["pymupdf", "pdfplumber"], default=None,
                        help="PDF motoru (varsayılan: config.extract.engine)")
    parser.add_argument("--compare-engines", action="store_true",
                        help="İki PDF motorunu örneklemde karşılaştırıp engine_comparison.csv yazar")
    parser.add_argument("--sample", type=int, default=100, help="--compare-engines için PDF sayısı")
    parser.add_argument("--redo", action="store_true",
                        help="İndirilmiş bütün dokümanları yeniden çıkar (sonraki adımda elenenler hariç)")
    args = parser.parse_args()
    cfg = load_config(args.config)
    logger = setup_logger("02_extract", cfg)
    seed = set_seed(cfg)
    engine = args.engine or cfg["extract"]["engine"]

    registry = load_registry(cfg)
    if "pages" not in registry.columns:
        registry["pages"] = ""
    if args.compare_engines:
        compare_engines(registry, cfg, args.sample, seed, logger)
        return

    extracted_dir = resolve_path(cfg, "extracted_dir")
    report_path = resolve_path(cfg, "extraction_report")
    report = (pd.read_csv(report_path, dtype=str, keep_default_na=False).set_index("document_id").to_dict("index")
              if report_path.exists() else {})

    todo = registry["status"] == "downloaded"
    if args.redo:
        # İleri adımlara geçmiş ya da ileri bir adımda elenmiş dokümanlar da yeniden çıkarılır ve "extracted"a
        # döner; sonraki adımlar onları yeniden işler (pipeline'ı bu adımdan baştan çalıştırmakla aynı küme).
        todo |= reached(registry, "extract")
    pending = registry.index[todo].tolist()
    if args.limit is not None:
        pending = pending[: args.limit]
    # Yeniden çıkarılan dokümanın bu ve sonraki adımlardaki eski eleme kayıtları silinir; gerekirse yenisi yazılır.
    drop_exclusions(cfg, "document", set(registry.loc[pending, "document_id"]), stages_from("extract"))
    ok = excluded = 0
    for idx in pending:
        row = registry.loc[idx]
        document_id, source_type = row["document_id"], row["source_type"]
        path = raw_path(row["original_path"])
        started = time.perf_counter()
        try:
            result = extract_document(path, source_type, row["pages"], engine)
            failure = failure_reason(result["text"], source_type, cfg)
        except Exception as exc:  # bozuk dosya: kütüphane ne fırlatırsa fırlatsın doküman elenir, script durmaz
            result = {"text": "", "title": "", "pages": "", "detail": "",
                      "engine": engine if source_type == "pdf" else "trafilatura" if source_type == "html" else "raw"}
            failure = ("extraction_error", f"{type(exc).__name__}: {exc}"[:300])
        seconds = round(time.perf_counter() - started, 3)

        if failure:
            reason, detail = failure
            registry.loc[idx, ["status", "exclusion_stage", "exclusion_reason", "exclusion_detail", "split"]] = \
                ["excluded", "extract", reason, detail, ""]
            log_exclusion(cfg, "document", document_id, "extract", reason, detail)
            excluded += 1
            logger.info("%s | elendi: %s (%s)", document_id, reason, detail)
        else:
            out = extracted_dir / row["source_name"] / f"{document_id}.txt"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(result["text"], encoding="utf-8", newline="")  # satır sonlarına ve \f'ye dokunma
            title = result["title"].strip() or first_meaningful_line(result["text"]) or path.name
            registry.loc[idx, ["status", "extracted_path", "title", "exclusion_stage", "exclusion_reason",
                               "exclusion_detail", "split"]] = ["extracted", stored_path(out), title, "", "", "", ""]
            # Yayın yılı indirme listesinde yoksa (Vikipedi) indirilen sürümün son düzenleme yılı yazılır.
            if not row["publication_year"] and result.get("year"):
                registry.loc[idx, "publication_year"] = result["year"]
            ok += 1
        report[document_id] = {"engine": result["engine"], "pages": result["pages"], "chars": len(result["text"]),
                               "seconds": seconds, "status": "excluded" if failure else "extracted",
                               "reason": failure[0] if failure else result["detail"]}

    save_registry(registry, cfg)
    report_df = pd.DataFrame.from_dict(report, orient="index").rename_axis("document_id").reset_index()
    if len(report_df):
        _atomic_write_csv(report_df.sort_values("document_id")[REPORT_COLUMNS], report_path)
    log_summary(logger, len(pending), ok, 0, excluded)


if __name__ == "__main__":
    main()
