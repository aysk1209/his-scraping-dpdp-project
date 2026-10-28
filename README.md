<p align="center"><img src="assets/banner.svg" alt="DPDP-compliant HIS data extraction" width="100%"></p>

<h1 align="center">Data Extraction Techniques for HIS Towards DPDP Compliance</h1>

<p align="center">
<img alt="python" src="https://img.shields.io/badge/python-3.10%2B-0d9488?style=flat-square">
<img alt="tests" src="https://img.shields.io/badge/tests-392%20passing-16a34a?style=flat-square">
<img alt="browser" src="https://img.shields.io/badge/browser-Playwright-4f46e5?style=flat-square">
<img alt="rules" src="https://img.shields.io/badge/DPDP%20rules-7-0f172a?style=flat-square">
<img alt="license" src="https://img.shields.io/badge/license-MIT-94a3b8?style=flat-square">
</p>

<p align="center">A final-year research project (VIT, SENSE). Compliance with India's Digital Personal Data Protection Act, 2023 is treated as a <b>measurable property of a data-extraction technique</b>, not a checkbox applied afterwards.</p>

## What it is

Seven principles of the Act are written as executable rules. Every extraction technique declares a manifest of what it pulled and why; the same rules score every technique on equal terms, beside a cost measured in units that reproduce on any machine (page loads, fields, records). The contribution is that **measurement framework**. Our own technique is its *reference implementation*: it executes an expert field list per job, so it is an upper bound by construction. What the framework reveals is how **public AI models** behave when handed the same job, beside a coverage-optimised baseline.

> The score measures conformance to an executable reading of seven principles and a hospital purpose policy. It is not legal compliance; no lawyer or hospital DPO has reviewed the rules.

## Architecture

```mermaid
flowchart LR
    P["Login-gated HIS portal<br/>(TLS, roles, robots.txt)"] --> B["Playwright browser<br/>login, crawl, paginate"]
    B --> M["Navigation map<br/>layers inferred from fields"]
    M --> T{{"Techniques<br/>reference / AI models / baseline"}}
    T --> C["7 DPDP rules<br/>+ purpose policy"]
    T --> N["HL7 v2 / FHIR export<br/>pseudonymised + audited"]
    N --> R["Retention sidecar<br/>scheduled erasure"]
    C --> K["Ranked benchmark<br/>cost + compliance + traps"]
    T --> A[("Hash-chained<br/>audit log")]
    S["Staff assistant<br/>role-gated, rule-based"] -.same policy.-> C
```

| Layer | What it does | Where |
|---|---|---|
| **Extraction** | Browser-driven scraping of a login-gated portal; each module's HIS layer inferred from its field names, never its URL | `src/extraction/` |
| **Compliance** | Seven DPDP rules, purpose policy, scoring, audit, retention, breach assessment, pseudonymisation | `src/compliance/` |
| **Interop** | HL7 v2 and FHIR shaping, export privacy audit | `src/interop/` |
| **Staff assistant** | Rule-based (no LLM) guidance for reception, nursing and administration, gated by the same policy | `src/agent/` |
| **Fixture portal** | Flask HIS mock the scraper treats as an uncontrolled third-party site | `tools/mock_portal/` |

## Results

<p align="center"><img src="assets/traps.svg" alt="Trap runs held" width="760"></p>
<p align="center"><img src="assets/pageloads.svg" alt="Page loads on the portal" width="760"></p>

Four public models, each handed the purpose policy (permitted categories, retention ceiling, every field's category) but not the job's field list, against the reference technique and the baseline. Full grid of briefings: [`benchmark.md`](docs/benchmark_results/benchmark.md).

<!-- table:agents -->
| Technique | Runs per task | Compliance | Behaviour | Trap runs held, per trap job | Agreement with the field list | Excess | Record excess | Stable | Distinct decisions per job |
|---|---|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | 5 | **1.00** | 1.00 | **20 / 20 (5 · 5 · 5 · 5)** | 1.00 | 1.00 | 1.00 | **32 / 32** | 1 |
| claude-sonnet-5-5, told the policy | 5 | 1.00 | 1.00 | 20 / 20 (5 · 5 · 5 · 5) | 0.69 | 0.89 | 0.75 | 18 / 32 | 1-3 (mean 1.9) |
| claude-opus-5-5, told the policy | 5 | 0.99 | 0.98 | 20 / 20 (5 · 5 · 5 · 5) | 0.80 | 1.22 | 0.88 | 17 / 32 | 1-4 (mean 1.9) |
| claude-haiku-4-5, told the policy | 5 | 0.99 | 0.97 | 20 / 20 (5 · 5 · 5 · 5) | 0.77 | 1.38 | 1.05 | 5 / 32 | 2-5 (mean 3.2) |
| gemini-3.1-flash-lite, told the policy | 5 | 0.97 | 0.94 | 10 / 20 (0 · 0 · 5 · 5) | 0.75 | 1.22 | 1.18 | 21 / 32 | 1-5 (mean 2.0) |
| unconstrained (baseline) | 5 | 0.04 | 0.00 | 0 / 20 (0 · 0 · 0 · 0) | 1.00 | 6.63 | 93.8 | 32 / 32 | 1 |

Trap runs are counted per job (`claim-reconciliation`, `desk-registration`, `ward-summary-registry`, `consultant-file`, five runs each): runs of one job are not independent, so the per-job counts, not a pooled interval, are the evidence. Traps are breaches of the hospital's purpose policy, which only the *told the policy* briefing shows the model. Agreement is the share of the expert field list obtained (ours runs that list); behaviour is DM-01, PL-01 and a retention within the ceiling.
<!-- /table:agents -->

Four public models -- `gemini-3.1-flash-lite` (public API, free tier, provider
default sampling) and `claude-haiku-4-5`, `claude-sonnet-5-5`, `claude-opus-5-5`
(a subscription's command line, reasoning effort pinned high) -- recorded
2026-09-18 to 2026-10-07, five times per job under three briefings. One budget
model against three Claude models on different access paths: the comparison is
between access paths as much as between models. Providers retire models;
reproducibility rests on the committed recordings. Each "AI model" is one
structured decision per job (what to fetch, what to declare); the pipeline
executes it -- it is not an agent with tools.

- **Traps** (read per job in the trap matrix). Not told the hospital's policy,
  no model held more than 10 of 20 trap runs and two held none -- but those runs
  measure agreement with a policy they were never shown, so they are not
  non-compliance. Told the policy, the three Claude models hold every trap run;
  Gemini still takes the diagnosis to reconcile an invoice and the policy number
  at the desk, 5 of 5 each.
- **The job.** Told the policy, they obtain 69-80% of our expert field list at
  0.89-1.38x its size. That is agreement with an expert specification, not a
  compliance verdict -- a clinician could defend some of their extra fields. One
  model ties our score (1.00) on 69% of the list: the difference is coverage and
  determinism, not the score.
- **Repeatability.** Given the same brief again, they reproduced their first
  decision in 5-21 of 32 repeats; ours, a lookup, in 32 of 32.

Every difference between a model told the policy and ours is in the
**behaviour** sub-score (what was pulled and kept), none in the **paperwork**
(the manifest's citations): given the register, no model over-claims a control
(veracity is a null result here). Ours on the portal reads one patient through
the search box the page offers -- see the portal run for its page loads against
the baseline's -- and its export carries no raw *direct* identifier (dates of
birth and PIN codes leave generalised, with a k-anonymity figure), where the
baseline's carries all of them. Six of the controls a manifest can cite are
**demonstrated, not declared**: the TLS session the browser observed, the audit
log written by the harness (hash-chained, kept a year), the export audit, a
retention sidecar that the purge erases and logs, a record of processing
generated from the log, and the access authorisation the scraper needs to get
past the portal's robots.txt.

## Data

**No hospital data, by design.** A hospital's export is its patients' personal data; nothing here assumes it. Everything runs on synthetic data of a realistic five-layer structure, on a portal fixture a real browser scrapes, and on a **public export we did not generate** (Synthea's sample, 108 synthetic patients) that passes through the real handling gate. A real export would be one column map and the same command; `src/compliance/handling.py` refuses it unless it is git-ignored, under `data/`, and has a provenance note.

## Run it

```bash
python -m venv .venv && .venv\Scripts\activate      # POSIX: source .venv/bin/activate
pip install -r requirements.txt                      # exact versions: requirements-lock.txt
python -m playwright install chromium                # once per machine
pytest                                               # the suite, ~2 min
python scripts/run_pipeline.py                       # the whole chain, ~7 min (--repeats 1: ~2 min)
```

`run_pipeline.py` serves a login-gated portal over TLS, logs a headless browser
into it under the hospital's access authorisation (the portal's robots.txt
refuses automated access without one), discovers its modules, runs every technique with real page loads as cost
(every run audit-logged by the harness; the connection observed, not assumed),
shapes the compliant run into HL7 v2 / FHIR with identifiers pseudonymised and
audited, schedules the export for erasure, re-judges one pull under every
purpose, puts one question per role to the assistant, and finally runs the purge
as of the day the retention ends. No network, no key: the AI models replay their
recorded decisions (`AI_AGENT_MODE=replay` is the default; only
`record_ai_agents.py` goes live).

The public export: `python scripts/fetch_public_dataset.py`, then
`python scripts/run_pipeline.py --dataset data/public_synthea --column-map data/public_synthea/column_map.json`.
Other demos, each one command in `scripts/`: `run_benchmark.py`, `compare_purposes.py`,
`show_role_access.py`, `ask_agent.py`, `check_ui_update.py`, `answer_access_request.py`,
`breach_drill.py`, `run_ablation.py`, `run_scale.py`, `run_injection.py`, `rehearse_day_one.py`.
`python scripts/make_readme_figures.py` redraws the figures above from the artefacts.

**Recording the AI models yourself** (optional — recordings are committed;
`pip install -r requirements-record.txt` for the provider SDKs): with `GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` set in your own
shell, `python scripts/record_ai_agents.py --list-models`, then
`python scripts/record_ai_agents.py --repeats 5`; with a Claude subscription and
no key, `--provider claude-code --model claude-opus-5-5` (or `claude-sonnet-5-5`, `claude-haiku-4-5`). The model is briefed
with field *names* and the job; no patient value ever leaves the machine, and the
recordings hold only field names and manifest choices.

## Repository

```
src/          compliance, extraction, interop, agent, data_synthetic
scripts/      every demo and runner (run_pipeline.py is the full chain)
tools/        mock_portal (login-gated HIS fixture), weight_sweep
tests/        392 tests; AI models replay committed recordings
docs/         benchmark_results (committed artefacts CI reproduces), access (column maps)
assets/       figures drawn from the artefacts
```

## Team

Avanindra (23BLC1089) · Ananya (23BLC1017) · Guide: Dr. Manoj Kumar, VIT SENSE. Licence: MIT ([`LICENSE`](LICENSE)); cite via [`CITATION.cff`](CITATION.cff).
