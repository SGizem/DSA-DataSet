"""FAZ 9: manuel kontrol örneklemi ve rapor yardımcıları."""
import importlib

import pandas as pd
import pytest

qc = importlib.import_module("scripts.12_sample_for_manual_qc")
rep = importlib.import_module("scripts.13_qc_report")


def test_allocation_is_proportional_with_minimum():
    alloc = qc.allocate({"a": 300, "b": 90, "c": 6, "d": 2}, 150, 5)
    assert sum(alloc.values()) == 150
    assert alloc["d"] == 2 and alloc["c"] >= 5  # küçük grup tamamen, diğerleri en az 5
    assert alloc["a"] > alloc["b"] > alloc["c"]


def test_stratified_sample_is_reproducible_and_covers_groups():
    items = [{"id": f"x{i:03d}", "g": "a" if i < 80 else "b"} for i in range(100)]
    s1 = qc.stratified_sample(items, "g", 20, 5, 42, "id")
    s2 = qc.stratified_sample(items, "g", 20, 5, 42, "id")
    assert s1 == s2 and len(s1) == 20
    assert sum(1 for x in s1 if x["g"] == "b") >= 5


def test_load_filled_rejects_bad_and_partial_rows(tmp_path):
    path = tmp_path / "qc.csv"
    checks = ["c1", "c2"]
    pd.DataFrame({"key": ["a", "b"], "c1": ["1", "0"], "c2": ["1", "1"], "notes": ["", ""]}).to_csv(path, index=False)
    assert len(rep.load_filled(path, checks, False)) == 2
    pd.DataFrame({"key": ["a", "b"], "c1": ["1", "2"], "c2": ["1", "1"]}).to_csv(path, index=False)
    with pytest.raises(SystemExit):
        rep.load_filled(path, checks, False)  # 0/1 dışında değer
    pd.DataFrame({"key": ["a", "b"], "c1": ["1", ""], "c2": ["1", "1"]}).to_csv(path, index=False)
    with pytest.raises(SystemExit):
        rep.load_filled(path, checks, True)  # yarım doldurulmuş satır
    pd.DataFrame({"key": ["a", "b"], "c1": ["1", ""], "c2": ["1", ""]}).to_csv(path, index=False)
    with pytest.raises(SystemExit):
        rep.load_filled(path, checks, False)  # doldurulmamış satır
    assert len(rep.load_filled(path, checks, True)) == 1


def test_round_rows_compare_same_documents_and_reject_different_sets():
    checks = qc.CORPUS_CHECKS
    before = pd.DataFrame([{"document_id": "DOC_000001", **{c: 1 for c in checks}},
                           {"document_id": "DOC_000002", **{c: 1 for c in checks}, "extraction_ok": 0}])
    after = before.copy()
    after.loc[1, "extraction_ok"] = 1
    rows = rep.round_rows(before, after, checks)
    assert rows[checks.index("extraction_ok")] == ["extraction_ok", "1/2 (%50,0)", "2/2 (%100,0)"]
    assert rows[-1] == ["**hepsi başarılı**", "1/2 (%50,0)", "2/2 (%100,0)"]
    other = after.assign(document_id=["DOC_000001", "DOC_000003"])
    with pytest.raises(SystemExit):
        rep.round_rows(before, other, checks)
