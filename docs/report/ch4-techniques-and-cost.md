# Chapter 4 — Extraction techniques and the cost axis

*Draft 2, 2026-09-16 — §4.2.2, §4.3 and §4.4 revised for the AI-agent
comparison the guide asked for. Target ~1800 words; this draft runs ~2600. Numbers quoted
here are illustrations taken from the tracked artefacts in
`docs/benchmark_results/`; the full tables and their discussion belong to
Chapter 7 and are not repeated. No section of the Act is cited in this chapter;
the data-minimisation principle is referred to by name and its provision is
established in §3.3.1.*

---

Chapter 3 established how a run is scored. This chapter establishes what is
scored: the techniques whose runs the benchmark compares, and the second axis on
which they are compared — what each one costs. The argument of the chapter is
that a technique differs from another in three ways at once — in *what it
pulls*, in *what it declares*, and in *whether it gives the same answer twice*;
that all three can be measured in units a reader can reproduce; and that the
cost measure which carries the comparison, the excess ratio, is not a separate
quantity from the data-minimisation score but the same quantity seen from the
other side.

## 4.1 The adapter boundary

Everything downstream of data acquisition — the techniques, the meter, the
rules, the interoperability shaping, the assistant — is written once, against a
single abstract interface, `HISDataSource` (`src/extraction/base.py`). The
interface is two methods: `layers()`, which reports which of the five HIS layers
a source can serve, and `fetch(layer, **query)`, which yields records for one
layer as plain dictionaries. Records cross the boundary as dictionaries and
nothing else; the interoperability standards are applied on the way *out*
(Chapter 6), not at the source.

Three adapters implement it. `MockHISDataSource` serves synthetic records from
the generator in memory. `PortalHISDataSource` drives a real browser through a
login-gated portal, discovers its modules, and reads tables and record pages
(Chapter 5). `DatasetHISDataSource` reads a directory of exported files, as a
hospital's own extract would arrive. A stub for a live system exists and remains
a stub.

The reason to insist on the boundary is not tidiness. It is the answer to a
doubt raised at our first review — that hospital systems are heterogeneous and a
method built against one would not transfer. The boundary makes the claim
testable: the techniques of §4.2 were written against the in-memory source
and run against the browser-driven portal **unchanged**, and the test suite
asserts it. A new hospital system is a new adapter; the compliance layer,
the benchmark and the assistant do not know which adapter is underneath. The
same property is what allows a real hospital export, when one arrives, to be
benchmarked with no new code beyond a column mapping.

One consequence of the boundary matters for this chapter specifically: because
every technique reaches data only through `fetch`, everything a technique does
can be *observed at the boundary*. That is where the meter of §4.3 sits.

## 4.2 The techniques

A technique (`src/extraction/technique.py`) is a strategy that fulfils an
`ExtractionTask` against a source. A task names its purpose, the job in words,
and the *minimum necessary* fields for it, per layer — the `needed` list. The
technique returns the records it produced and, crucially, **its own compliance
manifest**. Which fields a technique reads and which manifest it emits are both
consequences of its design, and the techniques under comparison differ in both:
ours, which derives both from the purpose policy; the publicly available AI
agents, which decide both for themselves; and the baseline, which decides
neither.

### 4.2.1 Compliance-aware (ours)

The compliant technique pulls exactly the fields the task declares as needed —
those and no others — and emits a full manifest. Its lawful basis is read from
the purpose policy rather than hard-coded, so the technique carries no
per-purpose knowledge of its own; its retention is the lesser of thirty days and
the purpose's ceiling; it declares a deletion mechanism, every security safeguard
including pseudonymisation on export, a notice that covers the purpose in
machine-readable form, and full governance with the hospital's Data Protection
Officer as accountable party. This is what "compliance constrains design from
the start" looks like as code: the technique cannot over-collect, because the
only field list it has is the task's necessary one, and it cannot under-declare,
because the manifest is built from the same policy the rules score against.

### 4.2.2 The AI agents (publicly available models)

The middle techniques are a different *kind* of thing from the other two, and
the benchmark needs them for that reason. The compliant technique asks "what
does this purpose make necessary?" and reads the answer from the policy. The
baseline asks nothing. An AI agent is *asked* — and decides for itself.

Concretely, `AIAgentTechnique` (`src/extraction/techniques/ai_agent.py`) hands
a publicly available model exactly what a developer would hand an extraction
agent: the job in words ("prepare a clinical summary of a patient for the care
team"), the purpose it serves, and the field names each module of the system
exposes. It is *not* shown the task's minimum-necessary list — that list is the
purpose policy's output, which is the thing under comparison; an agent asked
for a patient summary should work out what one needs. The model answers with a
structured decision: the fields to fetch, and every entry of the run manifest
(§3.1) — basis, retention, deletion, safeguards, notice, governance. The
pipeline then executes that decision through the same adapter and the same
seven rules score it. No rule knows an agent produced the manifest.

Three properties of the design are held to, and each is asserted by a test.

- **The model never sees a patient value.** It decides at schema level — field
  names, purpose, obligations — and the pipeline performs the fetch. That is
  how an agent orchestrating a scraper works in any case, and it means the
  comparison can be run against the hospital dataset with no personal data
  leaving the machine.
- **Decisions are recorded and replayed.** Each live decision — field names and
  manifest choices, nothing else — is written to a recording committed with
  the repository; the benchmark and the demonstrations replay it, so results
  reproduce without network access or a key. The recording also holds several
  answers to the same brief, which is what §4.3's determinism measure reads.
- **Two briefings.** *Unaided* gets the job, the purpose and the fields. *Told
  the Act* additionally gets the seven obligations in plain words — the same
  principles the rules encode, stated as a developer would state them in a
  system prompt. Whether prompting alone closes the gap to a rule-driven
  technique is then a measured question rather than an assumed answer.

The provider adapters (`ai_providers.py`) cover three public models behind
their official SDKs — Claude, OpenAI and Gemini — with the model identifier
configurable, so the comparison can be re-run against whatever is current. The
results in Chapter 7 are from `gemini-3.1-flash-lite`, five recorded runs per
task per briefing; the model tier is stated because it is part of the result.

What the agent actually does is the substance of Chapter 7, but its character
can be stated here. It is *good at the paperwork*: even unaided it declares a
lawful basis — citing a section of the Act by number, unprompted — a retention
period, a deletion mechanism, encryption, a notice and an accountable party,
and it passes five to six of the seven rules. Where it differs from a
rule-driven technique is in *which fields it takes* and in *whether it takes
the same ones twice*. It substitutes the human-readable identifier (the name)
for the record number the task needs, takes the laboratory result and the
attending clinician for a summary that did not ask for them, and — put the
same brief five times — returns a different field set in most of them. Neither
failure is visible in the compliance score alone; both are visible in the cost
profile, which is why the benchmark has one.

### 4.2.3 The unconstrained baseline

The baseline represents a scraper tuned purely for coverage — the way extraction
techniques in the literature are evaluated. It ignores the task's `needed` list
and pulls every field of every layer the source exposes, and it declares no
manifest beyond the transport being encrypted. It does not specify a purpose,
because a general-purpose scraper has none of its own.

We state plainly that the baseline is hand-written, and why that is acceptable.
An earlier plan called for a literature-faithful implementation of a published
coverage-optimised scraper as the baseline. The review panel's position, recorded
at the second review's preparation, was that the majority of deployed systems sit
at the baseline's level of compliance — a scraper with no manifest and no purpose
is not a straw man but the common case — and that a faithful reimplementation
would add engineering effort without adding to the argument. The baseline
therefore stands as a *coverage-optimised extractor with no compliance manifest*,
and published scrapers of that kind are cited as related work rather than
reproduced. The comparison the benchmark makes is between design stances, not
between our code and someone else's.

### 4.2.4 What they have in common

All of them implement the same interface, take the same task, and return the
same output shape. None of them knows it is being benchmarked, metered or
scored. The rules of Chapter 3 see one `ExtractionRun` manifest and one list of
category-tagged records per run and cannot tell which technique produced which.
That is the fairness property the benchmark rests on, and it is a property of
the interfaces, not of our good intentions.

## 4.3 Metering at the boundary

The first review asked us to report processing time alongside the compliance
score. We took the deeper requirement to be a *defensible way to quantify what
separates the techniques* beyond their scores, and wall-clock time alone is not
that: it moves with the machine, the dataset size and the network, so a reader of
the paper cannot reproduce it. We report it, but we do not lean on it.

Instead, a `MeteredSource` (`src/extraction/metering.py`) wraps whatever adapter
is in use and counts what passes through `fetch`. Because every technique reaches
data only through that method, every technique is measured identically, without
cooperation, without instrumentation in technique code, and without anything a
technique could game. The meter records:

| Metric | Deterministic | What it captures |
|---|---|---|
| `fetches` | yes | Calls to `fetch` — one per layer a technique asked for |
| `page_loads` | yes | Pages the browser actually loaded, when the source is a portal |
| `records` | yes | Rows returned |
| `fields_pulled` | yes | Field values returned, with repetition across rows |
| `distinct_fields` | yes | Distinct (layer, field) pairs touched |
| `needed_fields` | yes | Distinct pairs the task declared as necessary |
| `matched_fields` | yes | Needed pairs the technique actually obtained |
| `excess_ratio` | yes | `distinct_fields / needed_fields` — how far past the purpose |
| `coverage` | yes | `matched_fields / needed_fields` — did it do the job |
| `stable_runs` | yes | Of *k* identical runs, how many reproduced the first run's decision — the same fields *and* the same manifest structure |
| `stable_fields` | yes | The same, for the field selection alone |
| `elapsed_ms` | **no** | Wall-clock; the median over repeats when repeated |

All but the last reproduce on any machine and are independent of dataset size
in the ratios, which is why they lead. Per-task costs are combined into one
profile per technique by micro-averaging — summed numerators over summed
denominators — so a task with many needed fields weighs more than a task with
few, matching how the workload is actually run.

**Determinism is measured, not asserted.** The benchmark runs every technique
*k* times on identical input and compares each run's decision with the first:
the set of fields pulled, and the manifest reduced to its structure — whether a
basis, a notice, a deletion mechanism, an accountable party were declared, not
how the declaration was worded, so that two runs citing the same section in
different words count as the same decision. A rule-driven technique reproduces
itself *k* of *k* times by construction; an agent's figure is whatever it is,
and it is reported in the same table as its compliance score. The measure was
added because the guide's question — is a deterministic technique better than
"just AI"? — is not answerable from a compliance score, which is a property of
one run, but only from the spread across runs.

**Page loads are real cost.** Against the in-memory source a fetch is a
dictionary lookup and `page_loads` is not reported. Against the portal the
adapter reads a field from the list table when it is a list column, and opens a
record page *only* when a requested field lives on the record page alone. A
technique that asks for more than it needs therefore loads more pages, and the
meter reports the difference as the browser's own page count. On the pipeline's
default portal the compliant technique loads 70 pages over the three-task
workload; the baseline loads 330 for the same coverage. Nothing in the
comparison is simulated: those are pages a browser fetched.

## 4.4 Excess ratio and DM-01 are one quantity seen twice

The metric that carries the argument is the excess ratio. On the pipeline's
workload the compliant technique touches 13 distinct fields where the tasks
require 13 — a ratio of 1.00; the baseline touches 93 for the same 13 — a ratio
of 7.15. The observation the chapter exists to make is that this number is
**simultaneously a cost measure and a compliance measure**. Fields pulled beyond
what the purpose requires are precisely the overreach that the data-minimisation
rule (§3.3.1) penalises. The rule expresses it as a set-containment score over
categories; the meter expresses it as a count over fields; but the thing being
measured is the same thing. Cost and compliance are not two axes that trade off
against each other. On this axis they are one quantity viewed from two
directions.

That lets the results chapter make a sharper claim than "compliance is
affordable". It can say that on this workload **the compliant technique is the
cheap one, and the overreach the baseline pays for in page loads is exactly the
overreach the law objects to.** The claim does not depend on any particular
number coming out any particular way — that is the point of it. It is a
statement about what the excess ratio *is*, and it would hold on a hospital
dataset with different fields and different counts.

**Coverage is the guard rail.** Excess ratio alone can be gamed: a technique that
pulls nothing has an excess ratio of zero and a perfect DM-01, having extracted
no category outside the purpose. Coverage — needed fields actually obtained over
needed fields — closes that door, and it is the metric that catches the AI
agents. Their compliance scores on the workload are 0.955 and 0.991, within a
few hundredths of ours, and their excess ratios 1.10 and 1.05 — read alone,
nearly as economical as the compliant technique. Their coverage is 0.74: they
obtained under three-quarters of what the tasks lawfully required, because they
took a name where the task needed a record number, an e-mail where it needed a
phone, and a visit timestamp where it needed the appointment time. A high
compliance score on the wrong fields is not the job done; low cost here is
partly a shortfall, not efficiency. Both metrics are needed to tell the story,
and the benchmark's own summary line names the two cases separately — a
technique that pulled more than the purpose needs, and a technique that pulled
less than the task needs.

A third case exists and the benchmark distinguishes it: a *source* that does not
carry a needed field caps every technique at the same coverage, including the
baseline that pulls everything it can see. When that happens the shortfall is a
property of the dataset, not of any technique, and the report says so rather
than marking the compliant technique down. This case was built for the hospital
export, where a missing column is likely, and it is what keeps the benchmark
honest on data we did not generate.

---

*Cross-references to fill in at assembly: Chapter 3 (§3.3.1 DM-01; §3.4 the
policy the compliant technique reads its basis from), Chapter 5 (the portal
adapter, list versus record pages, layer inference), Chapter 7 (the benchmark
tables from which the numbers above are taken; the appointment-reminder task).*
