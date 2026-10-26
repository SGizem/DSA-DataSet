"""run_all: temiz bir kopyada (registry işlenmiş, ara dosyalar yok) 02-04 baştan çalışmalı."""
import importlib

import pandas as pd

run_all = importlib.import_module("scripts.run_all")


def test_missing_intermediates_finds_documents_without_files(tmp_path, monkeypatch):
    monkeypatch.setattr(run_all, "PROJECT_ROOT", tmp_path)
    (tmp_path / "data/extracted").mkdir(parents=True)
    (tmp_path / "data/cleaned").mkdir(parents=True)
    (tmp_path / "data/extracted/D1.txt").write_text("x", encoding="utf-8")
    (tmp_path / "data/cleaned/D1.txt").write_text("x", encoding="utf-8")
    (tmp_path / "data/extracted/D3.txt").write_text("x", encoding="utf-8")
    registry = pd.DataFrame([
        {"document_id": "D1", "extracted_path": "data/extracted/D1.txt", "cleaned_path": "data/cleaned/D1.txt"},
        {"document_id": "D2", "extracted_path": "data/extracted/D2.txt", "cleaned_path": "data/cleaned/D2.txt"},
        {"document_id": "D3", "extracted_path": "data/extracted/D3.txt", "cleaned_path": "data/cleaned/D3.txt"},
        {"document_id": "D4", "extracted_path": "", "cleaned_path": ""},  # henüz indirildi, işlenmedi
    ])
    assert run_all.missing_intermediates(registry) == ["D2", "D3"]


def test_manual_review_problems_detects_labels_not_applied():
    checks = ["a", "b"]
    labels = pd.DataFrame([
        {"key": "K1", "a": "1", "b": "1"},  # onaylı, sette manuel: sorun yok
        {"key": "K2", "a": "1", "b": "0"},  # reddedildi, sette yok: sorun yok
        {"key": "K3", "a": "0", "b": "1"},  # reddedildi ama sette: sorun
        {"key": "K4", "a": "1", "b": "1"},  # onaylı ama yalnızca yargıç onaylı: sorun
    ])
    data = [{"key": "K1", "verified_by": "manual:Ad"}, {"key": "K3", "verified_by": "manual:Ad"},
            {"key": "K4", "verified_by": "auto_judge"}]
    problems = run_all.manual_review_problems(labels, checks, data)
    assert [p.split(":")[0] for p in problems] == ["K3", "K4"]
