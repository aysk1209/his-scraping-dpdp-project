"""Handling checks for a real dataset -- as a gate.

A hospital export is almost certainly real personal data. Before anything reads
it, four things must be true, and this module checks them rather than trusting
that someone remembered:

1. it lives under ``data/`` -- the directory the repository ignores;
2. it is actually ignored by git (the rule is in force, not just intended);
3. a ``PROVENANCE.md`` sits beside it, saying who supplied it and on what basis;
4. that note states the de-identification status, on a line of its own
   (``De-identification status: ...``);
5. unless the note declares the export synthetic, the deployment's audit key
   (``DPDP_AUDIT_KEY``) is set -- the committed development key is public, so
   tokens made with it could be reversed by trying every record number.

A synthetic export (``manifest.json`` with ``"kind": "synthetic"``) needs none of
this and passes. Anything else that fails a check is refused by the scripts that
call ``require_safe_to_read`` -- being non-compliant with the Act we benchmark
against would be a serious and visible problem, so the default is to stop.

# DPDP Act 2023 -- accountability principle: the Data Fiduciary can demonstrate
# how personal data was obtained and handled. The provenance note is that record.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = _REPO_ROOT / "data"
PROVENANCE = "PROVENANCE.md"
# The note must *address* de-identification, one way or the other, on a
# labelled line: "De-identification status: none applied, identifiable" is an
# acceptable, honest statement; silence is not -- and neither is the word
# "identified" somewhere in a sentence ("supplier not identified" says nothing).
_DEID_LINE = re.compile(r"^\W*de-?identifi\w*(\s+status|\s+at\s+source)?\W*:\s*\S", re.I | re.M)


@dataclass
class HandlingReport:
    directory: Path
    synthetic: bool = False
    checks: list[tuple[str, bool, str]] = field(default_factory=list)   # (name, ok, detail)

    @property
    def ok(self) -> bool:
        return self.synthetic or all(ok for _, ok, _ in self.checks)

    def render(self) -> str:
        if self.synthetic:
            return f"  {self.directory}: synthetic export (manifest says so) -- no handling checks apply"
        lines = [f"  handling checks for {self.directory}:"]
        for name, ok, detail in self.checks:
            lines.append(f"    [{'x' if ok else ' '}] {name}: {detail}")
        lines.append("  " + ("all checks pass -- safe to read" if self.ok else "REFUSED -- fix the unchecked items first"))
        return "\n".join(lines)


def is_synthetic(directory: Path) -> bool:
    manifest = Path(directory) / "manifest.json"
    if not manifest.exists():
        return False
    try:
        return json.loads(manifest.read_text(encoding="utf-8")).get("kind") == "synthetic"
    except (OSError, ValueError):
        return False


_SYNTHETIC_LINE = re.compile(r"^\s*[-*]?\s*\**\s*synthetic\s*\**\s*:\s*\**\s*yes\b", re.I | re.M)


def declares_synthetic(directory: Path) -> bool:
    """True if the export is synthetic by its manifest, or its provenance note says
    ``Synthetic: yes`` on a line of its own.

    Not a handling check -- a note-declared synthetic export still goes through
    the gate like real data. It decides only what a demonstration page may show:
    values from a synthetic export, never values from a real one.
    """

    if is_synthetic(directory):
        return True
    note = Path(directory) / PROVENANCE
    try:
        return bool(_SYNTHETIC_LINE.search(note.read_text(encoding="utf-8", errors="replace")))
    except OSError:
        return False


def git_ignores(path: Path) -> bool:
    """True if git reports the path as ignored (or if git is unavailable, False)."""

    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", str(path)],
            cwd=_REPO_ROOT, capture_output=True, timeout=10,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def check_handling(directory: str | Path) -> HandlingReport:
    directory = Path(directory).resolve()
    report = HandlingReport(directory=directory)
    if is_synthetic(directory):
        report.synthetic = True
        return report

    under_data = DATA_DIR.resolve() in directory.parents or directory == DATA_DIR.resolve()
    report.checks.append((
        "under data/", under_data,
        "the export lives in the ignored data directory" if under_data
        else f"move it under {DATA_DIR} -- nowhere else is ignored",
    ))

    ignored = git_ignores(directory)
    report.checks.append((
        "git-ignored", ignored,
        "git check-ignore confirms it" if ignored
        else "git does not ignore this path -- do not commit; check .gitignore",
    ))

    note = directory / PROVENANCE
    has_note = note.exists()
    report.checks.append((
        "provenance note", has_note,
        f"{PROVENANCE} present" if has_note
        else f"write {PROVENANCE} beside the files: who supplied it, when, on what basis",
    ))

    deid = False
    if has_note:
        text = note.read_text(encoding="utf-8", errors="replace")
        deid = bool(_DEID_LINE.search(text))
    report.checks.append((
        "de-identification stated", deid,
        "the note states the de-identification status" if deid
        else f"{PROVENANCE} must carry a line 'De-identification status: ...' -- de-identified, "
             f"pseudonymised or identifiable, and how",
    ))

    # The audit log stores patients as keyed tokens; with the public development
    # key they could be reversed by brute force. Fail closed on real data.
    if not declares_synthetic(directory):
        from compliance.audit import AUDIT_KEY_ENV, audit_key_is_set
        keyed = audit_key_is_set()
        report.checks.append((
            "audit key set", keyed,
            f"{AUDIT_KEY_ENV} is set for this deployment" if keyed
            else f"set {AUDIT_KEY_ENV} (kept by the data-protection contact) -- the development key is public",
        ))
    return report


class UnsafeDataset(RuntimeError):
    pass


def require_safe_to_read(directory: str | Path) -> HandlingReport:
    """Raise ``UnsafeDataset`` unless the handling checks pass (or the data is synthetic)."""

    report = check_handling(directory)
    if not report.ok:
        raise UnsafeDataset(report.render())
    return report


__all__ = ["HandlingReport", "check_handling", "declares_synthetic", "git_ignores", "require_safe_to_read", "UnsafeDataset", "PROVENANCE", "DATA_DIR"]
