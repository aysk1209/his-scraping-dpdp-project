"""Declarative compliance policy: what each processing purpose permits.

This table is the auditable configuration the rules evaluate against. Tuning the
compliance envelope means editing policy here, not rule code. Keeping it separate
from the rules is itself a legibility artifact for the paper: the "what is
allowed" is inspectable in one place.
"""

from __future__ import annotations

from pydantic import BaseModel

from compliance.models import FieldCategory, Purpose


class PurposePolicy(BaseModel):
    """The compliance envelope for one processing purpose."""

    allowed_categories: set[FieldCategory]
    max_retention_days: int
    requires_pseudonymised_identifiers: bool


# DPDP Act 2023 -- data minimisation principle: data is limited to what is
# necessary for the specified purpose. The allowed-category set below is the
# machine-checkable form of "necessary for the purpose".
PURPOSE_POLICY: dict[Purpose, PurposePolicy] = {
    Purpose.CARE_COORDINATION: PurposePolicy(
        allowed_categories={
            FieldCategory.DIRECT_IDENTIFIER,   # needed to match a patient; pseudonymised on export
            FieldCategory.QUASI_IDENTIFIER,
            FieldCategory.CLINICAL,
            FieldCategory.ADMINISTRATIVE,
        },
        max_retention_days=90,
        requires_pseudonymised_identifiers=True,
    ),
}


def policy_for(purpose: Purpose) -> PurposePolicy:
    """Return the compliance policy for a processing purpose."""

    return PURPOSE_POLICY[purpose]
