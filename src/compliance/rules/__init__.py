"""DPDP Act 2023 compliance criteria as executable rules (build step 2).

Seven rules, each exercising a distinct check mechanism:

  DM-01  Data minimisation       -- set containment of extracted categories
  LB-01  Lawful basis            -- declaration + reference validation
  SL-01  Storage limitation      -- numeric retention bound + deletion mechanism
  SS-01  Security safeguards     -- fraction of required technical safeguards
  PL-01  Purpose limitation      -- purpose specified, recognised, not repurposed
  NT-01  Transparency / notice   -- notice recorded and covers the purpose
  AC-01  Accountability          -- fraction of governance controls in place

Rules cite DPDP Act 2023 principles by name; exact section citations are left
for the report's references.
"""

from __future__ import annotations

from compliance.rules.accountability import AccountabilityRule
from compliance.rules.base import Rule, RuleResult, RuleStatus
from compliance.rules.lawful_basis import LawfulBasisRule
from compliance.rules.minimisation import DataMinimisationRule
from compliance.rules.notice import NoticeRule
from compliance.rules.purpose_limitation import PurposeLimitationRule
from compliance.rules.security import SecuritySafeguardsRule
from compliance.rules.storage import StorageLimitationRule

ALL_RULES: list[Rule] = [
    DataMinimisationRule(),
    LawfulBasisRule(),
    StorageLimitationRule(),
    SecuritySafeguardsRule(),
    PurposeLimitationRule(),
    NoticeRule(),
    AccountabilityRule(),
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
    "PurposeLimitationRule",
    "NoticeRule",
    "AccountabilityRule",
]
