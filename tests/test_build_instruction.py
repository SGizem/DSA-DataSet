"""FAZ 8b: instruction setinin derlenmesi: split mirası, sızıntı kontrolü, id'ler, SFT mesaj biçimi."""
import importlib
import json

import pytest

b = importlib.import_module("scripts.11_build_instruction_dataset")
RATIOS = {"train": 0.8, "validation": 0.1, "test": 0.1}


def rec(key, doc=None, with_context=False, passage="P", task="kavram_aciklama"):
    return {"key": key, "source_document": doc, "passage_idx": 0, "task_type": task, "subtype": "" if doc else "alan_disi",
            "with_context": with_context, "instruction": f"talimat {key}", "response": f"cevap {key}",
            "passage": passage if doc else None, "verified_by": "auto_judge", "verified": False}


def dataset():
    doc_splits = {f"DOC_{i:06d}": ["train", "validation", "test"][i % 3] for i in range(9)}
    records = [rec(f"DOC_{i:06d}:{j}:kavram_aciklama", f"DOC_{i:06d}", with_context=j == 0)
               for i in range(9) for j in range(3)]
    records += [rec(f"OOD:{i}:bilgi_yetersizligi") for i in range(20)]
    splits = b.assign_instruction_splits(records, doc_splits, RATIOS, 42)
    return b.build(records, splits, lambda text: len(text.split())), records, doc_splits


def test_split_is_inherited_from_document_and_ids_are_unique():
    data, _, doc_splits = dataset()
    by_doc = {}
    for r in data:
        if r["source_document"]:
            by_doc.setdefault(r["source_document"], set()).add(r["split"])
    assert all(s == {doc_splits[d]} for d, s in by_doc.items())
    assert len({r["id"] for r in data}) == len(data)
    assert [r["id"] for r in data] == [f"INS_{i:05d}" for i in range(1, len(data) + 1)]
    b.check_leakage(data, doc_splits)  # hata vermez


def test_orphans_follow_split_ratios_and_are_reproducible():
    data, records, doc_splits = dataset()
    ood = [r["split"] for r in data if not r["source_document"]]
    assert ood.count("train") == 16 and ood.count("validation") == 2 and ood.count("test") == 2
    again = b.assign_instruction_splits(records, doc_splits, RATIOS, 42)
    assert {r["key"]: r["split"] for r in data} == again


def test_leakage_is_detected():
    data, _, doc_splits = dataset()
    data[0]["split"] = "test" if data[0]["split"] != "test" else "train"
    with pytest.raises(SystemExit):
        b.check_leakage(data, doc_splits)


def test_messages_use_context_template():
    data, records, _ = dataset()
    rows = {m["id"]: m for split in b.SPLITS for m in b.messages(data, records, split)}
    with_ctx = next(r for r in data if r["with_context"])
    user = rows[with_ctx["id"]]["messages"][0]["content"]
    assert user == f"Ders içeriği:\nP\n\n{with_ctx['instruction']}"
    plain = next(r for r in data if not r["with_context"])
    assert rows[plain["id"]]["messages"] == [{"role": "user", "content": plain["instruction"]},
                                             {"role": "assistant", "content": plain["response"]}]


def test_manual_review_removes_rejected_and_marks_approved():
    records = [rec("A", "DOC_000001"), rec("B", "DOC_000001"), rec("C", "DOC_000001")]
    reviews = [{"key": "A", "approved": True, "reviewer": "sgo"}, {"key": "B", "approved": False, "reviewer": "sgo"}]
    kept, rejected = b.apply_manual_review(records, reviews)
    assert rejected == 1 and [r["key"] for r in kept] == ["A", "C"]
    assert kept[0]["verified"] is True and kept[0]["verified_by"] == "manual:sgo"
    assert kept[1]["verified"] is False and kept[1]["verified_by"] == "auto_judge"


def test_examples_whose_passage_was_removed_from_the_corpus_are_dropped():
    doc_texts = {"DOC_000001": "A binary heap is a heap data structure that takes the form of a binary tree. "
                               "Heaps are commonly used to implement priority queues."}
    kept_passage = "A binary heap is a heap data structure that takes the form of a binary tree.[1]"
    removed_passage = "References\n- Williams, J. W. J. (1964). Algorithm 232 - Heapsort. Communications of the ACM."
    records = [rec("DOC_000001:0:kavram_aciklama", "DOC_000001", passage=kept_passage),
               rec("DOC_000001:1:kavram_aciklama", "DOC_000001", passage=removed_passage),
               rec("OOD:0:bilgi_yetersizligi")]
    kept, dropped = b.drop_removed_passages(records, doc_texts, 5, 0.25)
    assert [r["key"] for r in kept] == ["DOC_000001:0:kavram_aciklama", "OOD:0:bilgi_yetersizligi"]
    assert [k for k, _ in dropped] == ["DOC_000001:1:kavram_aciklama"] and dropped[0][1] == 0.0
    # Kaynak işareti ([1]) bir diziyi bozar ama passage silinmiş sayılmaz.
    assert b.passage_overlap(kept_passage, b.ngrams(doc_texts["DOC_000001"], 5), 5) > 0.9


def quiz_record(key, quiz):
    return rec(key, "DOC_000001", task="coktan_secmeli_soru_uretimi") | {"response": json.dumps(quiz, ensure_ascii=False)}


def test_quiz_answer_is_moved_with_its_option_and_explanation_references():
    quiz = {"question": "Hangisi doğrudur?", "options": {"A": "yanlış 1", "B": "doğru", "C": "yanlış 2", "D": "yanlış 3"},
            "correct": "B", "explanation": "B şıkkı doğrudur. A ve C şıkları metinle çelişir, D seçeneği eksiktir. "
                                           "A* algoritması ve A[j] elemanı değişmez."}
    # A* ve A[j] içerik; açıklamada tek başına harf yok sayılmalı ama dokunulmamalı.
    key = next(f"DOC_000001:{i}:coktan_secmeli_soru_uretimi" for i in range(50)
               if b.quiz_target(f"DOC_000001:{i}:coktan_secmeli_soru_uretimi", 42) == "D")
    moved, result = b.balance_quiz(quiz_record(key, quiz), 42)
    q = json.loads(moved["response"])
    assert result == "moved" and q["correct"] == "D" and q["options"]["D"] == "doğru"
    assert q["options"]["B"] == "yanlış 3" and q["options"]["A"] == "yanlış 1" and q["options"]["C"] == "yanlış 2"
    assert q["explanation"].startswith("D şıkkı doğrudur. A ve C şıkları metinle çelişir, B seçeneği eksiktir.")
    assert "A* algoritması ve A[j] elemanı" in q["explanation"]


def test_quiz_with_letters_used_as_content_is_not_moved():
    quiz = {"question": "A matrisi için hangisi doğrudur?", "options": {k: f"şık {k}" for k in "ABCD"},
            "correct": "B", "explanation": "B şıkkı doğrudur."}
    r = quiz_record("DOC_000001:0:coktan_secmeli_soru_uretimi", quiz)
    assert b.balance_quiz(r, 42) == (r, "unsafe")
    quiz2 = quiz | {"question": "Hangisi doğrudur?", "explanation": "Doğru cevap B'dir; minimum kesim C'den geçer."}
    r2 = quiz_record("DOC_000001:1:coktan_secmeli_soru_uretimi", quiz2)
    assert b.balance_quiz(r2, 42)[1] == "unsafe"
