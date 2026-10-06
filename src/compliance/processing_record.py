"""The record of processing activities, generated from the audit log -- not kept by hand.

A fiduciary that can show what processing it does, for which purpose and on
what basis, is accountable in the Act's sense; one that keeps that record in a
document someone updates when they remember is not. The capability register
lists a record of processing (``ROPA``). Until now it was *attested* -- the
deployment's word. This module makes it *demonstrated*: the record is derived,
on demand, from the audit log the harness writes at the metering boundary, so
it cannot fall behind what actually ran.

Per purpose it states the lawful basis the register holds for it, the data
categories and fields actually read, by which techniques, in how many runs,
over how many patients (counted from the log's tokens, never named), what was
exported and whether pseudonymised, and what has been erased. Nothing in it is
a value from a record.

# DPDP Act 2023 -- accountability: the Data Fiduciary is responsible for
# processing done by or on its behalf, and demonstrates it. Section references
# are a report-time task.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from pydantic import BaseModel, Field

from compliance.audit import AuditLog
from compliance.capabilities import DEFAULT_REGISTER, CapabilityRegister
from compliance.models import Purpose
from compliance.policy import policy_for
from data_synthetic.catalogue import FIELD_CATALOGUE
from interop.layers import HISLayer


class PurposeActivity(BaseModel):
    purpose: str
    lawful_basis: str
    retention_ceiling_days: int
    runs: int = 0
    records: int = 0
    patients: int = 0
    techniques: list[str] = Field(default_factory=list)
    categories: dict[str, list[str]] = Field(default_factory=dict)   # category -> fields read
    exports: int = 0
    raw_exports: int = 0
    erasures: int = 0
    first: datetime | None = None
    last: datetime | None = None


class ProcessingRecord(BaseModel):
    generated_at: datetime
    source: str
    activities: list[PurposeActivity]

    def render_markdown(self) -> str:
        lines = ["# Record of processing activities",
                 "",
                 f"*Generated {self.generated_at:%Y-%m-%d %H:%M} UTC from `{self.source}` -- derived from the audit "
                 f"log, not maintained by hand. Patients are counted from the log's keyed tokens; no record "
                 f"value appears here.*", ""]
        for a in self.activities:
            period = (f"{a.first:%Y-%m-%d} to {a.last:%Y-%m-%d}" if a.first and a.last else "no runs logged")
            lines += [
                f"## {a.purpose}",
                "",
                f"- **Lawful basis:** {a.lawful_basis}",
                f"- **Retention ceiling:** {a.retention_ceiling_days} days",
                f"- **Activity:** {a.runs} extraction run(s), {a.records} record(s), {a.patients} patient(s); {period}",
                f"- **By:** {', '.join(a.techniques) or '—'}",
                f"- **Exports:** {a.exports}" + (f" ({a.raw_exports} not pseudonymised)" if a.raw_exports else
                                                  (" (all pseudonymised)" if a.exports else "")),
                f"- **Erasures carried out:** {a.erasures}",
                "- **Data read, by category:**",
            ]
            lines += [f"  - {c}: {', '.join(fs)}" for c, fs in sorted(a.categories.items())] or ["  - none"]
            lines.append("")
        return "\n".join(lines)


def build_record(log: AuditLog | None = None, register: CapabilityRegister | None = None) -> ProcessingRecord:
    log = log or AuditLog()
    register = register or DEFAULT_REGISTER
    entries = log.entries()

    acts: dict[str, PurposeActivity] = {}
    tokens: dict[str, set[str]] = defaultdict(set)
    for purpose in Purpose:
        basis = register.lawful_bases.get(purpose)
        acts[purpose.value] = PurposeActivity(
            purpose=purpose.value,
            lawful_basis=f"{basis.id} -- {basis.description}" if basis else "none on record",
            retention_ceiling_days=policy_for(purpose).max_retention_days,
        )

    for e in entries:
        a = acts.get(e.purpose)
        if a is None:
            continue
        a.first = e.at if a.first is None or e.at < a.first else a.first
        a.last = e.at if a.last is None or e.at > a.last else a.last
        if e.event == "extraction":
            a.runs += 1
            a.records += e.records
            tokens[e.purpose] |= set(e.subjects)
            if e.technique and e.technique not in a.techniques:
                a.techniques.append(e.technique)
            for layer_value, names in e.fields.items():
                try:
                    catalogue = FIELD_CATALOGUE.get(HISLayer(layer_value), {})
                except ValueError:
                    continue
                for name in names:
                    cat = catalogue[name].value if name in catalogue else "uncatalogued"
                    bucket = a.categories.setdefault(cat, [])
                    if name not in bucket:
                        bucket.append(name)
        elif e.event == "export":
            a.exports += 1
            a.raw_exports += int("RAW" in e.note)
        elif e.event == "purge":
            a.erasures += 1
    for purpose, a in acts.items():
        a.patients = len(tokens[purpose])
    return ProcessingRecord(generated_at=datetime.now().astimezone(), source=str(log.path),
                            activities=list(acts.values()))


__all__ = ["ProcessingRecord", "PurposeActivity", "build_record"]
