"""FAZ 7b: reports/statistics.md ve statistics.json (yalnızca sayısal tablolar) + data/samples örnekleri.

Çalıştırma (proje kökünden): python -m scripts.08_statistics [--config ...] [--limit N]

Tablolar: (a) erime, (b) eleme sebepleri, (c) kaynaklar, (d) dil (token), (e) alt konu, (f) split,
(g) token istatistikleri, (h) instruction (dosyalar varsa), (i) manuel QC (CSV doldurulmuşsa) ve rehber §12'nin
özet tablosu. Sayılar registry, exclusions.csv ve data/final dosyalarından çapraz kontrol edilir; tutarsızlık
varsa rapor yazılmaz, script hata verir. --limit yalnızca örnek dosyası sayısını sınırlar (istatistik hep tam).
"""
from __future__ import annotations

import argparse
import json
import random
from typing import Any

import pandas as pd

from scripts.utils.config import PROJECT_ROOT, add_common_args, load_config, resolve_path, set_seed
from scripts.utils.logging_utils import log_summary, setup_logger
from scripts.utils.registry import load_registry

SPLITS = ["train", "validation", "test"]
SOURCE_SHARE_WARNING = 0.50  # tek kaynak token'ların %50'sinden fazlasıysa uyarı
# Manuel kontrol sütunları 12_sample_for_manual_qc'deki listelerle aynı (rehber §12'deki sorular).
QC_CORPUS_CHECKS = ["readable", "in_domain", "extraction_ok", "header_footer_clean", "no_broken_chars", "metadata_ok"]
QC_INSTRUCTION_CHECKS = ["instruction_clear", "response_correct", "grounded_in_source", "answers_instruction",
                         "task_type_ok"]


class InconsistentNumbers(Exception):
    pass


def n(value: float | int) -> str:
    """Türkçe sayı biçimi: 1.553.153"""
    return f"{int(value):,}".replace(",", ".")


def dec(value: float) -> str:
    """Türkçe ondalık biçim: 1.612,0"""
    return f"{value:,.1f}".replace(",", "_").replace(".", ",").replace("_", ".")


def pct(part: float, whole: float) -> str:
    return "—" if not whole else "%" + f"{100 * part / whole:.1f}".replace(".", ",")


def table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    return (["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
            + ["| " + " | ".join(str(c) for c in row) + " |" for row in rows] + [""])


def read_jsonl(path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def melt(registry: pd.DataFrame) -> dict[str, int]:
    """Erime: her aşamadan sonra kalan doküman sayısı (registry'den)."""
    stage = registry["exclusion_stage"].where(registry["status"] == "excluded", "")
    reason = registry["exclusion_reason"].where(registry["status"] == "excluded", "")
    raw = len(registry)
    after_extract = raw - int(stage.isin(["download", "extract"]).sum())
    after_filter = after_extract - int(stage.isin(["clean", "filter"]).sum())
    after_exact = after_filter - int(((stage == "dedup") & (reason == "duplicate")).sum())
    after_near = after_exact - int(((stage == "dedup") & (reason == "near_duplicate")).sum())
    return {"raw": raw, "extraction_failed": raw - after_extract, "after_extraction": after_extract,
            "after_filter": after_filter, "exact_duplicate": after_filter - after_exact, "after_exact": after_exact,
            "near_duplicate": after_exact - after_near, "after_near": after_near,
            "final": int((registry["status"] == "final").sum())}


def check_consistency(registry: pd.DataFrame, exclusions: pd.DataFrame, records: dict[str, list],
                      m: dict[str, int]) -> None:
    """Erime tablosu, eleme kayıtları ve final dosyaları birbirini tutmalı (FAZ 7 kabul testi)."""
    problems = []
    excluded = registry[registry["status"] == "excluded"]
    from_registry = excluded.groupby(["exclusion_stage", "exclusion_reason"]).size().to_dict()
    docs = exclusions[exclusions["scope"] == "document"]
    from_csv = docs.groupby(["stage", "reason"]).size().to_dict()
    if from_registry != from_csv:
        problems.append(f"registry eleme sayıları {from_registry} != exclusions.csv {from_csv}")
    if docs["id"].duplicated().any():
        problems.append(f"exclusions.csv'de iki kez elenen doküman: {docs.loc[docs['id'].duplicated(), 'id'].tolist()}")
    if m["raw"] - len(excluded) != m["final"] or m["after_near"] != m["final"]:
        problems.append(f"ham {m['raw']} - elenen {len(excluded)} != final {m['final']}")
    jsonl_ids = [r["document_id"] for split in SPLITS for r in records[split]]
    final_ids = set(registry.loc[registry["status"] == "final", "document_id"])
    if len(jsonl_ids) != len(set(jsonl_ids)):
        problems.append("aynı document_id birden çok JSONL kaydında")
    if set(jsonl_ids) != final_ids:
        problems.append(f"JSONL ({len(set(jsonl_ids))}) ile registry final ({len(final_ids)}) kümeleri farklı")
    for split in SPLITS:
        wrong = [r["document_id"] for r in records[split] if r["split"] != split]
        if wrong:
            problems.append(f"{split}.jsonl içinde split alanı farklı: {wrong[:5]}")
    if problems:
        raise InconsistentNumbers("; ".join(problems))


# exclusions.csv'deki instruction aşamaları (09, 10, 13) ve erime tablosundaki adları
INSTRUCTION_STAGES = {"generate": "Üretim hatası", "auto_check": "Otomatik kontroller", "judge": "Yargıç model",
                      "build": "Derleme", "manual_qc": "Manuel kontrol"}


def instruction_section(final_dir, instruction_dir, exclusions: pd.DataFrame) -> tuple[list[str], dict[str, Any]]:
    path = final_dir / "instruction_v1.0.jsonl"
    if not path.exists():
        return ["Instruction dosyaları henüz yok (FAZ 8).", ""], {}
    df = pd.DataFrame(read_jsonl(path))
    total = len(df)
    plan = pd.DataFrame(read_jsonl(instruction_dir / "plan.jsonl"))
    generated = sum(1 for line in (instruction_dir / "generated_raw.jsonl").open(encoding="utf-8") if line.strip())
    ins = exclusions[exclusions["scope"] == "instruction"]
    if ins["id"].duplicated().any():
        raise InconsistentNumbers(f"exclusions.csv'de iki kez elenen örnek: {ins.loc[ins['id'].duplicated(), 'id'].tolist()[:5]}")
    unknown_stage = set(ins["stage"]) - set(INSTRUCTION_STAGES)
    if unknown_stage:
        raise InconsistentNumbers(f"exclusions.csv'de bilinmeyen instruction aşaması: {unknown_stage}")
    removed = ins["stage"].map(INSTRUCTION_STAGES).value_counts()
    after_generation = generated
    after_auto = after_generation - int(removed.get("Otomatik kontroller", 0))
    state_path = instruction_dir / "verify_state.json"
    pending = json.loads(state_path.read_text(encoding="utf-8"))["pending"] if state_path.exists() else 0
    after_judge = after_auto - int(removed.get("Yargıç model", 0)) - pending
    after_build = after_judge - int(removed.get("Derleme", 0))
    after_manual = after_build - int(removed.get("Manuel kontrol", 0))
    if after_manual != total:
        raise InconsistentNumbers(f"instruction erime tablosu tutmuyor: üretilen - elenen = {after_manual} != final {total}")
    unknown = set(ins["id"]) - set(plan["key"])
    if unknown:
        raise InconsistentNumbers(f"plan'da olmayan elenmiş örnek: {sorted(unknown)[:5]}")
    not_generated = len(plan) - generated - int(removed.get("Üretim hatası", 0))
    if not_generated < 0:
        raise InconsistentNumbers(f"üretilen + üretim hatası ({generated} + {removed.get('Üretim hatası', 0)}) > plan")
    lines = [f"Toplam örnek: {n(total)}", "", "Erime (planlanan görevden final örneğe):", ""]
    lines += table(["Aşama", "Kalan örnek", "Bu aşamada elenen"], [
        ["Planlanan görev", n(len(plan)), "—"],
        ["Üretilen", n(generated), f"{n(int(removed.get('Üretim hatası', 0)))} üretim hatası"
         + (f", {n(not_generated)} henüz üretilmedi" if not_generated else "")],
        ["Otomatik kontroller sonrası", n(after_auto), n(int(removed.get("Otomatik kontroller", 0)))],
        ["Yargıç model sonrası", n(after_judge), n(int(removed.get("Yargıç model", 0)))
         + (f" (+{n(pending)} yargıç kararı bekliyor, sete alınmadı)" if pending else "")],
        ["Derleme sonrası (passage'ı v1.0'da silinmiş olanlar)", n(after_build), n(int(removed.get("Derleme", 0)))],
        ["Manuel kontrol sonrası (final)", n(after_manual), n(int(removed.get("Manuel kontrol", 0)))]])
    reasons = ins.groupby(["stage", "reason"]).size().reset_index(name="count").sort_values("count", ascending=False)
    lines += ["Eleme sebepleri:", ""] + table(["Aşama", "Sebep", "Örnek"],
                                               [[r.stage, r.reason, n(r.count)] for r in reasons.itertuples()])

    planned = plan["task_type"].value_counts()
    removed_by_type = ins["id"].str.split(":").str[-1].value_counts()
    tasks = df["task_type"].value_counts()
    lines += ["Görev türü dağılımı:", ""] + table(
        ["Görev türü", "Planlanan", "Elenen", "Final", "Final payı"],
        [[t, n(int(planned.get(t, 0))), n(int(removed_by_type.get(t, 0))), n(int(tasks.get(t, 0))),
          pct(int(tasks.get(t, 0)), total)] for t in planned.index])
    subtypes = df.loc[df["task_type"] == "bilgi_yetersizligi", "subtype"].value_counts()
    lines += [f"bilgi_yetersizligi alt türleri: " + ", ".join(f"{s} {n(c)}" for s, c in subtypes.items()), ""]
    splits = df["split"].value_counts()
    lines += table(["Split", "Örnek", "Oran"], [[s, n(splits.get(s, 0)), pct(splits.get(s, 0), total)] for s in SPLITS])
    with_context = int(df["with_context"].astype(bool).sum())
    lines += [f"with_context oranı: {pct(with_context, total)} ({n(with_context)} örnek)", ""]
    tok = df["token_count"].astype(int)
    lines += ["Örnek başına token (kullanıcı mesajı + cevap, Qwen3):", ""] + table(
        ["Toplam", "Min", "Medyan", "Ortalama", "95. yüzdelik", "Maks"],
        [[n(int(tok.sum())), n(int(tok.min())), n(int(tok.median())), dec(tok.mean()), n(int(tok.quantile(0.95))),
          n(int(tok.max()))]])
    verified = df["verified_by"].fillna("").astype(str).str.split(":").str[0].value_counts()
    lines += table(["verified_by", "Örnek"], [[v or "(boş)", n(c)] for v, c in verified.items()])
    models = df.groupby(["generation_model", "prompt_version", "prompt_sha"]).size()
    lines += ["Üretim modeli ve prompt:", ""] + table(["Öğretmen model", "prompt_version", "prompt_sha", "Örnek"],
                                                       [[*k, n(c)] for k, c in models.items()])
    return lines, {"total": total, "planned": len(plan), "generated": generated, "after_auto": after_auto,
                   "pending_judge": pending,
                   "after_judge": after_judge, "after_build": after_build, "removed": {k: int(v) for k, v in removed.items()},
                   "reasons": {f"{r.stage}/{r.reason}": int(r.count) for r in reasons.itertuples()},
                   "task_types": tasks.to_dict(), "splits": splits.to_dict(), "with_context": with_context,
                   "tokens": int(tok.sum()), "verified_by": verified.to_dict()}


def qc_section(path, checks: list[str], title: str) -> tuple[list[str], dict[str, Any]]:
    """Doldurulmuş manuel QC CSV'sinden kontrol bazında başarı oranı. Dolmamışsa boş döner."""
    if not path.exists():
        return [f"{title}: CSV henüz yok (FAZ 9).", ""], {}
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    filled = df[df[checks].isin(["0", "1"]).all(axis=1)]
    if filled.empty:
        return [f"{title}: CSV doldurulmamış.", ""], {}
    rows, out = [], {"reviewed": len(filled), "checks": {}}
    for check in checks:
        ok = int((filled[check] == "1").sum())
        rows.append([check, f"{n(ok)}/{n(len(filled))}", pct(ok, len(filled))])
        out["checks"][check] = ok
    all_ok = int((filled[checks] == "1").all(axis=1).sum())
    rows.append(["hepsi başarılı", f"{n(all_ok)}/{n(len(filled))}", pct(all_ok, len(filled))])
    out["all_ok"] = all_ok
    return [f"{title}: {n(len(filled))} örnek incelendi.", ""] + table(["Kontrol", "Başarılı", "Oran"], rows), out


def write_samples(records: dict[str, list], cfg: dict[str, Any], seed: int, limit: int | None) -> list[str]:
    """Her split'ten seed'li birkaç kısa kayıt -> data/samples/<split>_sample.jsonl (depoya girecek örnek)."""
    s = cfg["samples"]
    out_dir = resolve_path(cfg, "samples_dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    count = s["per_split"] if limit is None else min(s["per_split"], limit)
    for split in SPLITS:
        pool = sorted((r for r in records[split] if r["char_count"] <= s["max_chars"]), key=lambda r: r["document_id"])
        chosen = sorted(random.Random(f"{seed}:{split}").sample(pool, min(count, len(pool))),
                        key=lambda r: r["document_id"])
        path = out_dir / f"{split}_sample.jsonl"
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in chosen), encoding="utf-8",
                        newline="\n")
        written += [r["document_id"] for r in chosen]
    return written


def write_instruction_samples(final_dir, cfg: dict[str, Any], seed: int) -> list[str]:
    """Her görev türünden seed'li birkaç kısa instruction örneği -> data/samples/instruction_sample.jsonl.
    Veri dosyaları depoya girmediği için depodaki örnek, setin biçimini ve türlerini gösterir."""
    path = final_dir / "instruction_v1.0.jsonl"
    if not path.exists():
        return []
    s = cfg["samples"]
    rows = read_jsonl(path)
    chosen = []
    for task in sorted({r["task_type"] for r in rows}):
        pool = sorted((r for r in rows if r["task_type"] == task and r["token_count"] <= s["instruction_max_tokens"]),
                      key=lambda r: r["key"])
        chosen += random.Random(f"{seed}:{task}").sample(pool, min(s["instruction_per_task"], len(pool)))
    out = resolve_path(cfg, "samples_dir") / "instruction_sample.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in chosen), encoding="utf-8", newline="\n")
    return [r["id"] for r in chosen]


def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description=__doc__.splitlines()[0]))
    args = parser.parse_args()
    cfg = load_config(args.config)
    logger = setup_logger("08_statistics", cfg)
    seed = set_seed(cfg)

    registry = load_registry(cfg)
    exclusions = pd.read_csv(resolve_path(cfg, "exclusions_csv"), dtype=str, keep_default_na=False)
    sources = pd.read_csv(resolve_path(cfg, "sources_csv"), dtype=str, keep_default_na=False)
    token_stats = json.loads(resolve_path(cfg, "token_stats").read_text(encoding="utf-8"))
    final_dir = resolve_path(cfg, "final_dir")
    records = {split: read_jsonl(final_dir / f"{split}.jsonl") for split in SPLITS}

    m = melt(registry)
    check_consistency(registry, exclusions, records, m)
    final = registry[registry["status"] == "final"].copy()
    if (final["token_count"] == "").any():
        raise InconsistentNumbers("token_count boş olan final doküman var (07_token_count'u çalıştırın)")
    for col in ("token_count", "word_count", "char_count"):
        final[col] = final[col].astype(int)
    tokens, words, chars = int(final["token_count"].sum()), int(final["word_count"].sum()), int(final["char_count"].sum())
    if tokens != token_stats["overall"]["total"]:
        raise InconsistentNumbers(f"registry token toplamı {tokens} != token_stats.json {token_stats['overall']['total']}")

    out: dict[str, Any] = {"version": cfg["project"]["version"], "melt": m}
    lines = [f"# İstatistik raporu — Domain Corpus v{cfg['project']['version']}", "",
             "`python -m scripts.08_statistics` üretir. Kaynak: `data/registry.csv`, `reports/exclusions.csv`, "
             "`data/final/*.jsonl`, `reports/token_stats.json`.", ""]

    # Rehber §12 özet tablosu (birebir satırlar)
    qc_corpus_lines, qc_corpus = qc_section(PROJECT_ROOT / cfg["manual_qc"]["corpus_csv"], QC_CORPUS_CHECKS,
                                            "Corpus manuel kontrolü")
    qc_ins_lines, qc_ins = qc_section(PROJECT_ROOT / cfg["manual_qc"]["instruction_csv"], QC_INSTRUCTION_CHECKS,
                                      "Instruction manuel kontrolü")
    ins_lines, ins = instruction_section(final_dir, resolve_path(cfg, "instruction_dir"), exclusions)
    tr_tokens = int(final.loc[final["language"] == "tr", "token_count"].sum())
    # Rehber §2: doküman, kelime, karakter, dosya boyutu ve token birlikte raporlanır. Ham boyut, registry'deki
    # farklı ham dosyaların diskteki boyutu (kitaplar tek PDF'ten bölüm bölüm alındığı için dosya bir kez sayılır).
    raw_paths = {p for p in registry["original_path"] if p}
    raw_bytes = (sum((PROJECT_ROOT / p).stat().st_size for p in raw_paths)
                 if all((PROJECT_ROOT / p).exists() for p in raw_paths) else None)
    final_bytes = sum((final_dir / f"{split}.jsonl").stat().st_size for split in SPLITS)
    out["sizes"] = {"raw_files": len(raw_paths), "raw_bytes": raw_bytes, "final_jsonl_bytes": final_bytes,
                    "chars": chars}
    summary = [["Veri kaynağı sayısı", n(len(sources))], ["Ham doküman", n(m["raw"])],
               ["Ham dosya boyutu", f"{dec(raw_bytes / 1e6)} MB ({n(len(raw_paths))} dosya)" if raw_bytes else "—"],
               ["Extraction başarılı", n(m["after_extraction"])], ["Extraction başarısız", n(m["extraction_failed"])],
               ["Filtering sonrası", n(m["after_filter"])], ["Exact duplicate", n(m["exact_duplicate"])],
               ["Near duplicate", n(m["near_duplicate"])], ["Final doküman", n(m["final"])],
               ["Final corpus dosya boyutu (3 JSONL, metadata dahil)", f"{dec(final_bytes / 1e6)} MB"],
               ["Toplam karakter", n(chars)],
               ["Toplam kelime", n(words)], ["Toplam token", n(tokens)], ["Türkçe içerik (token)", pct(tr_tokens, tokens)],
               ["Manuel kontrol örneği", n(qc_corpus["reviewed"]) if qc_corpus else "—"],
               ["Manuel kalite başarısı", pct(qc_corpus["all_ok"], qc_corpus["reviewed"]) if qc_corpus else "—"],
               ["Instruction örneği", n(ins["total"]) if ins else "—"],
               ["Instruction kontrol örneği", n(qc_ins["reviewed"]) if qc_ins else "—"]]
    lines += ["## Özet", ""] + table(["Özellik", "Değer"], summary)
    out["summary"] = {k: v for k, v in summary}

    # (a) erime
    lines += ["## (a) Erime tablosu", ""] + table(["Aşama", "Kalan doküman", "Bu aşamada elenen"], [
        ["Ham (indirilen)", n(m["raw"]), "—"],
        ["Extraction sonrası", n(m["after_extraction"]), n(m["extraction_failed"])],
        ["Temizleme ve filtreleme sonrası", n(m["after_filter"]), n(m["after_extraction"] - m["after_filter"])],
        ["Exact duplicate sonrası", n(m["after_exact"]), n(m["exact_duplicate"])],
        ["Near duplicate sonrası", n(m["after_near"]), n(m["near_duplicate"])],
        ["Final", n(m["final"]), "—"]])

    # (b) eleme sebepleri
    docs = exclusions[exclusions["scope"] == "document"]
    by_reason = docs.groupby(["stage", "reason"]).size().reset_index(name="count").sort_values("count", ascending=False)
    lines += ["## (b) Eleme sebepleri", ""] + table(["Aşama", "Sebep", "Doküman"],
                                                     [[r.stage, r.reason, n(r.count)] for r in by_reason.itertuples()])
    lines += [f"Toplam elenen: {n(len(docs))}", ""]
    out["exclusions"] = {f"{r.stage}/{r.reason}": int(r.count) for r in by_reason.itertuples()}

    # (c) kaynaklar
    by_source = final.groupby("source_name").agg(documents=("document_id", "size"), tokens=("token_count", "sum"),
                                                 words=("word_count", "sum"), chars=("char_count", "sum"))
    by_source = by_source.sort_values("tokens", ascending=False)
    lines += ["## (c) Kaynaklar", "", f"Kaynak sayısı: {n(len(sources))}", ""]
    lines += table(["Kaynak", "Doküman", "Doküman payı", "Token", "Token payı", "Kelime", "Karakter"],
                   [[s, n(r.documents), pct(r.documents, m["final"]), n(r.tokens), pct(r.tokens, tokens), n(r.words),
                     n(r.chars)] for s, r in by_source.iterrows()])
    dominant = by_source[by_source["tokens"] / tokens > SOURCE_SHARE_WARNING]
    for s, r in dominant.iterrows():
        lines += [f"**UYARI:** `{s}` kaynağının token payı {pct(r.tokens, tokens)} "
                  f"(sınır %{int(SOURCE_SHARE_WARNING * 100)}).", ""]
        logger.warning("%s kaynağının token payı %s (sınır %%50)", s, pct(r.tokens, tokens))
    out["sources"] = {s: {k: int(v) for k, v in r.items()} for s, r in by_source.iterrows()}

    # (d) dil
    by_lang = final.groupby("language").agg(documents=("document_id", "size"), tokens=("token_count", "sum"))
    lines += ["## (d) Dil dağılımı (token bazlı)", ""] + table(
        ["Dil", "Doküman", "Token", "Token payı"],
        [[lang, n(r.documents), n(r.tokens), pct(r.tokens, tokens)] for lang, r in
         by_lang.sort_values("tokens", ascending=False).iterrows()])
    out["languages"] = {k: {kk: int(vv) for kk, vv in r.items()} for k, r in by_lang.iterrows()}

    # (e) alt konu
    by_topic = final.groupby("subtopic").agg(documents=("document_id", "size"), tokens=("token_count", "sum"))
    lines += ["## (e) Alt konu dağılımı", ""] + table(
        ["Alt konu", "Doküman", "Doküman payı", "Token", "Token payı"],
        [[t, n(r.documents), pct(r.documents, m["final"]), n(r.tokens), pct(r.tokens, tokens)]
         for t, r in by_topic.sort_values("documents", ascending=False).iterrows()])
    out["subtopics"] = {k: {kk: int(vv) for kk, vv in r.items()} for k, r in by_topic.iterrows()}

    # (f) split
    by_split = final.groupby("split").agg(documents=("document_id", "size"), tokens=("token_count", "sum"),
                                          chars=("char_count", "sum")).reindex(SPLITS)
    lines += ["## (f) Split boyutları", ""] + table(
        ["Split", "Doküman", "Doküman payı", "Token", "Token payı"],
        [[s, n(r.documents), pct(r.documents, m["final"]), n(r.tokens), pct(r.tokens, tokens)]
         for s, r in by_split.iterrows()])
    cross = pd.crosstab(final["source_name"], final["split"]).reindex(columns=SPLITS, fill_value=0)
    lines += table(["Kaynak", *SPLITS], [[s, *[n(v) for v in r]] for s, r in cross.iterrows()])
    out["splits"] = {s: {k: int(v) for k, v in r.items()} for s, r in by_split.iterrows()}

    # (g) token istatistikleri
    rows = [["Tümü", *[token_stats["overall"][k] for k in ("documents", "total", "min", "median", "mean", "p95", "max")]]]
    rows += [[s, *[token_stats["by_split"][s][k] for k in ("documents", "total", "min", "median", "mean", "p95", "max")]]
             for s in SPLITS]
    fmt = [[r[0]] + [n(v) if isinstance(v, int) else dec(v) for v in r[1:]] for r in rows]
    lines += ["## (g) Token istatistikleri (doküman başına)", "",
              f"Tokenizer: `{token_stats['tokenizer']}` (revision `{token_stats['tokenizer_revision'][:7]}`), "
              f"özel token eklenmeden.", ""]
    lines += table(["Küme", "Doküman", "Toplam", "Min", "Medyan", "Ortalama", "P95", "Max"], fmt)
    lines += [f"{n(token_stats['long_doc_warning_tokens'])} token'dan uzun doküman: "
              f"{len(token_stats['long_documents'])}", ""]
    out["tokens"] = token_stats

    # (h) instruction, (i) manuel QC
    lines += ["## (h) Instruction istatistikleri", ""] + ins_lines
    lines += ["## (i) Manuel kalite kontrolü", ""] + qc_corpus_lines + qc_ins_lines
    out["instruction"], out["manual_qc"] = ins, {"corpus": qc_corpus, "instruction": qc_ins}

    resolve_path(cfg, "statistics_md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    resolve_path(cfg, "statistics_json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                                                     encoding="utf-8")
    samples = write_samples(records, cfg, seed, args.limit)
    samples += write_instruction_samples(final_dir, cfg, seed)
    logger.info("Final %d doküman, %d token, %d kelime | örnekler: %s", m["final"], tokens, words, ", ".join(samples))
    log_summary(logger, m["final"], m["final"], 0, 0)


if __name__ == "__main__":
    main()
