"""The dataset page: built from a real run, and held to the rules it demonstrates.

The page is shown to a room. It must never carry a raw direct identifier; built
from a real export it must carry no values at all, only their shape; and a
real export's page must never land where git would commit it.
"""

from __future__ import annotations

import csv
import json
import re

import pytest

import tools.build_dataset_page as page_builder
from compliance.audit import AuditLog
from data_synthetic.export import write_export

RECORDS = 8


def _export(tmp_path, *, synthetic: bool):
    directory = write_export(tmp_path / "export", records_per_layer=RECORDS, seed=5)
    if not synthetic:
        # Treated as real: no synthetic manifest, a provenance note that does not say "Synthetic: yes".
        (directory / "manifest.json").unlink()
        (directory / "PROVENANCE.md").write_text(
            "# Provenance\n\nTest export. De-identification: none applied (identifiable).\n", encoding="utf-8")
    return directory


def _identifiers(directory):
    values = set()
    with (directory / "patient_administration.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            values |= {row["mrn"], row["full_name"], row["phone"], row["email"], row["street_address"]}
    return values


def _data(html: str) -> dict:
    return json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
                      .group(1).replace("<\\/", "</"))


def _build(tmp_path, directory, **kw):
    out = tmp_path / "page.html"
    page_builder.build(directory, out=out, enforce_handling=False, audit_log=AuditLog(tmp_path / "audit.jsonl"), **kw)
    return out.read_text(encoding="utf-8")


def test_a_synthetic_export_builds_a_page_with_every_step_and_no_raw_identifier(tmp_path):
    directory = _export(tmp_path, synthetic=True)
    html = _build(tmp_path, directory)
    data = _data(html)
    assert set(data) >= {"meta", "files", "layers", "gate", "tasks", "patients", "traces", "benchmark", "retention"}
    assert data["meta"]["values_shown"] is True
    assert data["patients"] and all(p["token"].startswith("PSN-") and "id" not in p for p in data["patients"])
    assert any(k.endswith("|ours") for k in data["traces"]) and any(k.endswith("|baseline") for k in data["traces"])
    for value in _identifiers(directory):
        assert value not in html
    # Our export for one patient leaks nothing; the baseline's leaks, and the page says so.
    ours = next(v for k, v in data["traces"].items() if k.endswith("|ours"))
    base = next(v for k, v in data["traces"].items() if k.endswith("|baseline"))
    assert ours["export"]["leaked"] == 0 and base["export"]["leaked"] > 0
    assert "•" in json.dumps(base["export"]["hl7"], ensure_ascii=False)                 # its raw identifiers, masked


def test_a_real_export_shows_structure_only(tmp_path, monkeypatch):
    monkeypatch.setattr(page_builder, "git_ignores", lambda path: True)
    directory = _export(tmp_path, synthetic=False)
    html = _build(tmp_path, directory)
    data = _data(html)
    assert data["meta"]["values_shown"] is False
    with (directory / "clinical_ehr.csv").open(encoding="utf-8") as fh:
        diagnoses = {row["primary_diagnosis"] for row in csv.DictReader(fh)}
    assert not any(d in html for d in diagnoses if len(d) >= 4)      # no clinical value on the page
    ours = next(v for k, v in data["traces"].items() if k.endswith("|ours"))
    assert "▒▒" in json.dumps(ours["export"], ensure_ascii=False)                        # values replaced by their shape
    assert all(p["label"] == "" for p in data["patients"])           # no sex, no birth year


def test_a_real_export_page_is_refused_where_git_would_commit_it(tmp_path, monkeypatch):
    monkeypatch.setattr(page_builder, "git_ignores", lambda path: False)
    directory = _export(tmp_path, synthetic=False)
    with pytest.raises(page_builder.PageLeak, match="not git-ignored"):
        _build(tmp_path, directory)
    assert not (tmp_path / "page.html").exists()


def test_the_page_audit_refuses_a_page_that_would_carry_a_raw_identifier(tmp_path, monkeypatch):
    # Break the masking: the builder's own search of its output must catch it.
    monkeypatch.setattr(page_builder, "mask", lambda value: str(value))
    directory = _export(tmp_path, synthetic=True)
    with pytest.raises(page_builder.PageLeak, match="must not be shown"):
        _build(tmp_path, directory)
    assert not (tmp_path / "page.html").exists()


def test_a_provenance_note_can_declare_an_export_synthetic_without_skipping_the_gate(tmp_path):
    from compliance.handling import check_handling, declares_synthetic
    directory = _export(tmp_path, synthetic=False)
    assert not declares_synthetic(directory)
    note = directory / "PROVENANCE.md"
    note.write_text(note.read_text(encoding="utf-8") + "\n- **Synthetic:** yes\n", encoding="utf-8")
    assert declares_synthetic(directory)
    assert not check_handling(directory).synthetic                   # still gated like real data
