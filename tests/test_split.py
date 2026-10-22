"""06_split testleri: doküman düzeyinde ayrım, sızıntı yok, aynı seed aynı atama."""
import importlib
import json

s = importlib.import_module("scripts.06_split")
RATIOS = {"train": 0.80, "validation": 0.10, "test": 0.10}
GROUPS = {"wiki": [f"DOC_{i:06d}" for i in range(1, 401)],
          "kitap": [f"DOC_{i:06d}" for i in range(401, 411)],
          "kod": [f"DOC_{i:06d}" for i in range(411, 511)]}


def test_every_document_lands_in_exactly_one_file(tmp_path):
    assignment = s.assign_splits(GROUPS, RATIOS, seed=42)
    for split in s.SPLITS:
        records = [{**{k: None for k in s.RECORD_FIELDS}, "document_id": d, "split": split}
                   for d, sp in assignment.items() if sp == split]
        s.write_jsonl(records, tmp_path / f"{split}.jsonl")
    seen = [json.loads(line)["document_id"] for split in s.SPLITS
            for line in (tmp_path / f"{split}.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(seen) == len(set(seen)) == sum(len(ids) for ids in GROUPS.values())


def test_same_seed_same_assignment_other_seed_differs():
    assert s.assign_splits(GROUPS, RATIOS, seed=42) == s.assign_splits(GROUPS, RATIOS, seed=42)
    assert s.assign_splits(GROUPS, RATIOS, seed=42) != s.assign_splits(GROUPS, RATIOS, seed=7)


def test_every_source_is_represented_in_every_split():
    assignment = s.assign_splits(GROUPS, RATIOS, seed=42)
    for ids in GROUPS.values():
        assert {assignment[d] for d in ids} == set(s.SPLITS)
    # 10 bölümlük kitap: 8 / 1 / 1
    book = [assignment[d] for d in GROUPS["kitap"]]
    assert (book.count("train"), book.count("validation"), book.count("test")) == (8, 1, 1)


def test_adding_a_source_does_not_change_other_sources():
    before = s.assign_splits(GROUPS, RATIOS, seed=42)
    after = s.assign_splits({**GROUPS, "yeni": ["DOC_999999"]}, RATIOS, seed=42)
    assert all(after[d] == split for d, split in before.items())


def test_tiny_groups_keep_at_least_one_training_document():
    assert s.split_counts(1, RATIOS) == {"train": 1, "validation": 0, "test": 0}
    assert s.split_counts(5, RATIOS) == {"train": 3, "validation": 1, "test": 1}
    assert s.split_counts(2, {"train": 0.4, "validation": 0.3, "test": 0.3})["train"] >= 1


def test_adding_a_document_moves_at_most_two_others():
    before = s.assign_splits(GROUPS, RATIOS, seed=42)
    group = max(GROUPS, key=lambda g: len(GROUPS[g]))
    after = s.assign_splits({**GROUPS, group: GROUPS[group] + ["DOC_999998"]}, RATIOS, seed=42)
    moved = [d for d, split in before.items() if after[d] != split]
    assert len(moved) <= 2
