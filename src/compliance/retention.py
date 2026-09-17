"""Retention and erasure of exports: the deletion mechanism the register names.

A manifest declares ``retention_days`` and a ``deletion_mechanism``. The rules
score the declaration; this module is the mechanism (``PURGE-01``). When an
export is written, a sidecar beside it records the run, the purpose, the
retention declared and the date after which the files must go. ``purge_expired``
walks a directory, erases every export whose date has passed, and logs the
erasure -- so storage limitation is something the pipeline *does*, not
something it says.

# DPDP Act 2023 -- storage limitation: personal data is erased once the purpose
# is served. The sidecar is the schedule; the purge is the erasure; the audit
# event is the proof.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from compliance.audit import AuditEvent, AuditLog
from compliance.models import ExtractionRun

SIDECAR_SUFFIX = ".retention.json"


class RetentionSchedule(BaseModel):
    run_id: str
    purpose: str
    retention_days: int | None
    written_at: datetime
    delete_after: datetime | None                # None: no retention declared -- flagged, not scheduled
    files: list[str] = Field(default_factory=list)
    deletion_mechanism: str = ""

    @property
    def path_name(self) -> str:
        return f"{self.run_id}{SIDECAR_SUFFIX}"

    def due(self, now: datetime | None = None) -> bool:
        if self.delete_after is None:
            return False
        return (now or datetime.now(timezone.utc)) >= self.delete_after

    def one_line(self) -> str:
        if self.delete_after is None:
            return f"{self.run_id}: no retention declared -- cannot be scheduled for erasure"
        return (f"{self.run_id}: {len(self.files)} file(s), retained {self.retention_days} d, "
                f"erase on or after {self.delete_after:%Y-%m-%d}")


def schedule(run: ExtractionRun, files: list[Path], *, now: datetime | None = None) -> RetentionSchedule | None:
    """Write the sidecar for an export. Returns None when nothing was written."""

    if not files:
        return None
    now = now or datetime.now(timezone.utc)
    delete_after = now + timedelta(days=run.retention_days) if run.retention_days is not None else None
    sched = RetentionSchedule(
        run_id=run.run_id, purpose=run.purpose.value, retention_days=run.retention_days,
        written_at=now, delete_after=delete_after, files=[p.name for p in files],
        deletion_mechanism=run.deletion_mechanism or "",
    )
    (files[0].parent / sched.path_name).write_text(sched.model_dump_json(indent=2), encoding="utf-8")
    return sched


def schedules(directory: Path) -> list[RetentionSchedule]:
    out: list[RetentionSchedule] = []
    for path in sorted(directory.glob(f"*{SIDECAR_SUFFIX}")):
        out.append(RetentionSchedule.model_validate_json(path.read_text(encoding="utf-8")))
    return out


def purge_expired(
    directory: Path,
    *,
    now: datetime | None = None,
    audit: AuditLog | None = None,
    dry_run: bool = False,
) -> list[Path]:
    """Erase every export in ``directory`` whose retention has run out.

    Returns the paths erased (or, with ``dry_run``, the paths that would be).
    Each erasure is logged as a ``purge`` event naming the run and the files.
    """

    now = now or datetime.now(timezone.utc)
    erased: list[Path] = []
    for sched in schedules(directory):
        if not sched.due(now):
            continue
        targets = [directory / name for name in sched.files] + [directory / sched.path_name]
        present = [p for p in targets if p.exists()]
        if not dry_run:
            for p in present:
                p.unlink()
            if audit is not None:
                audit.record(AuditEvent(
                    event="purge", run_id=sched.run_id, purpose=sched.purpose,
                    note=f"erased {len(present)} file(s) after {sched.retention_days} d: "
                         + ", ".join(p.name for p in present),
                ))
        erased.extend(present)
    return erased


__all__ = ["RetentionSchedule", "schedule", "schedules", "purge_expired", "SIDECAR_SUFFIX"]
