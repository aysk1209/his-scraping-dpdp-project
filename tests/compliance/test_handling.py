"""Tests for the real-data handling gate (PLAN.md section 4 as code)."""

from __future__ import annotations

import pytest

from compliance.handling import (
    DATA_DIR,
    PROVENANCE,
    UnsafeDataset,
    check_handling,
    require_safe_to_read,
)
from data_synthetic.export import write_export


def test_synthetic_export_passes_without_any_checks(tmp_path):
    directory = write_export(tmp_path / "syn", records_per_layer=2, seed=1)
    report = check_handling(directory)
    assert report.synthetic and report.ok
    assert "synthetic" in report.render()


def test_real_looking_directory_outside_data_fails_every_check(tmp_path):
    (tmp_path / "x.csv").write_text("mrn\nA\n", encoding="utf-8")
    report = check_handling(tmp_path)
    assert not report.ok
    names = {name for name, ok, _ in report.checks if not ok}
    assert {"under data/", "git-ignored", "provenance note", "de-identification stated"} <= names
    with pytest.raises(UnsafeDataset):
        require_safe_to_read(tmp_path)


def test_directory_under_data_with_a_proper_note_passes():
    directory = DATA_DIR / "_handling_test"
    directory.mkdir(parents=True, exist_ok=True)
    try:
        (directory / "x.csv").write_text("mrn\nA\n", encoding="utf-8")
        (directory / PROVENANCE).write_text(
            "Supplied by the hospital on 2026-09-13 for the benchmarking project.\n"
            "De-identified at source: MRNs and names replaced before transfer.\n",
            encoding="utf-8",
        )
        report = check_handling(directory)
        assert report.ok, report.render()
        assert "safe to read" in report.render()
    finally:
        for f in directory.iterdir():
            f.unlink()
        directory.rmdir()


def test_note_without_deidentification_statement_is_not_enough():
    directory = DATA_DIR / "_handling_test2"
    directory.mkdir(parents=True, exist_ok=True)
    try:
        (directory / "x.csv").write_text("mrn\nA\n", encoding="utf-8")
        (directory / PROVENANCE).write_text("Supplied by the hospital.\n", encoding="utf-8")
        report = check_handling(directory)
        assert not report.ok
        failed = [name for name, ok, _ in report.checks if not ok]
        assert failed == ["de-identification stated"]
    finally:
        for f in directory.iterdir():
            f.unlink()
        directory.rmdir()
