"""Manifest veracity: which of a run's declarations the deployment can back.

``verify(run, register)`` walks every control the manifest *asserts* and asks
whether the capability register provides it. A boolean safeguard is
substantiated if the register has that control; a free-text declaration -- a
deletion mechanism, a notice reference, an accountable party, a lawful-basis
reference -- is substantiated if it cites a register identifier. Anything else
is an unsubstantiated claim.

``substantiate(run, register)`` returns the manifest with every unsubstantiated
claim removed, so the same seven rules can score what the deployment can
actually demonstrate. The benchmark reports both: the score as declared, and
the score as substantiated. For a technique that declares only what exists the
two are equal; for one that declares what sounds right, the second is lower --
and the difference is the measure.

# DPDP Act 2023 -- accountability principle: compliance that cannot be
# demonstrated is not compliance. This module is the demonstration step.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from compliance.capabilities import CapabilityRegister, Control
from compliance.models import (
    ExtractionRun,
    Governance,
    LawfulBasis,
    Notice,
    SecurityPosture,
)


class Claim(BaseModel):
    control: str                  # what was declared, in the manifest's terms
    declared: str                 # the value declared (True, or the text)
    substantiated: bool
    note: str = ""                # why not, when not


class VeracityReport(BaseModel):
    claims: list[Claim] = Field(default_factory=list)

    @property
    def declared(self) -> int:
        return len(self.claims)

    @property
    def substantiated(self) -> int:
        return sum(1 for c in self.claims if c.substantiated)

    @property
    def unsubstantiated(self) -> list[Claim]:
        return [c for c in self.claims if not c.substantiated]

    @property
    def veracity(self) -> float | None:
        """Substantiated ÷ declared, or None when nothing was declared."""

        return None if not self.claims else round(self.substantiated / self.declared, 3)

    def one_line(self) -> str:
        if not self.claims:
            return "nothing declared"
        bad = self.unsubstantiated
        if not bad:
            n = self.declared
            return f"all {n} declared control{'' if n == 1 else 's'} exist{'s' if n == 1 else ''} in the register"
        return (f"{self.substantiated} of {self.declared} declared controls exist; unsubstantiated: "
                + "; ".join(f"{c.control} ({c.declared})" for c in bad))


def _cites(text: str | None, control: Control | None) -> bool:
    """A free-text declaration is backed when it names the register control's id."""

    if not text or control is None:
        return False
    return control.id.lower() in text.lower()


def verify(run: ExtractionRun, register: CapabilityRegister) -> VeracityReport:
    claims: list[Claim] = []

    def flag(name: str, declared: bool, control: Control | None) -> None:
        if declared:
            claims.append(Claim(control=name, declared="True", substantiated=control is not None,
                                note="" if control else "the deployment has no such control"))

    def text(name: str, value: str | None, control: Control | None) -> None:
        if value and value.strip():
            ok = _cites(value, control)
            claims.append(Claim(control=name, declared=value.strip()[:60], substantiated=ok,
                                note="" if ok else (f"does not cite {control.id}" if control else "no such control exists")))

    s = run.security
    flag("transport encryption", s.transport_encrypted, register.transport_encrypted)
    flag("encryption at rest", s.at_rest_encrypted, register.at_rest_encrypted)
    flag("access control", s.access_controlled, register.access_controlled)
    flag("pseudonymisation on export", s.identifiers_pseudonymised, register.pseudonymisation)
    text("deletion mechanism", run.deletion_mechanism, register.deletion_mechanism)
    if run.notice is not None:
        text("privacy notice", run.notice.reference, register.notice)
        if run.notice.machine_readable:
            claims.append(Claim(control="machine-readable notice", declared="True",
                                substantiated=bool(register.notice) and register.notice_machine_readable,
                                note="" if register.notice_machine_readable else "no machine-readable notice exists"))
    g = run.governance
    flag("audit log", g.audit_log_enabled, register.audit_log)
    text("accountable party", g.accountable_party, register.accountable_party)
    flag("record of processing", g.processing_record_kept, register.processing_record)
    if run.lawful_basis is not None and run.lawful_basis.reference:
        basis = register.lawful_bases.get(run.purpose)
        text("lawful-basis reference", run.lawful_basis.reference, basis)
    return VeracityReport(claims=claims)


def substantiate(run: ExtractionRun, register: CapabilityRegister) -> ExtractionRun:
    """The manifest with every unsubstantiated claim removed.

    Scoring this with the same rules gives the *substantiated* compliance
    score: what the deployment can demonstrate, rather than what was said.
    """

    report = verify(run, register)
    bad = {c.control for c in report.unsubstantiated}
    s = run.security
    security = SecurityPosture(
        transport_encrypted=s.transport_encrypted and "transport encryption" not in bad,
        at_rest_encrypted=s.at_rest_encrypted and "encryption at rest" not in bad,
        access_controlled=s.access_controlled and "access control" not in bad,
        identifiers_pseudonymised=s.identifiers_pseudonymised and "pseudonymisation on export" not in bad,
    )
    notice = run.notice
    if notice is not None:
        if "privacy notice" in bad:
            notice = None
        elif "machine-readable notice" in bad:
            notice = Notice(reference=notice.reference, covers_purpose=notice.covers_purpose, machine_readable=False)
    basis = run.lawful_basis
    if basis is not None and "lawful-basis reference" in bad:
        basis = LawfulBasis(type=basis.type, reference=None)     # asserted, but not on record
    g = run.governance
    governance = Governance(
        audit_log_enabled=g.audit_log_enabled and "audit log" not in bad,
        accountable_party=None if "accountable party" in bad else g.accountable_party,
        processing_record_kept=g.processing_record_kept and "record of processing" not in bad,
    )
    return run.model_copy(update={
        "security": security,
        "notice": notice,
        "lawful_basis": basis,
        "governance": governance,
        "deletion_mechanism": None if "deletion mechanism" in bad else run.deletion_mechanism,
    })


__all__ = ["Claim", "VeracityReport", "verify", "substantiate"]
