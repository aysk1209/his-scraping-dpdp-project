# AI-Driven HIS Management Agent with DPDP-Compliant Web Scraping

A research codebase from VIT (SENSE department, final-year project) exploring how
data extracted from Hospital Information Systems (HIS) can be scraped and
interfaced with, while treating **DPDP Act 2023 compliance as a measurable,
benchmarkable property of each extraction technique** rather than a post-hoc legal
checkbox.

The system has two contribution layers:

1. **Extraction layer** — techniques for pulling structured data out of HIS
   portals (Tier 2: credentialed headless-browser automation).
2. **Compliance layer** — every extraction technique is designed and benchmarked
   against DPDP Act 2023 criteria. This is the research differentiator.

The long-term motivating vision — an AI agent that helps hospital staff use and
adapt to HIS systems without workflow disruption — informs the architecture but
sits beyond this project's graded scope.

## Project status

Post Review-1 (approved). Now in the build phase, targeting Review 2 (~70%
completion).

**Live HIS data access is not usable yet.** Credentialed access is secured on
paper but unavailable for building. All current work runs against
self-generated synthetic HIS data, behind an adapter boundary so a live source
can be swapped in later without downstream refactoring.

## Build order

| Step | Deliverable | State |
|------|-------------|-------|
| 1 | Repo scaffolding + project structure | done |
| 2 | DPDP compliance framework — criteria as code-checkable rules/schema | in progress (4 rules: DM/LB/SL/SS) |
| 3 | Synthetic HIS data generator — records matching the five-layer HIS architecture | thin slice (field catalogue + generator) |
| 4 | Extraction module skeleton — Tier 2 adapter interface, first against synthetic data | thin slice (MockHISDataSource) |
| 5 | Compliance benchmarking harness — scores any extraction run against DPDP criteria | pending |
| 6 | LLM-agent scaffolding (AXE-method inspired), against synthetic data | pending |
| 7 | Swap synthetic source for live HIS, re-run benchmarks | blocked (data access) |

Do not skip ahead to step 7. Keep the data source pluggable throughout steps 1–6.

**Current state:** end-to-end thin slice working — synthetic records →
field-selective extraction → DPDP compliance score. Concrete:

- `src/compliance/` — 4 executable DPDP rules (DM-01, LB-01, SL-01, SS-01), a
  declarative purpose policy, and a `ComplianceReport` artifact.
- `src/data_synthetic/` — field catalogue (name → HIS layer → DPDP category) and
  a Faker-seeded record generator.
- `src/extraction/` — `HISDataSource` interface + a working `MockHISDataSource`.
- `src/interop/` — five-layer HIS enum + layer → interoperability-standard map.

Demos (each scores three runs — compliant / partial / careless):
`python scripts/score_extraction_run.py` and
`python scripts/run_synthetic_extraction.py`. Plain-language run-and-demo
instructions: [`DEMO_GUIDE.md`](DEMO_GUIDE.md). Method walkthrough:
[`docs/compliance/approach.md`](docs/compliance/approach.md).

Working assumptions (accepted as the working set): the five-layer HIS model, the
`care_coordination` purpose, and citing DPDP Act 2023 principles by name rather
than pinned section numbers. Revisit if/when real HIS access lands.

## Repository layout

```
src/
  compliance/       DPDP rule definitions, checkers, benchmarking harness
  data_synthetic/   synthetic HIS data generator (schemas + generators per layer)
  extraction/       scraping/extraction layer (adapter pattern: mock vs live)
  agent/            LLM-based extraction agent (AXE-inspired)
  interop/          HL7 / FHIR / DICOM / ISO-IEEE-11073 schema helpers + layer map
tests/
docs/
  architecture/         five-layer HIS architecture notes
  compliance/           DPDP Act 2023 provision -> rule index
  benchmark_results/     benchmark run artifacts (gitignored)
CLAUDE.md               persistent context for Claude Code
PROJECT_CONTEXT.md      deeper research background
```

## Setup

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# POSIX:    source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then fill in ANTHROPIC_API_KEY locally
pytest
```

## Team

- Avanindra (23BLC1089)
- Ananya (23BLC1017)
- Guide: Dr. Manoj Kumar

## Further reading

- [`CLAUDE.md`](CLAUDE.md) — build order, conventions, phase constraints
- [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) — research framing, review structure, technical foundations
