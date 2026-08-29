"""Data models for a DPDP-evaluable extraction run.

A compliance rule cannot score "a scrape" in the abstract; it inspects a
structured declaration of what was extracted, why, and under what safeguards.
These models are that structured form. Any extraction technique -- ours or a
baseline -- is wrapped in an ``ExtractionRun`` plus a sample of ``ExtractedRecord``
objects so the same rules score every technique on equal terms.

Section references in the compliance code carry a ``TODO: verify against Act
text`` marker until confirmed against the DPDP Act 2023 and the project's
background review report.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class FieldCategory(str, Enum):
    """Coarse category of an extracted data element, used for purpose-scope checks."""

    DIRECT_IDENTIFIER = "direct_identifier"    # name, medical record number, national id, phone
    QUASI_IDENTIFIER = "quasi_identifier"      # date of birth, sex, pincode
    CLINICAL = "clinical"                      # diagnosis, medication, lab result
    FINANCIAL = "financial"                    # billing, insurance, claims
    ADMINISTRATIVE = "administrative"          # ward, appointment time, staff assignment
    CONTACT = "contact"                        # postal address, email


class Purpose(str, Enum):
    """Processing purposes recognised by the compliance policy.

    Modelled with a single member for this slice. Kept as an enum so the rules
    and the policy table already have the shape for a multi-purpose taxonomy
    without pretending one has been designed.
    """

    CARE_COORDINATION = "care_coordination"


class LawfulBasisType(str, Enum):
    # DPDP Act 2023, s.4 -- personal data may be processed only for a lawful
    # purpose for which consent has been given (s.6) or for a legitimate use
    # (s.7). TODO: verify section numbers against Act text.
    CONSENT = "consent"
    LEGITIMATE_USE = "legitimate_use"


class LawfulBasis(BaseModel):
    """The lawful basis relied on for an extraction run."""

    type: LawfulBasisType
    # For CONSENT: reference to the recorded consent artefact.
    # For LEGITIMATE_USE: the specific s.7 legitimate use being relied on.
    reference: str | None = None


class SecurityPosture(BaseModel):
    """Security safeguards asserted for the extraction pipeline.

    DPDP Act 2023, s.8(5) -- a Data Fiduciary shall protect personal data in its
    possession by taking reasonable security safeguards to prevent a personal
    data breach. TODO: verify section number.
    """

    transport_encrypted: bool = False          # TLS on the portal connection
    at_rest_encrypted: bool = False            # extracted data store encrypted at rest
    access_controlled: bool = False            # authn/authz enforced on the extracted store
    identifiers_pseudonymised: bool = False    # direct identifiers tokenised on export


class ExtractionRun(BaseModel):
    """Declared manifest for a single extraction run."""

    run_id: str
    purpose: Purpose
    lawful_basis: LawfulBasis | None = None
    retention_days: int | None = None
    deletion_mechanism: str | None = None
    security: SecurityPosture = Field(default_factory=SecurityPosture)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExtractedRecord(BaseModel):
    """One record produced by a run, with each value's category tagged.

    Only the categories are needed for the current rule set -- not the values --
    which keeps sample data for the benchmark free of any real personal data.
    """

    source_layer: str                          # an ``interop.layers.HISLayer`` value
    field_categories: set[FieldCategory]
    record_id: str | None = None
