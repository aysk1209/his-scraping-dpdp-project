"""Pseudonymisation of direct identifiers on export.

The compliance-aware technique *declares* ``identifiers_pseudonymised=True`` in
its manifest, and rule SS-01 gives it credit for that. This module is where the
declaration becomes behaviour: before an extracted row is shaped into an HL7
message or a FHIR resource, every field the catalogue classes as a direct
identifier is replaced by a keyed token.

Pseudonymisation, not anonymisation: the same value yields the same token within
one export (a keyed hash), so records about one patient stay linkable to each
other, while the identifier itself does not leave the system. The key is the
export's secret; without it the token cannot be reversed or matched to a fresh
hash of the real value.

# DPDP Act 2023 -- security safeguards principle: reasonable technical measures to
# protect personal data. Pseudonymising direct identifiers on export is one, and
# ``interop.normalise.audit`` checks that it actually happened rather than trusting
# the manifest.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

from compliance.models import FieldCategory
from data_synthetic.catalogue import FIELD_CATALOGUE
from interop.layers import HISLayer

TOKEN_PREFIX = "PSN-"


def direct_identifier_fields(layer: HISLayer) -> list[str]:
    """Catalogue fields on ``layer`` that are direct identifiers."""

    return [
        name for name, category in FIELD_CATALOGUE.get(layer, {}).items()
        if category == FieldCategory.DIRECT_IDENTIFIER
    ]


def token_for(value: Any, *, key: str) -> str:
    """A stable, keyed, non-reversible stand-in for one identifier value."""

    digest = hmac.new(key.encode("utf-8"), str(value).encode("utf-8"), hashlib.sha256)
    return TOKEN_PREFIX + digest.hexdigest()[:12]


def pseudonymise_row(layer: HISLayer, row: dict[str, Any], *, key: str) -> dict[str, Any]:
    """Return a copy of ``row`` with its direct identifiers replaced by tokens."""

    out = dict(row)
    for name in direct_identifier_fields(layer):
        if name in out and out[name] not in (None, ""):
            out[name] = token_for(out[name], key=key)
    return out


def is_token(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(TOKEN_PREFIX)
