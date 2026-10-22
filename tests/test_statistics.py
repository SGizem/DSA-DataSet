"""08_statistics: erime tablosu registry'den doğru sayılır, tutarsız sayılar rapora girmeden yakalanır."""
import importlib

import pandas as pd
import pytest

st = importlib.import_module("scripts.08_statistics")


def registry() -> pd.DataFrame:
    rows = [("D1", "excluded", "extract", "too_short"), ("D2", "excluded", "filter", "out_of_domain"),
            ("D3", "excluded", "dedup", "duplicate"), ("D4", "excluded", "dedup", "near_duplicate"),
            ("D5", "final", "", ""), ("D6", "final", "", "")]
    return pd.DataFrame(rows, columns=["document_id", "status", "exclusion_stage", "exclusion_reason"])


def exclusions(reg: pd.DataFrame) -> pd.DataFrame:
    ex = reg[reg["status"] == "excluded"]
    return pd.DataFrame({"scope": "document", "id": ex["document_id"], "stage": ex["exclusion_stage"],
                         "reason": ex["exclusion_reason"]})


def records() -> dict:
    return {"train": [{"document_id": "D5", "split": "train"}], "validation": [{"document_id": "D6", "split": "validation"}],
            "test": []}


def test_melt_counts_each_stage():
    m = st.melt(registry())
    assert (m["raw"], m["after_extraction"], m["after_filter"], m["after_exact"], m["after_near"], m["final"]) == \
        (6, 5, 4, 3, 2, 2)
    assert (m["extraction_failed"], m["exact_duplicate"], m["near_duplicate"]) == (1, 1, 1)


def test_consistent_numbers_pass():
    reg = registry()
    st.check_consistency(reg, exclusions(reg), records(), st.melt(reg))


def test_missing_exclusion_record_is_caught():
    reg = registry()
    with pytest.raises(st.InconsistentNumbers):
        st.check_consistency(reg, exclusions(reg).iloc[1:], records(), st.melt(reg))


def test_document_missing_from_jsonl_is_caught():
    reg = registry()
    with pytest.raises(st.InconsistentNumbers):
        st.check_consistency(reg, exclusions(reg), {**records(), "validation": []}, st.melt(reg))


def test_turkish_number_format():
    assert st.n(1553153) == "1.553.153"
    assert st.dec(1612.0) == "1.612,0"
    assert st.pct(1, 3) == "%33,3"
