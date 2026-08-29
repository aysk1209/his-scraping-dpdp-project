"""DPDP Act 2023 compliance criteria as executable rules (build step 2).

Slice 1 implements four rules, each exercising a distinct check mechanism:

  DM-01  Data minimisation      -- set containment of extracted categories
  LB-01  Lawful basis           -- declaration + reference validation
  SL-01  Storage limitation     -- numeric retention bound + deletion mechanism
  SS-01  Security safeguards    -- fraction of required safeguards satisfied

Remaining criteria from docs/compliance/dpdp-provision-map.md (PL-01, NT-01,
AC-01) are not yet implemented. Section references throughout carry a
``TODO: verify against Act text`` marker.
"""

from __future__ import annotations

from compliance.rules.base import Rule, RuleResult, RuleStatus
from compliance.rules.lawful_basis import LawfulBasisRule
from compliance.rules.minimisation import DataMinimisationRule
from compliance.rules.security import SecuritySafeguardsRule
from compliance.rules.storage import StorageLimitationRule

ALL_RULES: list[Rule] = [
    DataMinimisationRule(),
    LawfulBasisRule(),
    StorageLimitationRule(),
    SecuritySafeguardsRule(),
]

__all__ = [
    "Rule",
    "RuleResult",
    "RuleStatus",
    "ALL_RULES",
    "DataMinimisationRule",
    "LawfulBasisRule",
    "StorageLimitationRule",
    "SecuritySafeguardsRule",
]
