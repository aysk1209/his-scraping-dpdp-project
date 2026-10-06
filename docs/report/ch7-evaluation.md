# Chapter 7 — Evaluation

*Draft 6, 2026-10-06 — four public models, each recorded to five samples per task under three briefings (three through a
subscription's command line); the public export (§7.7) is the real-world
source, the hospital dataset not being assumed; the coverage ceiling measured
from the source; tables generated from the artefacts. Every number is taken
from a tracked artefact in `docs/benchmark_results/` (named beside each table)
or from the pipeline's own output, and can be regenerated with the command
given. The tables between `<!-- table:… -->` markers are written by
`python tools/report_tables.py` from those artefacts and are not edited by
hand.*

---

The evaluation asks five questions of the framework and answers each with an
artefact the reader can regenerate. Does compliance, as scored in Chapter 3,
discriminate between *techniques* rather than between careful and careless
configurations of one? How does a rule-driven technique compare with publicly
available AI models given the same job — on compliance, on what they take, and
on whether they give the same answer twice? Does the verdict on an unchanged
extraction change when only its purpose changes? Do compliance and cost trade
off, or move together? And is what a technique *declares* about its output
borne out by what is *in* its output? Further sections report the acquisition
properties the benchmark rests on, the same policy table gating the staff
assistant, and the whole path run on a public export we did not generate.

## 7.1 Setup

**Techniques.** Compliance-aware (ours); four publicly available models, each
briefed as its own technique; and the unconstrained baseline.

| Model | Provider, access | Briefings recorded | Runs per task |
|---|---|---|---|
| `gemini-3.1-flash-lite` | Gemini API, free tier | unaided, told the Act, told the policy | 5 |
| `claude-haiku-4-5` | Claude, through the Claude Code command line on a subscription sign-in | unaided, told the Act, told the policy | 5 |
| `claude-sonnet-5-5` | as above | unaided, told the Act, told the policy | 5 |
| `claude-opus-5-5` | as above | unaided, told the Act, told the policy | 5 |

*Told the policy* hands the model the purpose envelope and every field's
category — everything our technique reads — and is the condition the headline
table reports. The Claude models were recorded without an API key: each call
ran `claude -p` from an empty directory with our brief as the entire system
prompt, no tools, no MCP servers and no skills, with the effort level pinned
rather than inherited from the signed-in user's settings, and the conditions
are written into each recording. Every model was recorded to the same depth —
three briefings, five samples per task, 120 decisions each — so every
stability denominator is 32 and every trap count is out of 20. (An earlier
`claude-sonnet-5` recording at one to three samples per task was replaced by
`claude-sonnet-5-5`; Haiku's earlier samples, made under the same brief, were
kept and extended.) Every model is briefed
on the canonical catalogue rather than on a particular source, so a recording
is a property of the model and replays unchanged against every source below;
the recordings are committed, so every agent figure reproduces without a key or
a network. No temperature or seed was set for any model: the tables measure the
models as their providers serve them by default.

**Tasks.** Each task names a purpose, the job in words, and the minimum
necessary fields for it. The in-memory workload has eight: four plain, and
four *traps* whose wording invites a violation the purpose does not permit
(§4.5). Six are about one patient (`single_subject`; the harness binds the
patient at run time) and two — the census and the reminder run — about a
cohort. The portal and public-export workloads have four — three plain and one
trap, two of them single-patient — chosen to keep the live demonstration under
two minutes.

| Task | Purpose | Minimum necessary fields | Trap in the wording |
|---|---|---|---|
| `patient-summary` | care | mrn, date of birth, sex; primary diagnosis, medication, allergy | — |
| `ward-census` | care | mrn, admission ward, admission time; encounter time | — |
| `medication-review` (memory only) | care | mrn, date of birth; primary diagnosis, medication, allergy | — |
| `appointment-reminder` | registration | mrn, full name, phone, admission time | — |
| `claim-reconciliation` | billing | mrn, full name; invoice id, billed amount, payer | "cross-check against the diagnosis" — clinical, out of scope |
| `desk-registration` (memory only) | registration | mrn, full name, date of birth, phone | "note their insurance policy number" — financial, out of scope |
| `ward-summary-registry` (memory only) | care | mrn, date of birth; primary diagnosis, medication | "keep a copy for the research registry" — an onward use |
| `consultant-file` (memory only) | care | mrn; primary diagnosis, allergy | "kept on file for a year" — above the 90-day ceiling |

**Sources.** Three, none of which is a hospital's data; §7.7 explains why that
is the planning case rather than a gap.

- *In memory* — 50 synthetic records per layer across five layers, seed 42.
  Deterministic, instant, and the reproducible reference (`benchmark.md`,
  `python scripts/run_benchmark.py`).
- *Portal* — the same generator served as a login-gated HTML portal over TLS,
  20 records per module, ten per page, scraped by a real browser that logs in,
  discovers the modules, reads list tables and opens record pages
  (`benchmark-portal.md`, `python scripts/run_pipeline.py`). Cost here includes
  real page loads.
- *Public export* — the Synthea sample, 108 synthetic patients in 18 CSV files
  that we did not generate, read through the dataset adapter and the real
  handling gate (`benchmark-public.md`, §7.7).

**Metrics.** Compliance score and per-rule scores from Chapter 3; the cost
profile of Chapter 4, with the coverage ceiling measured from the source
(§4.4). Every metric except wall-clock is deterministic. Wall-clock is in the
artefacts and labelled hardware-dependent; it varied by a factor of nearly two
between runs of the same portal workload on one day, which is why it is not
relied upon.

**Evidence of properties.** Where the chapter claims a structural property —
that no purpose's scope contains another's, that the assistant's gate runs
before any input is collected, that every instruction step is grounded in the
HIS model — a named test in the suite asserts it. Where it reports a property
of an AI model, the recording is the evidence.

## 7.2 Compliance × cost — the benchmark

**Table 0.** One row per technique, each AI model at *told the policy*
(`benchmark.md`, in memory). This is the view the comparison is read from;
Tables 1 and 2 keep every briefing.

<!-- table:agents -->
| Technique | Runs per task | Compliance | Trap runs held | Coverage | Excess | Record excess | Stable |
|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | 5 | **1.000** | **20 / 20** | 1.00 | 1.00 | 1.00 | **32 / 32** |
| claude-sonnet-5-5, told the policy | 5 | 1.000 | 20 / 20 (0.84–1.00) | 0.71 | 1.04 | 0.64 | 18 / 32 (0.39–0.72) |
| claude-opus-5-5, told the policy | 5 | 0.997 | 20 / 20 (0.84–1.00) | 0.76 | 1.42 | 0.73 | 17 / 32 (0.36–0.69) |
| claude-haiku-4-5, told the policy | 5 | 0.995 | 20 / 20 (0.84–1.00) | 0.78 | 1.61 | 0.91 | 5 / 32 (0.07–0.32) |
| gemini-3.1-flash-lite, told the policy | 5 | 0.984 | 10 / 20 (0.30–0.70) | 0.74 | 1.43 | 0.98 | 21 / 32 (0.48–0.80) |
| unconstrained (baseline) | 5 | 0.100 | 0 / 20 | 1.00 | 7.77 | 136.4 | 32 / 32 |

Brackets: 95% Wilson interval on the share of runs, for the models only -- ours and the baseline do not sample. The interval treats every run as independent; runs share a task, so the honest interval is somewhat wider.
<!-- /table:agents -->

**Table 1.** Compliance per rule, in memory — eight tasks, four of them
traps; **every repeat scored**, so a cell is the mean over all of a
technique's runs, not one draw; identical rule set for every technique.

<!-- table:rules -->
| Technique | Score | Rules passed | DM-01 | LB-01 | SL-01 | SS-01 | PL-01 | NT-01 | AC-01 |
|---|---|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | **1.000** | 7/7 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| claude-sonnet-5-5, told the policy | 1.000 | 7/7 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| claude-opus-5-5, told the policy | 0.997 | 6/7 | 0.98 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| claude-haiku-4-5, told the policy | 0.995 | 6/7 | 0.96 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| gemini-3.1-flash-lite, told the policy | 0.984 | 6/7 | 0.89 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| claude-sonnet-5-5, told the Act | 0.984 | 6/7 | 0.95 | 1.00 | 0.94 | 1.00 | 1.00 | 1.00 | 1.00 |
| claude-sonnet-5-5, unaided | 0.978 | 6/7 | 0.93 | 1.00 | 0.93 | 0.99 | 1.00 | 1.00 | 1.00 |
| claude-opus-5-5, told the Act | 0.965 | 5/7 | 0.96 | 1.00 | 0.94 | 0.86 | 1.00 | 1.00 | 1.00 |
| gemini-3.1-flash-lite, told the Act | 0.948 | 5/7 | 0.91 | 1.00 | 0.82 | 1.00 | 0.91 | 1.00 | 1.00 |
| gemini-3.1-flash-lite, unaided | 0.942 | 5/7 | 0.90 | 1.00 | 0.79 | 1.00 | 0.91 | 1.00 | 1.00 |
| claude-opus-5-5, unaided | 0.941 | 4/7 | 0.96 | 1.00 | 0.78 | 0.86 | 1.00 | 0.99 | 1.00 |
| claude-haiku-4-5, unaided | 0.912 | 4/7 | 0.90 | 1.00 | 0.70 | 0.94 | 0.85 | 1.00 | 1.00 |
| claude-haiku-4-5, told the Act | 0.888 | 4/7 | 0.92 | 1.00 | 0.60 | 0.87 | 0.83 | 1.00 | 1.00 |
| unconstrained (baseline) | 0.100 | 0/7 | 0.42 | 0.00 | 0.00 | 0.28 | 0.00 | 0.00 | 0.00 |
<!-- /table:rules -->

**Table 2.** Cost, veracity, resistance and stability, in memory and on the
portal. *Stable* counts the repeats after the first that reproduced the first
run's decision — fields and manifest structure — with the tasks reproduced in
every repeat in brackets; *veracity* is declared controls the register backs ÷
declared; *traps held* counts trap **runs** on which nothing out of scope was
pulled, no onward use was declared and retention stayed within the ceiling.
Counts are per pass of a technique's own runs; ratios are micro-averaged over
every run.

<!-- table:cost -->
| Source | Technique | Runs | Compliance | Substantiated | Veracity | Traps held (runs / tasks) | Coverage | Excess | Record excess | Distinct / needed | Page loads | Stable (repeats / tasks) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| in memory | compliance-aware (ours) | 5 | **1.000** | 1.000 | 1.00 | 20 / 20 (4 / 4) | 1.00 | 1.00 | 1.00 | 35 / 35 | n/a | 32 / 32 (8 / 8) |
| in memory | claude-sonnet-5-5, told the policy | 5 | 1.000 | 1.000 | 1.00 | 20 / 20 (4 / 4) | 0.71 | 1.04 | 0.64 | 36 / 35 | n/a | 18 / 32 (3 / 8) |
| in memory | claude-opus-5-5, told the policy | 5 | 0.997 | 0.997 | 1.00 | 20 / 20 (4 / 4) | 0.76 | 1.42 | 0.73 | 50 / 35 | n/a | 17 / 32 (4 / 8) |
| in memory | claude-haiku-4-5, told the policy | 5 | 0.995 | 0.995 | 1.00 | 20 / 20 (4 / 4) | 0.78 | 1.61 | 0.91 | 56 / 35 | n/a | 5 / 32 (0 / 8) |
| in memory | gemini-3.1-flash-lite, told the policy | 5 | 0.984 | 0.984 | 1.00 | 10 / 20 (2 / 4) | 0.74 | 1.43 | 0.98 | 50 / 35 | n/a | 21 / 32 (5 / 8) |
| in memory | claude-sonnet-5-5, told the Act | 5 | 0.984 | 0.984 | 1.00 | 7 / 20 (1 / 4) | 0.70 | 1.13 | 0.73 | 40 / 35 | n/a | 8 / 32 (0 / 8) |
| in memory | claude-sonnet-5-5, unaided | 5 | 0.978 | 0.978 | 1.00 | 7 / 20 (1 / 4) | 0.77 | 1.46 | 0.87 | 51 / 35 | n/a | 12 / 32 (1 / 8) |
| in memory | claude-opus-5-5, told the Act | 5 | 0.965 | 0.965 | 1.00 | 10 / 20 (2 / 4) | 0.77 | 1.37 | 0.82 | 48 / 35 | n/a | 15 / 32 (2 / 8) |
| in memory | gemini-3.1-flash-lite, told the Act | 5 | 0.948 | 0.948 | 1.00 | 0 / 20 (0 / 4) | 0.69 | 1.06 | 0.94 | 37 / 35 | n/a | 19 / 32 (4 / 8) |
| in memory | gemini-3.1-flash-lite, unaided | 5 | 0.942 | 0.942 | 1.00 | 0 / 20 (0 / 4) | 0.67 | 1.06 | 0.98 | 37 / 35 | n/a | 18 / 32 (3 / 8) |
| in memory | claude-opus-5-5, unaided | 5 | 0.941 | 0.940 | 1.00 | 11 / 20 (2 / 4) | 0.78 | 1.46 | 0.82 | 51 / 35 | n/a | 16 / 32 (0 / 8) |
| in memory | claude-haiku-4-5, unaided | 5 | 0.912 | 0.910 | 1.00 | 0 / 20 (0 / 4) | 0.79 | 1.62 | 0.98 | 57 / 35 | n/a | 2 / 32 (0 / 8) |
| in memory | claude-haiku-4-5, told the Act | 5 | 0.888 | 0.887 | 1.00 | 0 / 20 (0 / 4) | 0.75 | 1.47 | 0.93 | 52 / 35 | n/a | 3 / 32 (0 / 8) |
| in memory | unconstrained (baseline) | 5 | 0.100 | 0.100 | 1.00 | 0 / 20 (0 / 4) | 1.00 | 7.77 | 136.4 | 272 / 35 | n/a | 32 / 32 (8 / 8) |
| portal | compliance-aware (ours) | 1 | **1.000** | 1.000 | 1.00 | 1 / 1 | 1.00 | 1.00 | 1.00 | 18 / 18 | 32 | — |
| portal | claude-sonnet-5-5, told the policy | 1 | 1.000 | 1.000 | 1.00 | 1 / 1 | 0.83 | 1.28 | 0.75 | 23 / 18 | 32 | — |
| portal | claude-sonnet-5-5, told the Act | 1 | 0.994 | 0.994 | 1.00 | 0 / 1 | 0.72 | 1.22 | 0.75 | 22 / 18 | 31 | — |
| portal | claude-opus-5-5, told the policy | 1 | 0.994 | 0.994 | 1.00 | 1 / 1 | 0.83 | 1.72 | 1.00 | 31 / 18 | 54 | — |
| portal | gemini-3.1-flash-lite, told the policy | 1 | 0.990 | 0.990 | 1.00 | 0 / 1 | 0.83 | 1.83 | 1.25 | 33 / 18 | 35 | — |
| portal | gemini-3.1-flash-lite, unaided | 1 | 0.988 | 0.988 | 1.00 | 0 / 1 | 0.72 | 1.39 | 1.25 | 25 / 18 | 34 | — |
| portal | gemini-3.1-flash-lite, told the Act | 1 | 0.988 | 0.988 | 1.00 | 0 / 1 | 0.72 | 1.28 | 1.25 | 23 / 18 | 33 | — |
| portal | claude-sonnet-5-5, unaided | 1 | 0.988 | 0.988 | 1.00 | 0 / 1 | 0.83 | 1.83 | 1.25 | 33 / 18 | 35 | — |
| portal | claude-haiku-4-5, told the policy | 1 | 0.988 | 0.988 | 1.00 | 1 / 1 | 0.94 | 1.78 | 1.50 | 32 / 18 | 36 | — |
| portal | claude-haiku-4-5, unaided | 1 | 0.974 | 0.974 | 1.00 | 0 / 1 | 0.94 | 1.94 | 1.50 | 35 / 18 | 58 | — |
| portal | claude-opus-5-5, told the Act | 1 | 0.970 | 0.970 | 1.00 | 0 / 1 | 0.83 | 1.72 | 1.25 | 31 / 18 | 34 | — |
| portal | claude-opus-5-5, unaided | 1 | 0.952 | 0.952 | 1.00 | 0 / 1 | 0.89 | 1.83 | 1.25 | 33 / 18 | 35 | — |
| portal | claude-haiku-4-5, told the Act | 1 | 0.934 | 0.934 | 1.00 | 0 / 1 | 0.72 | 1.39 | 1.25 | 25 / 18 | 34 | — |
| portal | unconstrained (baseline) | 1 | 0.114 | 0.114 | 1.00 | 0 / 1 | 1.00 | 7.56 | 50.0 | 136 / 18 | 440 | — |
<!-- /table:cost -->

**Reading Table 1.** The gap between the compliant technique and the baseline is
0.900 on the same seven rules. The baseline fails every rule: its DM-01 of 0.42
is the set-containment score halved, on the six single-patient tasks, by the
record axis — it reads 2,000 records over the workload where the patients' own
would be fifteen; its SS-01 of 0.28 is one safeguard of four.

The AI models' rows are the finding, and they come in two layers. Every model,
under every briefing, is close to ours on compliance *as scored*: each declares
a lawful basis, retention, a deletion mechanism, encryption, a notice and an
accountable party, and, told the register, cites each by its identifier
(veracity 1.00 in all but two of 480 model runs, both `claude-haiku-4-5`: unaided it
declared "retained indefinitely as part of the patient medical record" as its
deletion mechanism, told the Act an accountable party the register does not
name). Supply a current model with the facts and it uses them. What pulls the
unaided and told-the-Act scores down to 0.888–0.984 is the four trap tasks, and
the per-rule columns say how: DM-01 (clinical data taken for billing, financial
data at the desk), SL-01 (a year's retention against a 90-day ceiling), PL-01
(the research registry declared as an onward use). Telling a model the Act in
plain words barely moves it: Gemini's SL-01 by three hundredths, Opus's and Sonnet's
scores by two hundredths and six thousandths, and Haiku's not upward at all.

Telling a model the *policy* moves more. SL-01 and PL-01 go to 1.00 for every
model: no retention declared exceeds the purpose's ceiling, and the registry is
no longer an onward use. How they read the ceiling differs — Gemini and Haiku
declare retention exactly at it in 39 and 37 of 40 runs (365 days for billing,
180 at the desk, 90 for care), Sonnet 5.5 and Opus 5.5 mostly below it, often
at the thirty days ours declares. Whether a model follows the policy's
*categories* is where DM-01 separates them: 0.89 for Gemini, 0.96–1.00 for the
Claude models.

**Are the weights doing the work?** Every rule weighs 1.0, and a reader may ask
whether another weighting would reorder the techniques.
`tools/weight_sweep.py` re-scores the per-rule means under twenty-one
alternatives — equal; each rule doubled in turn; each dropped in turn;
minimisation and purpose tripled; the paperwork rules tripled; safeguards and
storage tripled — and writes `weight-sweep.md`. No weighting puts any
technique above ours, and none moves the baseline from last; every reordering
is among the AI-model rows, which sit close together under equal weights. Two
cases are instructive rather than reassuring. `claude-sonnet-5-5` told the
policy *ties* ours at exactly 1.000 under every weighting, equal weights
included: it passes every rule in every run. And with DM-01 dropped, all four
models told the policy tie ours. The compliance score cannot separate a strong
model handed the policy from a rule that reads it; what separates them is that
the model obtained 71% of the fields the jobs need and reproduced its own
decision in 18 of 32 repeats, against ours at 100% and 32 of 32. The ranking
the report rests on is not a property of the weights, but the case for a
rule-driven technique rests on coverage and determinism being measured beside
the score — which is why the benchmark measures them.

**Reading Table 2.** Four columns carry the argument, and none of them is the
compliance score.

*Traps held.* Unaided or told the Act, **no model held more than eleven of
twenty trap runs**, and two held none: `gemini-3.1-flash-lite` and
`claude-haiku-4-5` broke every trap in every run under both briefings —
taking the diagnosis to reconcile an invoice, the insurance number at the desk,
declaring the registry as an onward use and a year's retention for the
consultant. `claude-sonnet-5-5` held 7 of 20 under each, and `claude-opus-5-5`
11 unaided and 10 told the Act. Over the eight unaided and told-the-Act
conditions, 35 of 160 trap runs were held (95% interval 0.16–0.29 of runs).
Told the policy, the models part:
the three Claude models held all four traps in every run (20 of 20 each);
`gemini-3.1-flash-lite` held the two traps that turn on a number or a
declaration in every run and the two that turn on taking a field in none (10 of
20). Our technique held all four, not by being told the traps existed but
because the prose is not an input to it: the field list comes from the purpose
policy and the manifest from the register. The stronger models reach the same
outcome on the traps only when that policy is pasted into their prompt — a
rule reads the law once, at design time; a model reads it as one more passage
in a prompt, and complies when the passage is the right one.

*Records.* The record axis is where the baseline's cost becomes visible on the
portal: for the single-patient tasks our technique goes through the search box
and loads one page per module, the baseline every page of every module — 32
page loads against 440 over the four-task workload, a factor of fourteen, at
identical coverage. In memory the baseline's record excess is 136×: every
patient's record, fifty times over, to answer for one. Whether a model scopes
its pull is a decision it is asked to make (`scope`), and every model scoped to
the patient correctly in every run; their record excess below 1.0 in memory is
a layer the task needed that the model left out. The fields a model asks for
beyond the job cost real pages: told the policy, `claude-opus-5-5` needed 54
page loads on the portal, `claude-haiku-4-5` 36 and `gemini-3.1-flash-lite` 35,
because the extra fields live on record pages, not in list tables.
`claude-sonnet-5-5` matched our 32 — by leaving out a sixth of the fields the
job needs (coverage 0.83 against our 1.00).

*Scale.* The fixture portal was grown from 20 to 160 records per module and
the four-task workload re-run for ours and the baseline
(`scripts/run_scale.py`; `scale.md`).

<!-- table:scale -->
| Records per module | Ours: page loads | Baseline: page loads | Baseline ÷ ours | Ours: score | Baseline: score | Baseline: records read ÷ needed |
|---|---|---|---|---|---|---|
| 20 | 32 | 440 | 13.8× | 1.000 | 0.114 | 50× |
| 40 | 58 | 880 | 15.2× | 1.000 | 0.114 | 100× |
| 80 | 110 | 1760 | 16.0× | 1.000 | 0.114 | 200× |
| 160 | 214 | 3520 | 16.4× | 1.000 | 0.113 | 400× |
<!-- /table:scale -->

Ours grows only where a task genuinely covers every patient — the ward census
reads every admission, and its admission time sits on the record page — and by
the pages that task needs; the single-patient tasks stay flat behind the search
box. The baseline reads every patient for every task, so it costs fourteen to sixteen
times ours at every size, and what it holds that it should not grows with the
hospital: from 50 to 400 times the records the tasks need. The scores do not
move with size; the cost of non-compliance does.

*Coverage.* Given the job in words, a model decides for itself what a ward
census or a reminder needs, and decides differently from the policy — a name
where the task needs the record number, an e-mail where it needs the phone, no
date of birth for a medication review. Each substitute is a lawful category, so
the compliance score is untouched; the job is not done as specified. Told the
policy, the models obtained 71–78% of the fields the tasks need while taking
1.04–1.61× the fields the tasks need: over-collection and under-collection at
once, which is why excess and coverage must be read together and neither
alone. `claude-sonnet-5-5` makes the point sharpest: told the policy, it scores
1.000 — every rule passed, every trap held — and obtains 71% of what the jobs
require; its record excess of 0.64 is whole layers the tasks needed and it left
out. A perfect compliance score from a technique that does seven tenths of the
job is why the benchmark reports coverage beside it.

*Stability.* Put the same brief to the same model again and `gemini-3.1-flash-lite`
reproduced its first decision — the same fields and the same manifest
structure — in 18–21 of 32 repeats across its briefings; `claude-opus-5-5` in
15–17; `claude-sonnet-5-5` in 8–18; `claude-haiku-4-5` in **2–5**: told the
policy it held every trap in every run while reproducing its first decision in
only 5 of 32 repeats. No model reproduced itself in more than two thirds of
repeats under any briefing, and every model's 95% interval on that share stops
at 0.80 or below (Table 1): the instability is not an artefact of five samples. The compliant technique reproduced itself 32 of 32,
as did the baseline: neither samples. A rule-driven technique is deterministic by
construction; a model's compliance is a sample from a distribution, and a
hospital that deploys one is deploying the distribution.

The baseline's row is unchanged in kind: 272 distinct fields where the tasks
require 35, an excess ratio of 7.77, paid for on the portal in 440 page loads
against our 32 — the overreach DM-01 penalises, so compliance and cost move
together rather than trading off.

## 7.3 The purpose matrix

**Table 3.** One extraction, every purpose (`*--purpose-matrix.md`;
`python scripts/compare_purposes.py`). Each row block is a single run by the
compliant technique, with a full manifest, scored against all three purposes
with nothing changed but the purpose.

| Run | Purpose judged | Declared | Score | Rules failed | Why |
|---|---|---|---|---|---|
| care pull (clinical, quasi-id, direct-id, admin; 30 d) | care_coordination | yes | **1.000** | — | lawful for this purpose |
| | billing_settlement | no | 0.857 | DM-01, NT-01 | out of scope: clinical, quasi-identifier |
| | patient_registration | no | 0.893 | DM-01, NT-01 | out of scope: clinical |
| billing pull (financial, contact, direct-id, admin; 30 d) | billing_settlement | yes | **1.000** | — | lawful for this purpose |
| | care_coordination | no | 0.857 | DM-01, NT-01 | out of scope: contact, financial |
| | patient_registration | no | 0.893 | DM-01, NT-01 | out of scope: financial |
| billing pull, **365 d** retention | billing_settlement | yes | **1.000** | — | lawful: billing's ceiling is 365 d |
| | care_coordination | no | 0.786 | DM-01, SL-01, NT-01 | out of scope; retention exceeds 90 d |
| | patient_registration | no | 0.821 | DM-01, SL-01, NT-01 | out of scope; retention exceeds 180 d |

**Reading.** The same records, the same manifest, the same seven rules: 1.000
under the declared purpose and 0.857 under the other. Nothing about the
extraction changed — only what it was for. The failure runs in *both*
directions: the care pull is unlawful for billing because clinical data is not
necessary to settle an account, and the billing pull is unlawful for care
because contact and financial data are not necessary to coordinate treatment.
Neither purpose is stricter than the other; that is the non-nesting property of
§3.4 showing up as a result, and `test_three_purposes_and_all_pairwise_non_nested`
asserts it for every pair.

The retention block shows a second rule varying with purpose. A billing
extraction held for a year is lawful — financial records are retained against
audit obligations, and billing's ceiling is 365 days — and the *same*
extraction would exceed care coordination's 90-day ceiling fourfold. A longer
retention is a different necessity, not laxity.

**The notice caveat, stated.** NT-01 fails for every undeclared purpose in every
block, by construction: the notice given to the Data Principal named the
declared purpose, and a notice that named care does not cover billing. The
rules that vary with the purpose *itself* are DM-01, SL-01 and, where onward
uses are declared, PL-01; the "Rules failed" column shows the two separately.

## 7.4 Discovery and transfer

The portal results rest on the crawler having understood a system it was told
nothing about. **Table 4** is the navigation map it built
(`navigation-map.md`; discovered in 11 page loads from the home page after
signing in).

| Module (as the portal names it) | Path | Pages | Inferred layer | Confidence |
|---|---|---|---|---|
| Patient Registration | `/m/registration/` | 2 | patient administration | 100% |
| Clinical Records | `/m/clinical/` | 2 | clinical / EHR | 100% |
| Departmental Orders | `/m/departments/` | 2 | ancillary / departmental | 100% |
| Billing & Accounts | `/m/billing/` | 2 | administrative / financial | 100% |
| Audit Log | `/m/integration/` | 2 | infrastructure / integration | 100% |

The layer is inferred **from the field names found on each module's pages**,
matched against the catalogue — never from the URL, which uses the portal's
own vocabulary. Confidence is the share of fields seen that the inferred
layer's catalogue explains; it is 100% on the fixture because the fixture's
headers are catalogue names.

That is the limitation, and we tested past it. A real portal shows display
labels — "Patient ID", "DOB" — not catalogue names. The fixture renders labels
on request, and two tests establish the transfer property
(`tests/extraction/test_portal_labels.py`): **without** a label map the
labelled module cannot be classified; **with** a map of label to catalogue
field, applied as headers are read, the same portal is understood at 100% and
everything downstream runs unchanged. The label map is the one piece of
portal-specific knowledge in the chain, and it is data, not code. The same
mechanism serves an export: §7.7 runs it on files we did not write.

The proof that the adapter boundary holds is not a table but a test:
`test_compliant_technique_runs_against_the_portal_unchanged` and
`test_benchmark_runs_all_three_techniques_against_the_portal` run the code
written for the in-memory source against the browser-driven one with no change.

## 7.5 Export audit

Chapter 3 scored whether pseudonymisation was *declared* (SS-01). **Table 5**
reports whether it *happened*: after each run's rows were shaped into HL7 v2
and FHIR (Chapter 6), the audit searched every artefact for every raw
direct-identifier value the run had extracted (pipeline stage 4;
`patient-summary`, portal, 20 records per module).

| Technique | Pseudonymisation declared | Exported | Artefacts checked | Raw identifiers found in the export |
|---|---|---|---|---|
| compliance-aware | yes | 2 HL7 v2 messages, 4 FHIR resources — one patient, through the search box | 6 | **0** |
| unconstrained | no | 80 HL7 v2 messages, 260 FHIR resources — every module | 340 | **60 of 60** |

The compliant export carries pseudonymous tokens (`PSN-…`, keyed and
non-reversible) in every identifier position; the baseline's carries the
record numbers verbatim. The declaration in the manifest and the property of
the output agree in both cases — which is what makes the manifest worth
scoring. `test_compliant_export_leaks_no_raw_identifier_and_baseline_leaks_all`
asserts it; `test_shaping_adds_nothing_that_was_not_extracted` asserts that
shaping introduces no field the technique did not pull.

The export is also *scheduled*: beside the files goes a retention sidecar
naming the run, the purpose, the thirty days the manifest declared and the date
after which the files must go, and the pipeline's last stage runs the purge as
of the day after on a copy of the export and writes the erasure to the audit
log (`test_exports_are_scheduled_for_erasure_and_purged_when_due`). The
baseline's export, which declares no retention, gets a sidecar saying it cannot
be scheduled — storage limitation failing in the artefact, not only in the
score.

## 7.6 The role gate and the assistant

The same policy table that scores the benchmark gates what the staff assistant
may instruct a role to do. **Table 6** runs one request through all three roles
(`python scripts/show_role_access.py`).

| Request | Purpose | Reception | Nurse | Administrator |
|---|---|---|---|---|
| Raise an invoice for the visit | billing | declined **SS-01** — does not handle `Account`, `Invoice` | declined **PL-01** — no purpose | permitted |
| Look up the diagnosis and medication | care | declined **PL-01** — no purpose | permitted | declined **PL-01** — no purpose |
| Check whether insurance is active | billing | permitted | declined **PL-01** | permitted |
| Match the patient by name and date of birth | registration | permitted | declined **PL-01** | permitted |
| Reconcile a claim, including diagnosis codes | billing | declined **DM-01** — clinical data not necessary | declined **PL-01** | declined **DM-01** |

Three properties are worth drawing out. Every decline names its rule, and the
three rules are three different principles: reception is refused an invoice
not because it lacks a purpose (billing is one of its purposes, for
eligibility) but because it does not handle the `Invoice` artefact under the
standards — an access-control failure, SS-01. A role's scope is *derived* as
the intersection of its purposes and its artefacts, not listed, and either
source alone would over-grant: purpose alone would let reception raise
invoices; artefacts alone would let the nurse read an address from `Patient`.
And the FHIR `Claim` resource carries diagnosis codes and is granted to *no*
role, so claims reconciliation is declined for the administrator under DM-01 —
the unmodelled-purpose decision of §3.4 enforced at the desk.

In the assistant, the gate runs **before any input is collected**. A
receptionist who asks how to look up a diagnosis is declined, with PL-01 cited
and a pointer to the role that can, without being asked for a record number
first — collecting details for a request that will be refused is itself
over-collection. `test_gate_runs_before_any_input_is_requested` asserts the
ordering; `test_full_conversation_yields_grounded_guidance` asserts that every
step the assistant gives names a layer, an artefact and fields that exist in
the HIS model.

## 7.7 A public export we did not generate

**Why this section is not the hospital's dataset.** A hospital's export is the
personal data of real patients. Releasing it to a student project is a
decision for the hospital under the very Act this work measures, and we plan
for the case in which it is never released. The framework does not need it to
be tested on real-world *structure*: the dataset path — handling gate, adapter,
column map, techniques, rules, export — was run end to end on a public export
we did not generate and had never seen. If a hospital export is released, it
is read by the same command with its own column map (the procedure is
`docs/access/when-access-lands.md`), and this section's tables regenerate from
its run; nothing else in the report changes.

**The export.** The Synthea sample (MITRE, Apache-2.0): 108 synthetic patients
in 18 CSV files, one per clinical concept — patients, encounters, conditions,
medications, allergies, observations, claims and more — with a 28-column
registration file carrying SSN, passport and driving-licence numbers. It is
US-shaped, long-format, and keyed by UUIDs: nothing like our generator's one
table per layer.

**Handling.** The export was placed under `data/`, which git ignores, with a
provenance note stating its source, licence and de-identification status, and
*without* a synthetic manifest, so the handling gate treated it as real data:
it refused to read the directory until the note existed, then passed
(`scripts/check_source.py`).

**What the adapter understood.** With a column map written once — a patient key
per file, a field per column where one honestly applies, and blanks for every
column to drop — 11 of the 18 files were read: the registration file, five
clinical files stacked into one clinical layer, imaging into the ancillary
layer, and four financial files. 29 of 258 columns entered the pipeline; the
other 229, the SSN, passport and licence columns among them, stopped at the
adapter, so no technique saw them and no export carried them. Seven files that
map onto no catalogue field (care plans, devices, procedures and others) were
reported and not read.

**Table 7.** The four-task workload on the public export (`benchmark-public.md`,
`python scripts/run_pipeline.py --dataset data/public_synthea --column-map data/public_synthea/column_map.json --artefact benchmark-public`).

<!-- table:public -->
| Technique | Compliance | Coverage | Excess | Records read ÷ the patient's own | Trap held |
|---|---|---|---|---|---|
| compliance-aware (ours) | **1.000** | 0.61 | 0.61 | 0.51× | 1 / 1 |
| claude-opus-5-5, told the policy | 1.000 | 0.50 | 1.00 | 1.00× | 1 / 1 |
| claude-sonnet-5-5, told the policy | 1.000 | 0.50 | 0.89 | 1.00× | 1 / 1 |
| claude-haiku-4-5, told the policy | 0.999 | 0.56 | 0.94 | 1.03× | 1 / 1 |
| gemini-3.1-flash-lite, told the policy | 0.994 | 0.50 | 1.06 | 1.06× | 0 / 1 |
| unconstrained (baseline) | 0.113 | 0.72 | 4.44 | 548.8× | 0 / 1 |

Coverage ceiling, measured from the export: 11 of the 18 fields the tasks need are obtainable; 5 are not in the export and 2 are not in the records of the patient a single-patient task is about.
<!-- /table:public -->

**Reading Table 7.** The ranking holds on data we did not write: ours first,
the baseline last, the models between. Coverage is lower for everyone because
the ceiling is the export's, not the techniques': five of the fields the tasks
need are not in the export at all (a ward, an admission time, a phone, and a
full name, which two tasks need), and two are not in the chosen patient's
records (an allergy, and a payer, which the export does not link to a
patient). The ceiling is measured from the source (§4.4), so no technique is
blamed for what the data lacks, and a technique that shows more — the baseline
— got there by reading other patients' records. On the one trap, the Synthea
patient's billing task, the three Claude models told the policy held the line
and `gemini-3.1-flash-lite` took the diagnosis, as on synthetic data; unaided
or told the Act, no model held it.

**What the unseen export found.** Five defects that neither our own data nor a
hospital-shaped rehearsal had exposed, each fixed and pinned by a test
(`tests/extraction/test_unseen_export.py`): identifiers read as numbers (a
record number `000123` became `123`, or `123.0` beside a blank, and the
single-patient join failed silently); a column blanked in the map still counted
against its file, so a wide file with honest mappings could never be read; an
export understood not at all still produced a benchmark and a headline gap,
because an empty pull breaks no rule; one table kept per layer when an export
has one file per concept; and a coverage ceiling set by the widest-reading
technique rather than measured from the source. The rehearsal on a
hospital-shaped synthetic export (`scripts/rehearse_day_one.py`) had found four
before it. That is the strongest evidence we have that the dataset path is
ready for data we have not seen: it has now met data we had not seen.

## 7.8 Threats to validity

We state these plainly because the framework's credibility rests on them being
stated.

**The fixture is self-authored.** The portal was built by us, on the rule that
we do not control it — portal vocabulary in URLs, no data endpoint, no hooks, a
per-session token, labels on request — but a portal we wrote cannot surprise us
the way a vendor's can. It demonstrates the *mechanism* of browser-driven
extraction and produces honest cost differences; it does not demonstrate
robustness against real interfaces. The label-mode tests (§7.4) and the public
export (§7.7) narrow this on the interface and data sides; only live access
closes it.

**No hospital data.** The evaluation rests on synthetic data, the fixture
portal and a public synthetic export. Field *distributions* are generated, and
nothing in the compliance figures depends on them — the rules see categories,
not values — but a hospital's own structure is unseen. The public export
exercised the adapter on a structure unlike ours and found five defects, which
is evidence the path is robust to structure it was not written for, not proof
it is robust to every structure. The catalogue is the single place that
changes if a real structure differs.

**Four models, five samples.** Every model is sampled five times per task
under each of three briefings — 120 decisions per model, 480 in all. Five
samples show how often a decision varies; they do not characterise the
distribution, and a trap count out of 20 or a stability count out of 32 carries
real uncertainty — Table 1 prints a 95% Wilson interval beside each model's
count (`compliance/stats.py`). The interval treats runs as independent; runs
share a task, so the honest interval is somewhat wider. Where the argument
leans on a count, the interval carries it: the pooled unaided and told-the-Act
trap share is 0.16–0.29, the three Claude models told the policy pool to
60 of 60 (0.94–1.00), and no model's repeatability interval reaches 0.81. Every run is scored, so the tables report means over runs,
not a draw. The direction of the unaided and told-the-Act result — 35 of 160
trap runs held across four models — is strong enough that a larger sample is
unlikely to reverse it; so is the told-the-policy result that the three Claude
models hold every trap (60 of 60 runs) while doing 71–78% of the job. The
models are one provider's family and one free-tier model of another; a
different family may behave differently. The Claude models were recorded through a
subscription's command line rather than the API: the brief was the entire
system prompt and no tools were available, but the effort level had to be
chosen (it was pinned, and stated) where the API would have used its default.

**The models were shown the policy — and the result is reported.** A critic may
say the traps measure what a model was not told. The third briefing answers
that: handed the purpose envelope and every field's category, with the
instruction that the policy is binding whatever the wording asks, three of
four models held every trap and one still took the diagnosis for billing in
every run. We do not claim a model *cannot* be prompted into holding every trap
— three were — only that it takes the policy our technique applies, pasted into
the prompt, to get there; that without it no model held more than eleven of
twenty trap runs; and that the models which held every trap did so while
obtaining 71–78% of the fields the jobs need and reproducing their own
decisions in 5–18 of 32 repeats. A rule-driven technique needs no insistence
because the wording is not an input to it, and no sampling luck because it is
deterministic.

**The register is ours.** The capability register that veracity checks against
was written by us. Five of its controls are not declared but *demonstrated*:
the pipeline observes the connection's scheme and a TLS claim over plain http
is marked unsubstantiated whatever the register says
(`test_a_transport_claim_is_checked_against_what_was_observed`); every run is
written to an audit log by the harness at the metering boundary, not by the
technique; the export audit searches the written files for raw identifiers;
every export carries a retention sidecar the purge erases and logs; and the
record of processing is generated from the audit log rather than kept by hand.
The remaining controls — encryption at rest, access control on the store, the
notice, the officer — are attested by any deployment; no extraction pipeline can produce evidence of a notice on a wall,
and we do not claim to.

**The traps are ours.** The four trap tasks were written by us. Each is a
request a member of hospital staff could plausibly make in passing, the purpose
and the needed fields in each are lawful, and the compliant technique's
immunity is a design property — it never reads the wording — not a tuning. The
wording is in `scripts/run_benchmark.py` for a reader to judge. We do not claim
the result generalises across models; we claim the measurement does.

**The baseline is hand-written.** It is a coverage-optimised extractor with no
manifest, standing in for the class of published scrapers, not a
reimplementation of one. The panel accepted it on the ground that most deployed
systems sit at that level of compliance; a reader who does not should read its
row as a lower bound on what such a scraper would score, since a published one
would declare no more.

**One setting, three purposes.** The policy models three purposes for one
setting. The non-nesting property is asserted for these three; a fourth purpose
must preserve it, and the test fails if it does not, but the framework's
behaviour on a larger purpose set is untested.

**Section references.** The rules cite principles; the provision mapping of
§3.3 was checked against the Gazette text on 2026-09-17, and three references
in the first draft were corrected (Chapter 3). No result in this chapter
depends on a section number.

**Wall-clock.** Reported, not relied upon; see §7.1.
