"""The audit log: every extraction run, written by the pipeline, not the technique.

The capability register says the deployment has an audit log of extraction runs
(``AUDIT-LOG``). This is it. It is written at the metering boundary by the
benchmark harness and by the export stage -- never by a technique -- so a
technique cannot claim to have been logged; it simply is. Each line is one
event: what run, which technique, for what purpose, which fields from which
layers, how many records, which patients, and a digest of the manifest it
declared. Values are never written: fields are named, records are counted, and
patients appear only as keyed tokens of their record number (``subject_token``)
-- enough to answer a patient who asks what was done with their data, and
nothing a reader of the log could turn back into a record number without the
audit key. Records that carried no patient key are counted as unattributed, so
the log says plainly what it cannot answer for.

# DPDP Act 2023 -- rights of the data principal (access to information about
# processing): the log names, per run, whose data was read, so a request can be
# answered from evidence rather than reconstructed.

Append-only JSON lines, one file, under ``data/`` (git-ignored) by default. A
deployment would keep it somewhere with its own access control; the point here
is that the log exists, is produced by the machinery rather than declared by
the thing being audited, and can be read back to show what ran.

# DPDP Act 2023 -- accountability principle: the Data Fiduciary demonstrates
# compliance. A run that is logged by the pipeline is demonstrable; a run that
# declares itself logged is not.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from compliance.models import ExtractionRun
from compliance.pseudonymise import token_for
from data_synthetic.catalogue import subject_key
from interop.layers import HISLayer

_REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR_ENV = "DPDP_AUDIT_DIR"
DEFAULT_AUDIT_DIR = _REPO_ROOT / "data" / "audit"
AUDIT_FILE = "extraction-audit.jsonl"
# The audit key turns a record number into the token the log stores. A
# deployment sets its own and keeps it with the data-protection contact; the
# default makes the fixture's log reproducible and protects nothing.
AUDIT_KEY_ENV = "DPDP_AUDIT_KEY"
_DEV_AUDIT_KEY = "fixture-audit-key--not-a-secret"


def audit_key() -> str:
    return os.environ.get(AUDIT_KEY_ENV) or _DEV_AUDIT_KEY


def subject_token(value: Any) -> str:
    """The token the audit log stores for one patient's record number."""

    return token_for(value, key=audit_key())


def subjects_in(rows: dict[str, list[dict[str, Any]]], scoped_to: str | None = None) -> tuple[list[str], int]:
    """Tokens of the patients whose records ``rows`` carry, and how many rows had no key.

    ``scoped_to`` is the patient every fetch of the run was filtered to, as the
    meter observed it: a keyless row of such a run is that patient's.
    """

    tokens: set[str] = {subject_token(scoped_to)} if scoped_to else set()
    unattributed = 0
    for layer_value, layer_rows in rows.items():
        key = subject_key(HISLayer(layer_value))
        for row in layer_rows:
            value = row.get(key) if key else None
            if value in (None, ""):
                unattributed += 0 if scoped_to else 1
            else:
                tokens.add(subject_token(value))
    return sorted(tokens), unattributed


def manifest_digest(run: ExtractionRun) -> str:
    """A stable digest of the manifest as declared (the timestamp excluded)."""

    payload = run.model_dump(mode="json", exclude={"created_at"})
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


class AuditEvent(BaseModel):
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event: str                                   # extraction | export | purge
    run_id: str
    technique: str = ""
    purpose: str = ""
    source: str = ""                             # how the source described itself
    fields: dict[str, list[str]] = Field(default_factory=dict)   # layer -> field names pulled
    records: int = 0
    subjects: list[str] = Field(default_factory=list)            # keyed tokens of the patients read
    unattributed: int = 0                                        # records read with no patient key
    scoped: bool = False                                         # every fetch filtered to one patient (metered)
    manifest_sha256: str = ""
    note: str = ""

    def one_line(self) -> str:
        n = sum(len(v) for v in self.fields.values())
        if n > 8:
            pulled = f"{n} fields across {len(self.fields)} layer(s)"
        else:
            pulled = "; ".join(f"{layer}: {', '.join(names)}" for layer, names in sorted(self.fields.items()))
        return (f"{self.at:%Y-%m-%d %H:%M:%S}Z  {self.event:<10} {self.run_id:<44} {self.purpose:<20} "
                f"{self.records:>5} records  {pulled or self.note}")


class AuditLog:
    """Append-only JSON-lines log of extraction events."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or self.default_path()

    @staticmethod
    def default_path() -> Path:
        directory = Path(os.environ.get(AUDIT_DIR_ENV) or DEFAULT_AUDIT_DIR)
        return directory / AUDIT_FILE

    def record(self, event: AuditEvent) -> AuditEvent:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(event.model_dump_json() + "\n")
        return event

    def extraction(
        self,
        run: ExtractionRun,
        *,
        technique: str,
        fields: dict[str, list[str]],
        records: int,
        source: str = "",
        rows: dict[str, list[dict[str, Any]]] | None = None,
        scoped_to: str | None = None,
    ) -> AuditEvent:
        subjects, unattributed = subjects_in(rows, scoped_to) if rows is not None else ([], 0)
        return self.record(AuditEvent(
            event="extraction", run_id=run.run_id, technique=technique,
            purpose=run.purpose.value, source=source, fields=fields, records=records,
            subjects=subjects, unattributed=unattributed, scoped=bool(scoped_to),
            manifest_sha256=manifest_digest(run),
        ))

    def touching(self, token: str) -> list[AuditEvent]:
        """Every event whose run read the patient behind ``token``, and the events
        that followed from those runs (their exports and purges)."""

        entries = self.entries()
        runs = {e.run_id for e in entries if token in e.subjects}
        return [e for e in entries if e.run_id in runs]

    def entries(self) -> list[AuditEvent]:
        if not self.path.exists():
            return []
        out: list[AuditEvent] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(AuditEvent.model_validate_json(line))
        return out

    def for_run(self, run_id: str) -> list[AuditEvent]:
        return [e for e in self.entries() if e.run_id == run_id]

    def logged(self, run_id: str) -> bool:
        """Was an extraction event written for this run? The evidence AUDIT-LOG rests on."""

        return any(e.event == "extraction" for e in self.for_run(run_id))

    def render_tail(self, n: int = 5) -> str:
        entries = self.entries()
        lines = [f"  {self.path}  ({len(entries)} events)"]
        lines += ["  " + e.one_line() for e in entries[-n:]]
        return "\n".join(lines)


def fields_by_layer(pulled: set[tuple[str, str]]) -> dict[str, list[str]]:
    """Group the meter's (layer, field) pairs for the log."""

    out: dict[str, list[str]] = {}
    for layer, name in sorted(pulled):
        out.setdefault(layer, []).append(name)
    return out


__all__ = ["AuditEvent", "AuditLog", "manifest_digest", "fields_by_layer", "AUDIT_DIR_ENV", "DEFAULT_AUDIT_DIR",
           "AUDIT_KEY_ENV", "audit_key", "subject_token", "subjects_in"]
