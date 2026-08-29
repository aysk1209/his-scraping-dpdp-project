# DPDP Act 2023 — provision → rule index

The build-step-2 compliance framework turns each criterion below into a
code-checkable rule in [`src/compliance/rules/`](../../src/compliance/rules/),
with a stable rule ID and an evaluation that yields a pass/fail + score against
an extraction run.

Every compliance-relevant code path must cite its provision in a comment, e.g.
`# DPDP Act 2023, Sec 8(5) — data retention limitation`.

> Section references below are **placeholders to be confirmed** against the Act
> text and the Review-1 background report before rules are implemented.

| Rule ID | Criterion | DPDP Act 2023 provision (to confirm) | Notes |
|---------|-----------|--------------------------------------|-------|
| `DM-01` | Data minimisation | Sec 5 / Sec 6 — collection limited to what is necessary for the stated purpose | Extraction must not pull fields beyond the declared purpose scope |
| `PL-01` | Purpose limitation | Sec 5(2) / Sec 6 — processing tied to the purpose consented to | Each extraction run declares a purpose; benchmark checks adherence |
| `SL-01` | Storage limitation | Sec 8(5) — erase once the purpose is served | Retention window + deletion evidence for scraped records |
| `CL-01` | Consent / legitimate use basis | Sec 6 (consent) / Sec 7 (legitimate uses) | Lawful basis recorded per run |
| `SS-01` | Security safeguards | Sec 8(4) / Sec 8(5) — reasonable security safeguards | Encryption at rest/in transit, access control, breach-resistance of the pipeline |
| `TR-01` | Transparency / notice | Sec 5(3) — notice to the Data Principal | Applicability to scraping context to be assessed |
| `AC-01` | Accountability | Sec 8(1)–(3) — Data Fiduciary obligations | Audit trail produced by the benchmarking harness |

## Output artifact

Build step 5 (`src/compliance/benchmark.py`) writes a scored result per
extraction run to `docs/benchmark_results/` (gitignored). That artifact — not
prose — is the comparison point against baseline techniques (e.g. AutoScraper,
EMNLP 2024).
