"""Registry yardımcıları: --redo kümesi pipeline'ı o adımdan baştan çalıştırmakla aynı dokümanları seçmeli."""
import pandas as pd

from scripts.utils.registry import excluded_before, reached, stages_from

REG = pd.DataFrame([
    {"document_id": "D1", "status": "downloaded", "exclusion_stage": ""},
    {"document_id": "D2", "status": "excluded", "exclusion_stage": "extract"},
    {"document_id": "D3", "status": "cleaned", "exclusion_stage": ""},
    {"document_id": "D4", "status": "excluded", "exclusion_stage": "filter"},
    {"document_id": "D5", "status": "deduped", "exclusion_stage": ""},
    {"document_id": "D6", "status": "excluded", "exclusion_stage": "dedup"},
    {"document_id": "D7", "status": "final", "exclusion_stage": ""},
])


def ids(mask: pd.Series) -> list[str]:
    return REG.loc[mask, "document_id"].tolist()


def test_redo_set_includes_later_statuses_and_later_exclusions():
    # Temizleme yeniden: çıkarma aşamasında elenen D2 ve henüz indirilmiş D1 hariç herkes.
    assert ids(reached(REG, "clean")) == ["D3", "D4", "D5", "D6", "D7"]
    # Filtre yeniden: filtrede ve dedup'ta elenenler dahil, filtreye gelmemiş D1 ve D2 hariç.
    assert ids(reached(REG, "filter")) == ["D3", "D4", "D5", "D6", "D7"]
    # Dedup yeniden: filtrede elenen D4 hariç.
    assert ids(reached(REG, "dedup")) == ["D5", "D6", "D7"]


def test_excluded_before_and_stage_order():
    assert ids(excluded_before(REG, "clean")) == ["D2"]
    assert ids(excluded_before(REG, "dedup")) == ["D2", "D4"]
    assert stages_from("filter") == ["filter", "dedup", "split"]
