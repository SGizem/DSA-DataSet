"""Instruction üretimi için passage (parça) bölme: paragraf, başlık ve cümle sınırlarından, token aralığında.

Kural: metin yalnızca satır sonlarından kesilir, hiçbir zaman kelime ya da cümle ortasından (rastgele karakter
kesmesi yok, FAZ 8 kararı). Kesim yerinin kalitesi kaynağın yapısına göre puanlanır ve aralık içindeki en iyi
yer seçilir:

- HTML (Vikipedi, Open Guide): her satır bir paragraf; her satır sonu paragraf sınırıdır, başlıktan önce
  kesmek daha iyidir.
- PDF (kitaplar): satırlar sayfa genişliğinde kırılmış, paragraflar arasında boş satır yok. Cümle sonu
  (`.` `?` `!` `:` ile biten satır) kesilebilir; ardından başlık geliyorsa daha iyi. Cümle ortası yalnızca
  aralıkta başka yer yoksa kesilir.
- Kod: boş satır (fonksiyon/blok arası) en iyi yer; satır sonu ancak blok tek başına sınırı aşıyorsa.

Tek satır tek başına sınırı aşıyorsa (çok uzun Vikipedi paragrafı) önce cümlelerine bölünür.
"""
from __future__ import annotations

import re
from typing import Any, Callable

SENTENCE_END = re.compile(r"[.?!:;]\s*$")
SENTENCE_SPLIT = re.compile(r"(?<=[.?!])\s+(?=[A-ZÇĞİÖŞÜ0-9$(\"'“])")
SECTION_NUMBER = re.compile(r"^\s*(?:\d+(?:\.\d+)*|[A-Z](?:\.\d+)*|Chapter \d+|Bölüm \d+)\s*$")
HEADING_MAX_CHARS = 80

# Kesim yeri kalitesi: büyük olan tercih edilir. 0 = cümle ortası (yalnızca zorunlu kalırsa).
BEST, PARAGRAPH, SENTENCE, NONE = 3, 2, 1, 0


def load_tokenizer(cfg: dict[str, Any]):
    """config.tokens'taki tokenizer (sürüm sabit). 07 ve 09 aynı tokenizer'ı kullanır."""
    from transformers import AutoTokenizer
    from transformers.utils import logging as hf_logging
    hf_logging.set_verbosity_error()  # "sequence length is longer than max" uyarısı: model girişi değil, sayım
    t = cfg["tokens"]
    return AutoTokenizer.from_pretrained(t["tokenizer"], revision=t.get("tokenizer_revision"))


def token_counter(tokenizer) -> Callable[[str], int]:
    return lambda text: len(tokenizer.encode(text, add_special_tokens=False))


def looks_like_heading(line: str, previous: str) -> bool:
    """Kısa, noktalama ile bitmeyen ve önceki satırı cümle sonuyla biten satır: bölüm başlığı ya da numarası."""
    text = line.strip()
    if not text or len(text) > HEADING_MAX_CHARS or SENTENCE_END.search(text):
        return False
    if SECTION_NUMBER.match(text):
        return True
    return (not previous.strip() or bool(SENTENCE_END.search(previous))) and text[:1].isupper()


def split_long_line(line: str, count: Callable[[str], int], max_tokens: int) -> list[str]:
    """Sınırı tek başına aşan satırı cümlelerine böler (cümleler yeniden birleştirilince satır aynen çıkar)."""
    if count(line) <= max_tokens:
        return [line]
    parts = SENTENCE_SPLIT.split(line)
    return parts if len(parts) > 1 else [line]


def cut_quality(lines: list[str], i: int, source_type: str) -> int:
    """lines[i]'den SONRA kesmenin kalitesi."""
    current = lines[i]
    following = lines[i + 1] if i + 1 < len(lines) else ""
    if source_type == "code":
        if not following.strip() or not current.strip():
            return BEST
        return NONE if current.startswith((" ", "\t")) and following.startswith((" ", "\t")) else SENTENCE
    if source_type == "html":
        return BEST if looks_like_heading(following, current) else PARAGRAPH
    # pdf
    if not SENTENCE_END.search(current):
        return NONE
    return BEST if looks_like_heading(following, current) else SENTENCE


def chunk_text(text: str, source_type: str, count: Callable[[str], int], min_tokens: int,
               max_tokens: int) -> list[str]:
    """Metni [min_tokens, max_tokens] aralığında passage'lara böler.

    Doküman min_tokens'tan kısaysa tek passage olur. Sondaki kısa artık bir öncekiyle birleşir (sınırı
    aşmıyorsa), aşıyorsa min_tokens'ın yarısından uzunsa ayrı passage olur, değilse atılır.
    """
    lines: list[str] = []
    for line in text.split("\n"):
        lines.extend(split_long_line(line, count, max_tokens))
    sizes = [count(line) + 1 for line in lines]  # +1: satır sonu
    if sum(sizes) <= max_tokens:
        whole = "\n".join(lines).strip()
        return [whole] if whole else []

    passages: list[str] = []
    start = 0
    while start < len(lines):
        total, candidates, end = 0, [], start
        while end < len(lines) and total + sizes[end] <= max_tokens:
            total += sizes[end]
            if total >= min_tokens:
                candidates.append((cut_quality(lines, end, source_type), end))
            end += 1
        if end >= len(lines):  # kalan metin sığıyor: son passage
            passages.append("\n".join(lines[start:]).strip())
            break
        if candidates:
            best = max(q for q, _ in candidates)
            cut = max(i for q, i in candidates if q == best)  # en iyi kalitedeki en geç yer
        else:  # tek satır sınırı aşıyor (bölünemeyen satır): yalnızca o satır
            cut = max(start, end - 1) if end > start else start
        passages.append("\n".join(lines[start:cut + 1]).strip())
        start = cut + 1

    passages = [p for p in passages if p]
    if len(passages) > 1 and count(passages[-1]) < min_tokens:
        tail = passages.pop()
        merged = passages[-1] + "\n" + tail
        if count(merged) <= max_tokens:
            passages[-1] = merged
        elif count(tail) >= min_tokens // 2:
            passages.append(tail)
    return passages
