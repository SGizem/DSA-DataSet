"""FAZ 8a: passage bölme, görev planı, prompt ve model çıktısının ayrıştırılması (API çağrısı yok)."""
import importlib
import json
from collections import Counter
import re

from scripts.utils.chunking import chunk_text

g = importlib.import_module("scripts.09_generate_instructions")


def words(text: str) -> int:  # testte tokenizer yerine kelime sayısı
    return len(text.split())


def same_text(a: str, b: str) -> bool:
    return re.sub(r"\s+", "", a) == re.sub(r"\s+", "", b)


def test_html_passages_stay_in_range_and_cut_only_between_paragraphs():
    paragraphs = [" ".join(f"k{i}_{j}" for j in range(40)) + "." for i in range(30)]  # 30 paragraf x 40 kelime
    text = "\n".join(paragraphs)
    passages = chunk_text(text, "html", words, 100, 200)
    assert same_text("\n".join(passages), text)  # metin kaybolmadı, sırası korundu
    assert all(100 <= words(p) <= 200 for p in passages[:-1])
    assert 50 <= words(passages[-1]) <= 200  # sondaki artık: en az min/2 ise ayrı passage kalır
    assert all(set(p.split("\n")) <= set(paragraphs) for p in passages)  # paragraf ortasından kesilmedi


def test_pdf_cut_prefers_sentence_end_never_mid_sentence():
    # Satırlar sayfa genişliğinde kırılmış; cümle sonu yalnızca bazı satırlarda.
    lines = []
    for s in range(20):
        lines += [f"cümle{s} " + "kelime " * 8, "devam " * 8, "son kısım " * 3 + "bitti."]
    text = "\n".join(lines)
    passages = chunk_text(text, "pdf", words, 60, 120)
    assert same_text("\n".join(passages), text)
    assert all(p.rstrip().endswith(".") for p in passages[:-1])


def test_code_cut_at_blank_lines_between_functions():
    funcs = ["def f%d(x):\n" % i + "\n".join(f"    y{j} = x + {j}" for j in range(12)) + "\n    return x" for i in range(8)]
    text = "\n\n".join(funcs)
    passages = chunk_text(text, "code", words, 30, 80)
    assert same_text("\n".join(passages), text)
    assert all(p.lstrip().startswith("def ") for p in passages)


def test_short_document_is_a_single_passage():
    assert chunk_text("Kısa bir madde.\nİkinci satır.", "html", words, 100, 200) == ["Kısa bir madde.\nİkinci satır."]


def test_latex_lines_are_not_code_but_pseudocode_is():
    assert not g.is_code_line(r"- $n^* = -\frac{m}{k} \ln \left[ 1 - \frac{X}{m} \right],$")
    assert g.is_code_line("for (int i=0; i<n; ++i) {")
    prose = ["Every pair (v,parent(v)) is an edge; we claim this.", "Some prose line here.", "x = f(y) holds."]
    assert g.longest_code_run(prose) < g.CODE_RUN_MIN


def fake_passages() -> list[dict]:
    out = []
    for d in range(30):
        for i in range(4):
            code = d % 3 == 0
            out.append({"document_id": f"DOC_{d:06d}", "passage_idx": i, "title": "t", "source": "s",
                        "source_type": "code" if code else "html", "language": "en", "split": "train", "tokens": 400,
                        "has_code": code, "complexity": i % 2 == 0, "procedural": code or i == 1, "text": "x"})
    return out


def cfg(total: int = 100) -> dict:
    return {"instruction": {"target_total": total, "plan_factor": 1.0, "max_per_document": 8, "with_context_ratio": 0.4,
                            "passage_tokens": {"min": 250, "max": 700}, "tasks_per_request": 3,
                            "out_of_domain_share": 0.5, "out_of_domain_batch": 5,
                            "out_of_domain_topics": ["hava", "futbol", "yemek"],
                            "taxonomy": {"kavram_aciklama": 0.4, "kod_okuma": 0.2, "karmasiklik_analizi": 0.2,
                                         "bilgi_yetersizligi": 0.2}}}


def test_plan_follows_taxonomy_eligibility_and_document_cap():
    tasks = g.plan_tasks(fake_passages(), cfg(), seed=42)
    by_key = {(p["document_id"], p["passage_idx"]): p for p in fake_passages()}
    counts = {}
    for t in tasks:
        counts[t["task_type"]] = counts.get(t["task_type"], 0) + 1
        if t["document_id"]:
            p = by_key[(t["document_id"], t["passage_idx"])]
            assert g.eligible(t["task_type"], p, 700)
    assert counts == {"kavram_aciklama": 40, "kod_okuma": 20, "karmasiklik_analizi": 20, "bilgi_yetersizligi": 20}
    per_doc = {}
    for t in tasks:
        if t["document_id"]:
            per_doc[t["document_id"]] = per_doc.get(t["document_id"], 0) + 1
    assert max(per_doc.values()) <= 8
    assert len({t["key"] for t in tasks}) == len(tasks)  # aynı (doküman, passage, tür) iki kez yok
    ood = [t for t in tasks if t["subtype"] == g.SUBTYPE_OOD]
    assert len(ood) == 10 and all(t["document_id"] is None and not t["with_context"] for t in ood)
    assert all(t["with_context"] for t in tasks if t["subtype"] == g.SUBTYPE_MISSING)
    assert sum(t["with_context"] for t in tasks) == 40  # 0.4 x 100


def test_plan_is_reproducible_and_groups_respect_request_size():
    a, b = g.plan_tasks(fake_passages(), cfg(), 42), g.plan_tasks(fake_passages(), cfg(), 42)
    assert a == b
    groups = g.execution_order(a, 42)
    assert all(len(grp) <= 5 for grp in groups)
    passage_groups = [grp for grp in groups if grp[0]["document_id"]]  # alan dışı grupların passage'ı yok
    assert all(len({(t["document_id"], t["passage_idx"]) for t in grp}) == 1 for grp in passage_groups)
    assert all(len(grp) <= 3 for grp in passage_groups)
    # İlk 5 grup (4 tür + alan dışı alt türü ayrı sayılır) bütün türleri ve iki bilgi_yetersizligi alt türünü içerir.
    first = [t for grp in groups[:5] for t in grp]
    assert {t["task_type"] for t in first} == {"kavram_aciklama", "kod_okuma", "karmasiklik_analizi",
                                               "bilgi_yetersizligi"}
    assert {g.SUBTYPE_OOD, g.SUBTYPE_MISSING} <= {t["subtype"] for t in first}


def test_parse_items_handles_quiz_missing_and_invalid_json():
    group = [{"key": "D:0:kavram_aciklama", "task_type": "kavram_aciklama"},
             {"key": "D:0:coktan_secmeli_soru_uretimi", "task_type": "coktan_secmeli_soru_uretimi"},
             {"key": "D:0:kod_okuma", "task_type": "kod_okuma"}]
    quiz = {"question": "Q?", "options": {"A": "1", "B": "2", "C": "3", "D": "4"}, "correct": "B", "explanation": "e"}
    text = json.dumps({"items": [{"task_id": "g1", "instruction": "Nedir?", "response": "Şudur."},
                                 {"task_id": "g2", "instruction": "Soru hazırla", "quiz": quiz}]})
    ok, errors = g.parse_items(text, group)
    assert ok["D:0:kavram_aciklama"] == ("Nedir?", "Şudur.")
    assert json.loads(ok["D:0:coktan_secmeli_soru_uretimi"][1])["correct"] == "B"
    assert errors == {"D:0:kod_okuma": "görev çıktıda yok"}
    ok, errors = g.parse_items("bu json değil", group)
    assert not ok and set(errors) == {t["key"] for t in group}
    # "\text" JSON'da TAB + "ext" olarak okunur: kontrol karakteri içeren çıktı reddedilir.
    broken = '{"items": [{"task_id": "g1", "instruction": "Nedir?", "response": "$0 \\text{ ile } n$"}]}'
    ok, errors = g.parse_items(broken, group[:1])
    assert not ok and "kontrol karakteri" in errors["D:0:kavram_aciklama"]


def test_prompt_marks_context_mode_and_includes_rules():
    group = [{"key": "k1", "task_type": "kavram_aciklama", "with_context": True, "subtype": ""},
             {"key": "k2", "task_type": "bilgi_yetersizligi", "with_context": True, "subtype": g.SUBTYPE_MISSING}]
    passage = {"title": "Heap", "text": "A heap is a tree."}
    prompt = g.build_prompt(group, passage, {"kavram_aciklama": "KURAL-A", "bilgi_yetersizligi": "KURAL-B"})
    assert "A heap is a tree." in prompt and "KURAL-A" in prompt and "KURAL-B" in prompt
    assert "task_id=g1: kavram_aciklama (BAĞLAMLI)" in prompt and "METİNDE YOK" in prompt


def test_daily_quota_error_is_not_retried():
    daily = Exception("429 RESOURCE_EXHAUSTED quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier")
    minute = Exception("429 RESOURCE_EXHAUSTED quotaId: GenerateRequestsPerMinutePerProjectPerModel-FreeTier")
    assert g.is_daily_quota(daily) and not g.is_transient(daily)
    assert not g.is_daily_quota(minute) and g.is_transient(minute)
    assert g.is_transient(g.EmptyResponse("boş yanıt"))


def test_top_up_leaves_base_plan_unchanged_and_prefers_code():
    passages = fake_passages()
    c = cfg()
    base = g.plan_tasks(passages, c, 42)
    c["instruction"]["top_up"] = {"kod_okuma": 10}
    assert g.plan_tasks(passages, c, 42) == base  # ek plan ana planı değiştirmez
    extra = g.plan_top_up(passages, base, c, 42)
    assert len(extra) == 10 and all(t["task_type"] == "kod_okuma" for t in extra)
    assert not {t["key"] for t in extra} & {t["key"] for t in base}
    by_key = {(p["document_id"], p["passage_idx"]): p for p in passages}
    assert all(g.eligible("kod_okuma", by_key[(t["document_id"], t["passage_idx"])], 700) for t in extra)
    assert all(by_key[(t["document_id"], t["passage_idx"])]["source_type"] == "code" for t in extra)
    per_doc = Counter(t["document_id"] for t in base + extra if t["document_id"])
    assert max(per_doc.values()) <= c["instruction"]["max_per_document"]
    assert sum(t["with_context"] for t in extra) == 4
    assert g.plan_top_up(passages, base, c, 42) == extra  # tekrar üretilebilir


def test_network_and_api_errors_do_not_count_as_attempts():
    from scripts.utils.llm import API_ERROR, counts_as_attempt, is_network_error

    class ConnectTimeout(Exception):
        pass

    assert is_network_error(ConnectTimeout("x")) and g.is_transient(ConnectTimeout("x"))
    assert not counts_as_attempt({"error": "ConnectError: [Errno 11001] getaddrinfo failed"})  # eski kayıt
    assert not counts_as_attempt({"error": "ServerError: 503 UNAVAILABLE", "kind": API_ERROR})
    assert counts_as_attempt({"error": "görev çıktıda yok"})
    assert counts_as_attempt({"error": "json_parse: Unterminated string starting at: line 1"})
    assert counts_as_attempt({"error": "yargıç bu örnek için geçerli karar vermedi"})
