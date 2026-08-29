"""DPDP Act 2023 compliance criteria expressed as code-checkable rules.

Build step 2. Each rule is a pydantic model carrying, at minimum:
  - a stable rule ID,
  - the DPDP Act 2023 provision it derives from (section reference),
  - an evaluation that yields a pass/fail + score against an extraction run.

Criteria to cover (from PROJECT_CONTEXT.md): data minimisation, purpose
limitation, storage limitation, consent / legitimate-use basis, security
safeguards. See docs/compliance/dpdp-provision-map.md.
"""
