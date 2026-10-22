"""Metin temizleme kuralları (FAZ 3) ve is_code_like.

Her kural ayrı bir fonksiyondur ve yalnızca metni döndürür; ne kadar sildiğini 03_clean.py ölçer.
Kural kimlikleri, ne yaptıkları ve gerekçeleri RULES içinde durur; reports/cleaning_rules.md
buradan üretilir. Yasaklar (FAZ 3 kararı): rakam, sembol ve stopword silinmez, küçük harfe
çevrilmez, "kısa satırı sil" kuralı yoktur.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from typing import Any
from urllib.parse import urlsplit

# (kimlik, ne yapar, neden) — sıra, uygulama sırasıdır.
RULES = [
    ("R1", "Unicode NFC; ligatürler (ﬁ ﬂ ﬀ ﬃ ﬄ) harflere açılır; NBSP boşluğa çevrilir; sıfır genişlikli "
           "boşluk, BOM ve yumuşak tire silinir",
     "Aynı kelime farklı kodlarla yazılmasın. NFKC kullanılmaz: ² karakterini 2 yapar, O(n²) anlam değiştirir"),
    ("R2", "Kontrol karakterleri silinir (\\n \\t \\f hariç); CRLF ve CR -> LF; çözülemeyen glif işaretleri "
           "(U+FFFD, U+FFFF) silinir",
     "Bozuk baytlar ve PDF'te karşılığı bulunamayan glifler bilgi taşımaz; tahminle harfe çevrilmez"),
    ("R3", "Sayfalı dokümanda (PDF) sayfanın ilk/son dolu satırlarındaki sayı, dokümanın sayfa numaralamasına "
           "uyuyorsa (sayı - sayfa sırası = dokümanda en sık görülen fark) silinir",
     "Sayfa numarası kalıntısı. Numaralamaya uymayan sayılar içeriktir: sayfa sonuna denk gelen dizi elemanı "
     "('9 7 7 2 ... 6 9' dizisinin son 9'u), şekil etiketi. Gövdedeki sayılara hiç bakılmaz"),
    ("R4", "Sayfanın ilk/son dolu satırlarında, normalize edilince (rakam -> #, küçük harf, tek boşluk) en az "
           "repeated_line_min_pages farklı sayfada tekrar eden satırlar silinir; sonra sayfalar birleştirilir",
     "Sayfa başlığı ve alt bilgisi. Yalnızca sayfa kenarı: gövdede tekrar eden satırlar sözde kod "
     "('mark v') ve formül parçasıdır ('∑')"),
    ("R5", "config.clean.boilerplate_lines ile tam eşleşen satırlar silinir", "Site menüsü ve navigasyon"),
    ("R8", "Vikipedi'de sondaki kaynakça bölümleri (References, See also, Kaynakça, Dış bağlantılar ...) silinir; "
           "kesim noktasından sonra düzyazı paragraf varsa o noktadan kesilmez. Ayrıca kesilmeyen yerlerde kalan "
           "dipnot girdileri (Vikipedi'nin geri bağlantı işareti '↑' ile başlayan satırlar) silinir",
     "Bilgi taşımayan kaynak ve bağlantı listeleri. Düzyazı denetimi: bazı maddelerde kaynakça başlığından "
     "sonra içerik bölümü geliyor (Segment tree: Notes, sonra History). '↑' corpus'ta yalnızca dipnot "
     "girdilerinin başında geçiyor (363 satırın 363'ü), içerikte kullanılmıyor"),
    ("R9", "Sayfalı dokümanda (PDF) art arda gelen kısa satırlar (en çok short_line_max_chars karakter, kod değil; "
           "en az short_line_run_min satır) boşlukla tek satırda birleştirilir. Harf ya da sembol silinmez; "
           "yalnızca satır başı/sonu boşlukları gider",
     "PDF çıkarımı aralıklı dizilmiş şekil hücrelerini ve parçalı formülleri her hücre bir satır olacak şekilde "
     "veriyor (mergesort şeklindeki 'S O R T ...' harflerinin her biri ayrı satırda). HTML'de uygulanmaz: "
     "orada kısa satırlar ASCII çizimdir (ağaç şekli)"),
    ("R6", "Satır sonu tiresi birleştirilir (sonraki satır küçük harfle başlıyorsa). Kelimenin tireli hâli "
           "corpus'ta tiresizinden sık geçiyorsa tire korunur",
     "PDF satır kırılması. Tire koruma: 'B-|tree', 'two-|dimensional' yalın kuralla 'Btree' olurdu"),
    ("R7", "Kod olmayan satırlarda ardışık boşluk/tab tek boşluğa iner, satır sonu boşlukları silinir "
           "(satır başı girintisi korunur); 3+ boş satır 2'ye iner",
     "PDF sütun hizalamasından kalan boşluklar. Girinti iç içe liste ve sözde kod yapısını taşır"),
]
CODE_ONLY_RULES = {"R2"}  # source_type=code dokümanlara yalnızca R2 uygulanır (FAZ 3 kararı)

# --- is_code_like -------------------------------------------------------------------------------
# Temel liste + sözde kodda atama okları (← :=). Kod benzeri satır R4, R6, R7'den muaftır.
CODE_TOKENS = ("{", "}", ";", "->", "==", "!=", "<=", ">=", "::", "()", "←", ":=")
# Temel liste ("gibi") + sözde kodun blok kelimeleri. Büyük/küçük harf duyarlı: "For example" kod değildir.
CODE_START = re.compile(r"^\s*(?:#include\b|(?:def|class|for|while|if|else|elif|return|int|public|void|"
                        r"function|procedure|end|do|repeat|until|import)\b)")
INDENTED = re.compile(r"^(?: {2,}|\t)")


def tr_lower(text: str) -> str:
    """Türkçe küçük harf: İ -> i, I -> ı. Python'un .lower()'ı "I"yı "i" yapar, Türkçede yanlıştır."""
    return text.replace("İ", "i").replace("I", "ı").lower()


def is_code_like(line: str) -> bool:
    """Satır kod ya da sözde kod gibi mi? Öyleyse boşluğuna ve tiresine dokunulmaz, silinmez."""
    if any(token in line for token in CODE_TOKENS) or CODE_START.match(line):
        return True
    return bool(INDENTED.match(line)) and any(ch in line for ch in "=()")


# --- R1 -----------------------------------------------------------------------------------------
UNICODE_TABLE = str.maketrans({
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st",
    " ": " ", " ": " ", " ": " ",                        # bölünmez boşluk türleri
    "​": None, "⁠": None, "﻿": None, "­": None,     # görünmez: sıfır genişlik, BOM, yumuşak tire
})


def r1_unicode(text: str) -> str:
    return unicodedata.normalize("NFC", text).translate(UNICODE_TABLE)


# --- R2 -----------------------------------------------------------------------------------------
# Cc kategorisi (U+0000-001F, U+007F-009F) eksi \t \n \f; artı çözülemeyen glif işaretleri.
CONTROL = re.compile("[\x00-\x08\x0b\x0e-\x1f\x7f-\x9f�￿]")


def r2_control(text: str) -> str:
    return CONTROL.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))


# --- R3 + R4 (sayfa düzeyi) -------------------------------------------------------------------
PAGE_NUMBER = re.compile(r"^\s*(Sayfa|Page|s\.)?\s*\d{1,4}(\s*/\s*\d{1,4})?\s*$")


def normalize_line(line: str) -> str:
    """Tekrar karşılaştırması için: rakamlar #, küçük harf, boşluklar tek ("Page 12" ~ "page ##")."""
    return " ".join(re.sub(r"\d", "#", line).lower().split())


# Kitapların bölüm sayfa başlıkları. Bölüm birkaç sayfa sürdüğü için repeated_line_min_pages eşiğine ulaşmaz.
SECTION_MARK = re.compile(r"^§\s?\d+(?:\.\d+)*$")                       # ODS: "§2.1" (başlığın yanında)
NUMBERED_RUNNING_HEADER = re.compile(r"^n?\d+(?:\.\d+)+\.\s+\S")       # Erickson: "8.3. The Only SSSP Algorithm"


def running_section_headers(pages: list[list[str]]) -> set[tuple[int, int]]:
    """Sayfa üstündeki bölüm başlıkları: (sayfa, satır) kümesi.

    İki kalıp, manuel kontrolde (22.10.2026) pseudocode ve paragraf ortasında bulundu:
    - Sayfanın ilk iki dolu satırından biri "§2.1" ise öbürü bölüm adıdır ("DualArrayDeque: Building a Deque ...").
    - Sayfanın ilk dolu satırı "8.3. Başlık" biçimindeyse (numaradan sonra nokta) sayfa başlığıdır; kitabın
      gerçek bölüm başlıkları numarayı ayrı satıra yazıyor ("8.3" / "The Only SSSP Algorithm"). Baştaki "n",
      kenar boşluğundaki süs glifinin kalıntısı ("n8.2. Negative Edges").
    """
    found = set()
    for p, lines in enumerate(pages):
        top = [i for i, line in enumerate(lines) if line.strip()][:2]
        if any(SECTION_MARK.match(lines[i].strip()) for i in top):
            found.update((p, i) for i in top if not is_code_like(lines[i]) and not SECTION_MARK.match(lines[i].strip()))
        if top and NUMBERED_RUNNING_HEADER.match(lines[top[0]].strip()):
            found.add((p, top[0]))
    return found


def r3_r4_pages(text: str, min_pages: int, edge: int) -> tuple[str, int, int]:
    """Sayfa numaralarını (R3) ve tekrar eden sayfa başlıklarını (R4) siler, sayfaları birleştirir.

    Kenar satırları silmeden önceki sayfa düzenine göre belirlenir: bir satırın silinmesi başka bir
    satırı kenara taşımaz. Döner: (metin, R3'ün sildiği karakter, R4'ün sildiği karakter).
    """
    if "\f" not in text:  # sayfası olmayan dokümanda sayfa numarası ya da sayfa başlığı yoktur
        return text, 0, 0
    pages = [page.split("\n") for page in text.split("\f")]
    edges = []
    for lines in pages:
        filled = [i for i, line in enumerate(lines) if line.strip()]
        edges.append(set(filled[:edge] + filled[-edge:]))
    # R3: kenardaki sayı satırlarından, (sayı - sayfa sırası) farkı dokümanda en sık olanlar sayfa numarasıdır.
    numbers = {(p, i): int(re.search(r"\d+", lines[i]).group()) - p
               for p, lines in enumerate(pages) for i in edges[p] if PAGE_NUMBER.match(lines[i])}
    offset = Counter(numbers.values()).most_common(1)[0][0] if numbers else None
    page_numbers = {key for key, diff in numbers.items() if diff == offset}

    seen_on = defaultdict(set)
    for p, lines in enumerate(pages):
        for i in edges[p]:
            key = normalize_line(lines[i])
            # Tek karakterlik satırlar (formül parçası "n", "∑") başlık olamaz.
            if len(key) >= 2 and not is_code_like(lines[i]):
                seen_on[key].add(p)
    repeated = {key for key, on in seen_on.items() if len(on) >= min_pages}
    running = running_section_headers(pages)

    removed_r3 = removed_r4 = 0
    out = []
    for p, lines in enumerate(pages):
        kept = []
        for i, line in enumerate(lines):
            if (p, i) in page_numbers:
                removed_r3 += len(line)
            elif (p, i) in running or (i in edges[p] and normalize_line(line) in repeated and not is_code_like(line)
                                       and not PAGE_NUMBER.match(line)):  # numaralamaya uymayan sayı içeriktir
                removed_r4 += len(line)
            else:
                kept.append(line)
        out.append("\n".join(kept).strip("\n"))
    # Sayfa ayırıcı yerine satır sonu: sayfa sonunda kesilen cümle bir sonraki satırda sürer.
    return "\n".join(out), removed_r3, removed_r4


# --- R5 -----------------------------------------------------------------------------------------
def r5_boilerplate(text: str, boilerplate: set[str]) -> str:
    return "\n".join(line for line in text.split("\n") if line.strip() not in boilerplate)


# --- R8 -----------------------------------------------------------------------------------------
def has_reference_sections(url: str, domains: list[str]) -> bool:
    host = urlsplit(url).netloc.lower()
    return any(host == d or host.endswith("." + d) for d in domains)


def r8_trailing_sections(text: str, headings: set[str], max_line_chars: int) -> str:
    """İlk uygun kaynakça başlığından sonrasını siler.

    Bir başlık ancak arkasında yalnızca liste öğeleri ("- ..."), başka kaynakça başlıkları ve kısa
    satırlar (alt başlık) kalıyorsa kesim noktası olur. Arkasında düzyazı paragraf varsa (içerik
    bölümü) bir sonraki aday denenir; hiçbiri uymazsa metne dokunulmaz.
    """
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.strip() not in headings:
            continue
        rest = [ln.strip() for ln in lines[i + 1:] if ln.strip()]
        prose, content = 0, False
        for j, ln in enumerate(rest):
            if ln.startswith("-") or ln in headings or len(ln) <= max_line_chars or REFERENCE_LIKE.search(ln):
                continue
            prose += 1
            prev = rest[j - 1] if j else line.strip()
            # Düzyazının önünde kaynakça başlığı ya da liste öğesi değil başka bir kısa satır varsa o satır bir
            # içerik başlığıdır ("History"): burası kaynakça değil, içerik bölümü.
            if len(prev) <= max_line_chars and not prev.startswith("-") and prev not in headings:
                content = True
        if not content and prose <= TRAILING_PROSE_LINES:
            return drop_footnote_entries("\n".join(lines[:i]).rstrip("\n"))
    return drop_footnote_entries(text)


# Kaynakça satırı izleri. Kaynakça ve not bölümlerindeki uzun satırlar çoğunlukla künyedir.
REFERENCE_LIKE = re.compile(r"ISBN|doi:|Retrieved|Archived|Erişim tarihi|\(PDF\)|\bpp?\.\s?\d|"
                            r"incorporates public domain|\((?:19|20)\d{2}\)")
# Kesim noktasından sonra kalmasına izin verilen, künyeye benzemeyen uzun satır sayısı. 22.10.2026'daki manuel
# kontrolde not bölümündeki bir iki açıklama satırı ("This article incorporates public domain material ...",
# dipnot metni) yüzünden 17 maddenin kaynakçası hiç kesilmemişti. Gerçek içerik bölümü (Segment tree:
# "Notes" sonrasında "History") çok daha fazla paragraf içerir ve korunur.
TRAILING_PROSE_LINES = 2


FOOTNOTE_ENTRY = re.compile(r"^\s*(?:-\s*)?↑")


def drop_footnote_entries(text: str) -> str:
    """Kesim noktasından önce ya da kesim yapılamayan metinde kalan dipnot girdilerini siler.

    Vikipedi dipnot girdileri metne "- ↑ Yazar (yıl). Başlık ..." biçiminde geçiyor; '↑' geri bağlantı işareti.
    Yalnızca satır başındaki '↑' silinir; satır içindeki bir ok işaretine dokunulmaz.
    """
    if "↑" not in text:
        return text
    return "\n".join(line for line in text.split("\n") if not FOOTNOTE_ENTRY.match(line))


# --- R9 -----------------------------------------------------------------------------------------
def r9_join_short_runs(text: str, max_chars: int, min_run: int) -> str:
    r"""Art arda en az min_run kısa satırı tek satırda birleştirir: "S\nO\nR\nT" -> "S O R T".

    Boş satır ve kod benzeri satır diziyi böler; kısa ama tek başına duran satırlar ("BFS", "O(n)") etkilenmez.
    """
    lines = text.split("\n")
    short = [0 < len(line.strip()) <= max_chars and not is_code_like(line) for line in lines]
    out: list[str] = []
    i = 0
    while i < len(lines):
        j = i
        while j < len(lines) and short[j]:
            j += 1
        if j - i >= min_run:
            out.append(" ".join(line.strip() for line in lines[i:j]))
            i = j
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out)


# --- R6 -----------------------------------------------------------------------------------------
WORD = re.compile(r"[^\W\d_][\w-]*")
LINE_END_HYPHEN = re.compile(r"([^\W\d_][\w-]*)-$")
LINE_START_WORD = re.compile(r"\s*([^\W\d_][\w-]*)")


def word_counts(texts: Any) -> Counter:
    """Satır içindeki kelimelerin sıklığı (küçük harfe indirgenmiş). R6'nın tire kararı için."""
    counts: Counter = Counter()
    for text in texts:
        counts.update(word.casefold() for word in WORD.findall(text))
    return counts


CODE_STRUCTURE_TOKENS = ("←", ":=", "==", "!=", "->", "::")


def is_code_structure(line: str) -> bool:
    """R6 için kod satırı: kod anahtar kelimesiyle başlıyor, girintili ya da atama/karşılaştırma işareti var.

    is_code_like burada fazla geniş: düzyazıdaki "{0,...,2^w −1}" ya da "remove()" satırı kod sayıyor ve satır
    sonu tiresi birleşmiyordu ("inte-|gers", "op-|erations"; PDF kitaplarında 100 yer, 22.10.2026).
    """
    return bool(CODE_START.match(line) or INDENTED.match(line)) or any(t in line for t in CODE_STRUCTURE_TOKENS)


def r6_hyphenation(text: str, vocabulary: Counter) -> str:
    """'algo-' + 'ritma' -> 'algoritma'. Sonraki satır küçük harfle başlamalı; kod satırlarına dokunulmaz.

    Tire korunur: kelimenin ilk parçası zaten tireliyse ('divide-and-|conquer') ya da tireli hâli
    corpus'ta tiresiz hâlinden daha sık geçiyorsa ('B-|tree'). Hiç iz yoksa tire atılır (varsayılan kural).
    """
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if i + 1 < len(lines) and not is_code_structure(line) and not is_code_structure(lines[i + 1]):
            head = LINE_END_HYPHEN.search(line.rstrip())
            tail = LINE_START_WORD.match(lines[i + 1])
            if head and tail and tail.group(1)[0].islower():
                first, second = head.group(1), tail.group(1)
                keep = "-" in first or \
                    vocabulary[f"{first}-{second}".casefold()] > vocabulary[f"{first}{second}".casefold()]
                # Birleşen satır sonraki turda yeniden denenir: zincirleme kırılmalar da birleşir.
                lines[i + 1] = line.rstrip()[:-1] + ("-" if keep else "") + lines[i + 1].lstrip()
                i += 1
                continue
        out.append(line)
        i += 1
    return "\n".join(out)


# --- R7 -----------------------------------------------------------------------------------------
INDENT = re.compile(r"[ \t]*")


def r7_whitespace(text: str) -> str:
    out = []
    for line in text.split("\n"):
        if is_code_like(line):
            out.append(line)
            continue
        indent = INDENT.match(line).group(0)
        body = re.sub(r"[ \t]+", " ", line[len(indent):]).rstrip()
        out.append(indent + body if body else "")
    return re.sub(r"\n{4,}", "\n\n\n", "\n".join(out)).strip("\n") + "\n"


# --- Hepsi bir arada -------------------------------------------------------------------------
def clean_text(text: str, source_type: str, url: str, cfg: dict[str, Any],
               vocabulary: Counter) -> tuple[str, dict[str, int], set[str]]:
    """Kuralları sırayla uygular. Döner: (temiz metin, kural -> silinen karakter (net), metni değiştiren kurallar)."""
    c = cfg["clean"]
    removed: dict[str, int] = {}
    changed: set[str] = set()

    def step(rule: str, func, *args) -> None:
        nonlocal text
        new = func(text, *args)
        removed[rule] = removed.get(rule, 0) + len(text) - len(new)
        if new != text:
            changed.add(rule)
        text = new

    if source_type == "code":
        step("R2", r2_control)
        return text, removed, changed

    step("R1", r1_unicode)
    step("R2", r2_control)
    paginated = "\f" in text  # R3, R4 ve R9 yalnızca PDF'ten gelen sayfalı dokümanlarda
    # R3/R4'ün sayısı silinen satırların karakteridir; sayfa ayırıcının satır sonuna dönmesi silme sayılmaz.
    text, removed["R3"], removed["R4"] = r3_r4_pages(text, c["repeated_line_min_pages"], c["page_edge_lines"])
    changed |= {rule for rule in ("R3", "R4") if removed[rule]}
    step("R5", r5_boilerplate, set(c["boilerplate_lines"]))
    if has_reference_sections(url, c["reference_section_domains"]):
        step("R8", r8_trailing_sections, set(c["trailing_sections"]), c["trailing_section_max_line_chars"])
    if paginated:
        step("R9", r9_join_short_runs, c["short_line_max_chars"], c["short_line_run_min"])
    step("R6", r6_hyphenation, vocabulary)
    step("R7", r7_whitespace)
    return text, removed, changed
