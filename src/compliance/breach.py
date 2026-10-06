"""A personal data breach, assessed from the evidence the pipeline left behind.

When an export leaks -- a copied folder, a misdirected attachment, a lost
drive -- the hospital has to tell the Data Protection Board and every patient
affected. It can only do that quickly and truthfully if it can say, from
records rather than memory, *whose* data was in what leaked, *which kinds* of
data, and *in what form*. This module does that from three things the pipeline
already writes:

- the **export events** in the audit log, which name the patients each export
  carried (as keyed tokens) and whether it was pseudonymised;
- the **extraction events** for the same runs, which name the fields read, and
  so the data categories the export can contain;
- the **retention sidecars**, which say when the files were due to be erased --
  a file that should already have been purged and was not is itself a finding.

It drafts the two notices a breach requires -- to the Board, and to each
affected patient -- in plain words, without reproducing a single value from a
record. Turning tokens back into patients to send the notices needs the audit
key and the patient register, which stay with the data-protection contact
(``resolve``).

The same assessment run on two exports of the same job shows minimisation
from the side of risk: a purpose-bound, pseudonymised export that leaks
exposes one patient's tokens; a scrape-everything export exposes everyone's
identifiers.

# DPDP Act 2023 -- personal data breach: the Data Fiduciary intimates the Board
# and each affected Data Principal. The form and timelines are prescribed by the
# Rules; the report cites them. Section references are a report-time task.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from compliance.audit import AuditEvent, AuditLog, subject_token
from compliance.retention import RetentionSchedule, schedules
from data_synthetic.catalogue import FIELD_CATALOGUE
from interop.layers import HISLayer

# Categories whose exposure raises the harm of a breach the most.
_SENSITIVE = ("clinical", "financial", "direct_identifier", "contact")


class ExposedExport(BaseModel):
    run_id: str
    purpose: str
    records: int
    patients: int
    pseudonymised: bool
    categories: list[str]
    overdue: bool = False                    # past its erasure date and still on disk


class BreachAssessment(BaseModel):
    discovered_at: datetime
    description: str
    exports: list[ExposedExport] = Field(default_factory=list)
    affected: list[str] = Field(default_factory=list)          # tokens, for the data-protection contact
    unattributed: int = 0                                       # records with no patient key
    unknown: list[str] = Field(default_factory=list)           # run ids the log has no export event for

    # ------------------------------------------------------------------ view

    def categories(self) -> list[str]:
        return sorted({c for e in self.exports for c in e.categories})

    def raw_identifiers(self) -> bool:
        return any(not e.pseudonymised and "direct_identifier" in e.categories for e in self.exports)

    def severity(self) -> str:
        """A plain grading the notices lead with; the report explains it."""

        sensitive = [c for c in self.categories() if c in _SENSITIVE]
        if self.raw_identifiers() and "clinical" in sensitive:
            return "high -- identifiable clinical data"
        if self.raw_identifiers():
            return "high -- identifiable personal data"
        if "clinical" in sensitive or "financial" in sensitive:
            return "moderate -- sensitive data, identifiers pseudonymised"
        return "low -- pseudonymised administrative data"

    def to_board(self) -> str:
        """The intimation to the Data Protection Board."""

        lines = [
            "Intimation of a personal data breach -- to the Data Protection Board",
            "",
            f"  Discovered      : {self.discovered_at:%Y-%m-%d %H:%M} UTC",
            f"  What happened   : {self.description}",
            f"  Exports involved: {len(self.exports)}"
            + (f" (and {len(self.unknown)} file(s) the audit log has no record of)" if self.unknown else ""),
            f"  Patients        : {len(self.affected)} identified from the audit log"
            + (f"; {self.unattributed} record(s) carried no patient key and could not be attributed"
               if self.unattributed else ""),
            f"  Data categories : {', '.join(self.categories()) or 'none'}",
            f"  Identifiers     : {'RAW identifiers were exposed' if self.raw_identifiers() else 'pseudonymised (keyed tokens; the key was not in the exported files)'}",
            f"  Severity        : {self.severity()}",
        ]
        overdue = [e for e in self.exports if e.overdue]
        if overdue:
            lines.append(f"  Retention       : {len(overdue)} export(s) were past their erasure date and should "
                         f"not have existed to be exposed")
        lines += [
            "",
            "  Measures taken  : the exposed files are identified by run; their retention schedules are",
            "                    brought forward and the erasure logged; each affected patient is notified.",
            "  Contact         : the hospital's data-protection contact.",
        ]
        return "\n".join(lines)

    def to_patient(self) -> str:
        """The notice each affected patient receives -- the same for each, naming no one."""

        shown = [c for c in self.categories() if self.raw_identifiers() or c != "direct_identifier"]
        named = [_plain(c) for c in shown]
        exposed = (", ".join(named[:-1]) + " and " + named[-1]) if len(named) > 1 else (named[0] if named else "no personal data")
        protected = ("Your name and record number were not in the files: each was replaced by a code that "
                     "cannot be traced back to you without a key the hospital holds separately."
                     if not self.raw_identifiers() else
                     "The files contained information that identifies you directly.")
        return "\n".join([
            "Notice to you about a personal data breach",
            "",
            f"  On {self.discovered_at:%d %B %Y} we found that {self.description.rstrip('.')}.",
            f"  The files held {exposed} about you.",
            f"  {protected}",
            "  We have removed the files we hold, logged it, and told the Data Protection Board.",
            "  You can ask our data-protection contact what we hold about you and what we did with it.",
        ])


def _plain(category: str) -> str:
    return {
        "direct_identifier": "details that identify you", "quasi_identifier": "details such as date of birth",
        "contact": "contact details", "clinical": "clinical information", "financial": "billing information",
        "administrative": "visit and admission details",
    }.get(category, category.replace("_", " "))


def _categories(fields: dict[str, list[str]]) -> list[str]:
    out: set[str] = set()
    for layer_value, names in fields.items():
        try:
            catalogue = FIELD_CATALOGUE.get(HISLayer(layer_value), {})
        except ValueError:
            continue
        out |= {catalogue[n].value for n in names if n in catalogue}
    return sorted(out)


def assess(
    run_ids: Iterable[str],
    *,
    description: str,
    log: AuditLog | None = None,
    export_dirs: Iterable[Path] = (),
    now: datetime | None = None,
) -> BreachAssessment:
    """What the exports of ``run_ids`` exposed, from the audit log and the sidecars."""

    log = log or AuditLog()
    now = now or datetime.now(timezone.utc)
    entries = log.entries()
    sidecars: dict[str, RetentionSchedule] = {}
    for directory in export_dirs:
        if Path(directory).is_dir():
            sidecars.update({s.run_id: s for s in schedules(Path(directory))})

    exports: list[ExposedExport] = []
    affected: set[str] = set()
    unattributed = 0
    unknown: list[str] = []
    for run_id in dict.fromkeys(run_ids):
        events = [e for e in entries if e.run_id == run_id]
        export = next((e for e in reversed(events) if e.event == "export"), None)
        if export is None:
            unknown.append(run_id)
            continue
        extraction: AuditEvent | None = next((e for e in events if e.event == "extraction"), None)
        sidecar = sidecars.get(run_id)
        exports.append(ExposedExport(
            run_id=run_id, purpose=export.purpose, records=export.records,
            patients=len(export.subjects),
            pseudonymised="RAW" not in export.note,
            categories=_categories(extraction.fields) if extraction else [],
            overdue=bool(sidecar and sidecar.delete_after and sidecar.delete_after < now),
        ))
        affected |= set(export.subjects)
        # A run the meter saw filtered to one patient has no stranger's rows in it.
        unattributed += 0 if extraction is not None and extraction.scoped else export.unattributed
    return BreachAssessment(discovered_at=now, description=description, exports=exports,
                            affected=sorted(affected), unattributed=unattributed, unknown=unknown)


def resolve(assessment: BreachAssessment, register: Iterable[str]) -> list[str]:
    """The record numbers behind the affected tokens, from the hospital's own register.

    Only the holder of the audit key can do this; the notices are sent from the
    result. Nothing else in this module ever sees a record number.
    """

    wanted = set(assessment.affected)
    return [mrn for mrn in register if subject_token(mrn) in wanted]


__all__ = ["BreachAssessment", "ExposedExport", "assess", "resolve"]
