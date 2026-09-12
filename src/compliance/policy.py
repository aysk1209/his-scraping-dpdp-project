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
    legitimate_use_note: str          # the specific legitimate use this purpose rests on


# DPDP Act 2023 -- data minimisation principle: data is limited to what is
# necessary for the specified purpose. The allowed-category set below is the
# machine-checkable form of "necessary for the purpose".
#
# The two purposes are intentionally NOT nested. Care coordination sees clinical
# data but no financial or contact data; billing settlement sees financial and
# contact data but no clinical data. So an extraction lawful for one can be
# unlawful for the other, in either direction -- which is what purpose limitation
# means, and what a single-purpose policy table could never demonstrate.
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
        legitimate_use_note="legitimate use -- provision of medical services",
    ),
    Purpose.BILLING_SETTLEMENT: PurposePolicy(
        allowed_categories={
            FieldCategory.DIRECT_IDENTIFIER,   # an invoice must name the payer
            FieldCategory.CONTACT,             # the bill has to be delivered somewhere
            FieldCategory.FINANCIAL,
            FieldCategory.ADMINISTRATIVE,      # which service, which ward, when
        },
        # Financial records are retained against audit and tax obligations, so the
        # ceiling is higher than care coordination's -- a longer retention is not
        # laxity, it is a different necessity. An extraction retained for a year is
        # therefore lawful here and unlawful under care coordination.
        max_retention_days=365,
        # Pseudonymisation would defeat the purpose: an invoice that cannot be
        # attributed to a payer cannot be settled. Note that this makes billing
        # look *weaker* on SS-01 inputs while being no less compliant -- necessity,
        # not strictness, is what the policy encodes.
        requires_pseudonymised_identifiers=False,
        legitimate_use_note="legitimate use -- settlement of amounts due for services provided",
    ),
}

# Deliberately NOT modelled: claims adjudication. Real insurance adjudication does
# need coded diagnosis data, so folding it into billing_settlement would quietly
# re-admit the clinical category and collapse the distinction above. It belongs as
# its own purpose with its own envelope, not as a loosening of this one.


def policy_for(purpose: Purpose) -> PurposePolicy:
    """Return the compliance policy for a processing purpose."""

    return PURPOSE_POLICY[purpose]
