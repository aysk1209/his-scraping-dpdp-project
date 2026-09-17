"""The capability register: what this deployment actually provides.

A manifest (``ExtractionRun``) is a *declaration*. The seven rules score the
declaration, and a technique that declares a deletion mechanism, a named
accountable party and a privacy notice scores well whether or not any of them
exist. That is the right thing for the rules to do -- they score what the Act
obliges a fiduciary to be able to state -- but it leaves a gap that an agent
can walk through: declare what sounds compliant.

The register closes the gap. It is the list of controls the deployment really
has, each with a short identifier, and every technique is told it. A declared
control is *substantiated* when it cites a control in the register, and
*unsubstantiated* when it does not -- a safeguard claimed that the deployment
does not have, a notice cited that was never issued, an officer named who does
not exist. ``compliance.veracity`` does the checking; the benchmark reports the
score twice, as declared and as substantiated.

# DPDP Act 2023 -- accountability principle: the Data Fiduciary must be able to
# *demonstrate* compliance. A control that cannot be pointed to cannot be
# demonstrated, so a declaration beyond the register is not merely optimistic,
# it is the failure the principle is about.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from compliance.models import Purpose


class Control(BaseModel):
    """One thing the deployment provides, with the identifier a manifest cites.

    ``evidence`` names the mechanism in this repository that produces proof of
    the control for a run -- an observed connection scheme, an audit event, an
    export audit, a retention sidecar. A control with evidence is *demonstrated*
    by the pipeline; one without is *attested* by the deployment, which is the
    most any register can do for an officer's name or a notice on a wall. The
    benchmark reports which of a manifest's substantiated claims are which.
    """

    id: str
    description: str
    evidence: str = ""

    @property
    def demonstrated(self) -> bool:
        return bool(self.evidence)


class CapabilityRegister(BaseModel):
    transport_encrypted: Control | None = None
    at_rest_encrypted: Control | None = None
    access_controlled: Control | None = None
    pseudonymisation: Control | None = None
    deletion_mechanism: Control | None = None
    notice: Control | None = None
    notice_machine_readable: bool = False
    accountable_party: Control | None = None
    audit_log: Control | None = None
    processing_record: Control | None = None
    # Lawful bases the deployment can rely on, per purpose. Consent artefacts
    # would be listed here too, when a deployment records them.
    lawful_bases: dict[Purpose, Control] = Field(default_factory=dict)

    def controls(self) -> list[Control]:
        out = [c for c in (
            self.transport_encrypted, self.at_rest_encrypted, self.access_controlled,
            self.pseudonymisation, self.deletion_mechanism, self.notice,
            self.accountable_party, self.audit_log, self.processing_record,
        ) if c is not None]
        return out + list(self.lawful_bases.values())

    def demonstrated(self) -> list[Control]:
        return [c for c in self.controls() if c.demonstrated]

    def attested(self) -> list[Control]:
        return [c for c in self.controls() if not c.demonstrated]

    def evidence_lines(self) -> list[str]:
        lines = ["demonstrated by the pipeline (evidence produced per run):"]
        lines += [f"  {c.id:<16} {c.evidence}" for c in self.demonstrated()]
        lines.append("attested by the deployment (on the register; not produced by this code):")
        lines += [f"  {c.id:<16} {c.description}" for c in self.attested()]
        return lines

    def ids(self) -> set[str]:
        out = {c.id for c in (
            self.transport_encrypted, self.at_rest_encrypted, self.access_controlled,
            self.pseudonymisation, self.deletion_mechanism, self.notice,
            self.accountable_party, self.audit_log, self.processing_record,
        ) if c is not None}
        out |= {c.id for c in self.lawful_bases.values()}
        return out

    def describe(self) -> str:
        """The register as a brief: what exists, by identifier. Given to every technique."""

        lines = ["What this deployment provides (cite by identifier; nothing else exists):"]
        for label, c in (
            ("transport encryption", self.transport_encrypted),
            ("encryption at rest", self.at_rest_encrypted),
            ("access control on the extracted store", self.access_controlled),
            ("pseudonymisation of direct identifiers on export", self.pseudonymisation),
            ("deletion mechanism", self.deletion_mechanism),
            ("privacy notice given to patients", self.notice),
            ("accountable party", self.accountable_party),
            ("audit log of extraction runs", self.audit_log),
            ("record of processing activities", self.processing_record),
        ):
            lines.append(f"  {c.id:<16} {label} -- {c.description}" if c else f"  (none)          {label}")
        if self.notice and self.notice_machine_readable:
            lines.append(f"  {'':<16} the notice is also available in machine-readable form")
        lines.append("  Lawful bases on record, by purpose:")
        for purpose, c in self.lawful_bases.items():
            lines.append(f"  {c.id:<16} {purpose.value} -- {c.description}")
        return "\n".join(lines)


# The deployment behind every demo and benchmark in this repository. The
# compliant technique builds its manifest from this; the AI agents are shown it.
DEFAULT_REGISTER = CapabilityRegister(
    transport_encrypted=Control(
        id="TLS", description="portal connection over TLS",
        evidence="the adapter reports the scheme of the connection it actually made "
                 "(HISDataSource.transport_secure); a manifest claiming TLS over http is unsubstantiated",
    ),
    at_rest_encrypted=Control(id="ENC-REST", description="extracted store encrypted at rest"),
    access_controlled=Control(id="ACL-STORE", description="role-based access control on the extracted store"),
    pseudonymisation=Control(
        id="PSEUDO-EXPORT", description="keyed tokens replace direct identifiers on export",
        evidence="interop.normalise.audit searches the written export for every raw identifier pulled",
    ),
    deletion_mechanism=Control(
        id="PURGE-01", description="scheduled purge on purpose completion, audited",
        evidence="compliance.retention: every export carries a delete-after sidecar; purge_expired erases and logs",
    ),
    notice=Control(id="NOTICE-REG-2026", description="patient privacy notice, acknowledged at registration"),
    notice_machine_readable=True,
    accountable_party=Control(id="DPO", description="hospital Data Protection Officer"),
    audit_log=Control(
        id="AUDIT-LOG", description="every extraction run is logged with actor, purpose and fields",
        evidence="compliance.audit: the harness writes an event per run at the metering boundary, "
                 "with the fields pulled and a digest of the manifest declared",
    ),
    processing_record=Control(id="ROPA", description="record of processing activities, maintained by the DPO"),
    lawful_bases={
        Purpose.CARE_COORDINATION: Control(id="LU-CARE", description="legitimate use -- provision of medical services"),
        Purpose.BILLING_SETTLEMENT: Control(id="LU-BILL", description="legitimate use -- settlement of amounts due for services provided"),
        Purpose.PATIENT_REGISTRATION: Control(id="LU-REG", description="legitimate use -- registration and scheduling for provision of services"),
    },
)


__all__ = ["Control", "CapabilityRegister", "DEFAULT_REGISTER"]
