"""Answering a patient who asks what the hospital has done with their data.

At the desk, the assistant logs the request and routes it to the hospital's
data-protection contact (``agent.functions``, *log a patient's request for a copy
of their data*). This is what the contact then does with it: turn the patient's
record number into the audit log's token, and read back, from evidence the
pipeline wrote rather than from anyone's recollection,

- every extraction that read the patient's records -- when, by which technique,
  for which purpose, and which fields, by data category;
- every export made from those runs -- whether pseudonymised, and when it is
  due to be erased, read from the retention sidecar beside it;
- every erasure already carried out;
- and what the log cannot answer for: runs that read records carrying no
  patient key, which may or may not have included this patient.

The summary names fields and categories and counts records. It never carries a
value from the patient's record, and it shows the record number only masked:
the reply to an access request must not itself become a disclosure to whoever
handles it.

# DPDP Act 2023 -- rights of the data principal: the right to obtain a summary
# of the personal data being processed and the processing activities undertaken
# with it. Section references are a report-time task, as elsewhere.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from compliance.audit import AuditEvent, AuditLog, subject_token
from compliance.retention import RetentionSchedule, schedules
from data_synthetic.catalogue import FIELD_CATALOGUE
from interop.layers import HISLayer


class ProcessingActivity(BaseModel):
    """One extraction that read the patient's records."""

    at: datetime
    run_id: str
    technique: str
    purpose: str
    categories: dict[str, list[str]]          # DPDP category -> fields read, across layers
    exported: bool = False
    pseudonymised: bool | None = None
    erase_after: datetime | None = None
    erased_at: datetime | None = None


class AccessSummary(BaseModel):
    subject: str                               # masked record number
    token: str
    activities: list[ProcessingActivity] = Field(default_factory=list)
    unattributed_runs: int = 0                 # runs that read keyless records
    log_path: str = ""

    def purposes(self) -> dict[str, int]:
        out: dict[str, int] = defaultdict(int)
        for a in self.activities:
            out[a.purpose] += 1
        return dict(out)

    def categories(self) -> list[str]:
        return sorted({c for a in self.activities for c in a.categories})

    def render(self) -> str:
        lines = [f"Access request -- the data held and processed about patient {self.subject}", ""]
        if not self.activities:
            lines.append("  The audit log records no extraction that read this patient's records.")
        else:
            lines.append(f"  {len(self.activities)} extraction(s) read this patient's records, for "
                         + ", ".join(f"{p} ({n})" for p, n in sorted(self.purposes().items()))
                         + "; categories read: " + ", ".join(self.categories()) + ".")
            lines.append("")
            for a in self.activities:
                n_fields = sum(len(fs) for fs in a.categories.values())
                if n_fields > 10:       # a pull this wide is better read as a count per category
                    cats = "; ".join(f"{c} ({len(fs)} fields)" for c, fs in sorted(a.categories.items()))
                else:
                    cats = "; ".join(f"{c}: {', '.join(fs)}" for c, fs in sorted(a.categories.items()))
                lines.append(f"  {a.at:%Y-%m-%d %H:%M}  {a.purpose:<22} {a.technique}")
                lines.append(f"    read      : {cats}")
                if a.exported:
                    state = "pseudonymised" if a.pseudonymised else "NOT pseudonymised"
                    if a.erased_at:
                        tail = f"erased {a.erased_at:%Y-%m-%d}"
                    elif a.erase_after:
                        tail = f"to be erased on or after {a.erase_after:%Y-%m-%d}"
                    else:
                        tail = "no erasure scheduled"
                    lines.append(f"    exported  : {state}; {tail}")
                else:
                    lines.append("    exported  : no")
        lines.append("")
        if self.unattributed_runs:
            lines.append(f"  The log cannot answer for {self.unattributed_runs} run(s) that read records "
                         f"carrying no patient key; they may or may not include this patient.")
        lines.append("  Values from the record are not reproduced here; the record number is masked.")
        lines.append(f"  Source: {self.log_path}")
        return "\n".join(lines)


def mask(value: str) -> str:
    """'MRN2867825' -> 'MRN*****25' -- enough to match a slip, not to read a number."""

    v = str(value)
    if len(v) <= 4:
        return "*" * len(v)
    keep = 3 if v[:3].isalpha() else 0
    return v[:keep] + "*" * (len(v) - keep - 2) + v[-2:]


def _category(layer_value: str, field: str) -> str:
    try:
        cat = FIELD_CATALOGUE.get(HISLayer(layer_value), {}).get(field)
    except ValueError:
        cat = None
    return cat.value if cat is not None else "uncatalogued"


def access_summary(
    record_number: str,
    *,
    log: AuditLog | None = None,
    export_dirs: list[Path] | None = None,
) -> AccessSummary:
    """Everything the audit log and the export sidecars say about one patient."""

    log = log or AuditLog()
    token = subject_token(record_number)
    entries = log.entries()

    sidecars: dict[str, RetentionSchedule] = {}
    for directory in export_dirs or []:
        if directory.is_dir():
            sidecars.update({s.run_id: s for s in schedules(directory)})

    by_run: dict[str, list[AuditEvent]] = defaultdict(list)
    for e in entries:
        by_run[e.run_id].append(e)

    # A run counts if any of its events names the patient. Its extraction event
    # says what was read; a run seen only through its export says less, and the
    # activity then lists no categories rather than guessing them.
    runs = list(dict.fromkeys(e.run_id for e in entries if token in e.subjects))
    activities: list[ProcessingActivity] = []
    for run_id in runs:
        events = by_run[run_id]
        e = next((x for x in events if x.event == "extraction"), events[0])
        categories: dict[str, list[str]] = defaultdict(list)
        for layer_value, names in e.fields.items():
            for name in names:
                cat = _category(layer_value, name)
                if name not in categories[cat]:
                    categories[cat].append(name)
        exports = [x for x in by_run[e.run_id] if x.event == "export"]
        purges = [x for x in by_run[e.run_id] if x.event == "purge"]
        sidecar = sidecars.get(e.run_id)
        activities.append(ProcessingActivity(
            at=e.at, run_id=e.run_id, technique=e.technique, purpose=e.purpose,
            categories=dict(categories), exported=bool(exports),
            pseudonymised=("pseudonymised" in exports[-1].note and "RAW" not in exports[-1].note) if exports else None,
            erase_after=sidecar.delete_after if sidecar else None,
            erased_at=purges[-1].at if purges else None,
        ))

    unattributed = len({e.run_id for e in entries if e.event == "extraction" and e.unattributed})
    return AccessSummary(subject=mask(record_number), token=token, activities=activities,
                         unattributed_runs=unattributed, log_path=str(log.path))


__all__ = ["AccessSummary", "ProcessingActivity", "access_summary", "mask"]
