# Compliance approach — reviewer walkthrough

A one-page account of how the project treats DPDP Act 2023 compliance as a
measurable property of an extraction technique. Companion to
[`dpdp-provision-map.md`](dpdp-provision-map.md).

## The claim

Existing HIS scraping work is evaluated on speed, robustness, and coverage.
This project adds a fourth axis — **data-protection compliance** — and makes it
a number, produced by the same harness for any technique, so techniques can be
compared on it.

## How a run is represented

A compliance rule cannot inspect "a scrape" in the abstract, so an extraction is
expressed as data ([`compliance/models.py`](../../src/compliance/models.py)):

- **`ExtractionRun`** — the manifest a technique declares: processing `purpose`,
  `lawful_basis` (+ reference), `retention_days`, `deletion_mechanism`, and a
  `SecurityPosture` (TLS, at-rest encryption, access control, pseudonymisation).
- **`ExtractedRecord`** — a sample of what came out, tagged only by
  `FieldCategory` (`direct_identifier`, `quasi_identifier`, `clinical`,
  `financial`, `administrative`, `contact`). No values, so benchmark inputs
  carry no personal data.

## The policy

[`compliance/policy.py`](../../src/compliance/policy.py) holds `PURPOSE_POLICY`:
per processing purpose, the field categories that are *necessary for that
purpose*, the maximum retention, and whether identifiers must be pseudonymised.
This is the auditable "what is allowed" — tuning the compliance envelope is a
policy edit, not a rule-code change. Three purposes are modelled —
`care_coordination`, `billing_settlement`, `patient_registration` — and no
purpose's scope contains another's (see *Purpose limitation, demonstrated* below).

[`compliance/roles.py`](../../src/compliance/roles.py) applies the same table to
**staff roles**: a role may be instructed to touch a data category only where a
purpose it acts under makes it necessary *and* an interoperability artefact it
handles (HL7 v2, FHIR, DICOM, ISO/IEEE 11073) carries it. That intersection is the
gate the staff-guidance agent calls before it answers — see
[`dpdp-provision-map.md`](dpdp-provision-map.md#roles).

## The rules

Seven rules ([`compliance/rules/`](../../src/compliance/rules/)), each a distinct
check mechanism, each citing a DPDP Act 2023 **principle** (exact section
citations are left for the report's references, not pinned in code):

| Rule | DPDP principle | Mechanism |
|------|----------------|-----------|
| `DM-01` | data minimisation | extracted categories ⊆ policy-allowed; score = 1 − excess/total |
| `LB-01` | lawful basis for processing | basis declared, recognised, carries a reference |
| `SL-01` | storage limitation | `retention_days` present and ≤ policy max; deletion mechanism declared |
| `SS-01` | security safeguards | fraction of required technical safeguards satisfied |
| `PL-01` | purpose limitation | a purpose is specified, recognised, and not extended by undeclared onward uses |
| `NT-01` | transparency / notice | a privacy notice is recorded and covers the stated purpose |
| `AC-01` | accountability | fraction of governance controls (audit log, named party, processing record) in place |

Each returns a status (`pass` / `fail` / `not_applicable`), a 0–1 score, and
plain-language findings.

## The output

`compliance.checkers.run_all(run, records)` →
[`ComplianceReport`](../../src/compliance/report.py): an overall
`compliance_score` (mean of applicable rule scores), a `rules_passed` count, a
`pass_rate`, the per-rule breakdown with plain-language findings, and an
`ExtractionSummary` ([`compliance/summary.py`](../../src/compliance/summary.py)) —
record count, layers touched, field counts per DPDP category, and which
categories fell outside the purpose policy. It renders three ways — console
table (`render_table`), JSON (`to_json_file`), and Markdown (`to_markdown_file`,
for pasting into slides or the report). Artifacts land in
`docs/benchmark_results/<run_id>.{json,md}`.

## Comparing techniques — the core evidence

A **technique** ([`extraction/technique.py`](../../src/extraction/technique.py))
is a strategy that fulfils an `ExtractionTask` *and* produces its own compliance
manifest — so "compliance-aware" is a property of the technique's design, not a
label added afterwards. Three kinds are implemented
([`extraction/techniques/`](../../src/extraction/techniques/)):

| Technique | Behaviour |
|-----------|-----------|
| compliance-aware (ours) | pulls exactly the task's needed fields, read off the purpose policy; builds its manifest from the capability register, citing each control by identifier; declares transport encryption only as observed |
| ai agent: *provider* (unaided / told the Act) | a publicly available model is given the job in words, the purpose, the field *names* per module and the register, and decides for itself what to pull and what manifest to declare; the pipeline executes the fetch (the model never sees a value); decisions are recorded once and replayed by every demo; the *informed* briefing adds the Act's obligations in plain words |
| unconstrained (baseline) | ignores the task, grabs every field of every layer; no manifest beyond the transport it was observed on. Stands in for a coverage-optimised scraper (cf. AutoScraper, EMNLP 2024); the Review-I panel accepted it as where most deployed systems sit |

[`compliance.benchmark.run_benchmark`](../../src/compliance/benchmark.py) runs
every technique against every task (eight; four of them *traps* whose wording
invites a violation the purpose does not permit), five repeats each with every
repeat scored, and aggregates. `python scripts/run_benchmark.py`:

| Technique | Compliance score | Rules passed | Trap runs held | Repeats that reproduced run 1 |
|-----------|-----------------|--------------|---------------:|------------------------------:|
| compliance-aware (ours) | 1.000 | 7/7 | 20 / 20 | 32 / 32 |
| ai agent: gemini (told the Act) † | 0.948 | 5/7 | 0 / 20 | 19 / 32 |
| ai agent: gemini (unaided) † | 0.941 | 4/7 | 0 / 20 | 15 / 32 |
| unconstrained (baseline) | 0.100 | 0/7 | 0 / 20 | 32 / 32 |

† recorded under the previous brief (2026-09-17); re-recorded under the
record-axis brief, with the third *told the policy* briefing, on 2026-09-18.

The full artifact (`docs/benchmark_results/benchmark.md`) also carries the
per-rule breakdown, a per-task table with the range where repeats disagreed,
what each task needs, what each technique actually pulled over the workload,
the manifest veracity table (declared versus demonstrable, and of the
substantiated claims which the pipeline demonstrates and which the deployment
attests), and the register's evidence lines.

### The second axis: cost

Ranking techniques on compliance alone invites the obvious question — *and what
does that compliance cost?* The harness answers it by metering every technique
identically at the adapter boundary
([`extraction.metering`](../../src/extraction/metering.py)), so no technique
cooperates in its own measurement or could game it.

| Technique | Compliance | Excess ratio | Coverage | Fields pulled | Fetches |
|-----------|-----------:|-------------:|---------:|--------------:|--------:|
| compliance-aware (ours) | 1.000 | 1.00 | 1.00 | 427 | 14 |
| ai agent: gemini (told the Act) † | 0.948 | 1.06 | 0.78 | 1850 | 16 |
| ai agent: gemini (unaided) † | 0.941 | 1.03 | 0.74 | 1810 | 15 |
| unconstrained (baseline) | 0.100 | 7.77 | 1.00 | 13600 | 40 |

Six of the eight tasks are about one patient, and the harness scopes ours to
that patient's records: 161 records over the workload against the baseline's
2,000 — a record excess of 136× that DM-01 now scores as well as the meter.

**`excess_ratio`** is distinct fields pulled divided by the fields the task's
purpose requires. It is a cost measure and a compliance measure at once, because
fields pulled beyond the purpose *are* the overreach the data-minimisation rule
penalises — which is what lets the benchmark claim that here compliance and cost
move together rather than trading off. **`coverage`** is the guard rail: without
it, a technique could score perfectly by pulling nothing.

Both are deterministic — they reproduce on any machine and do not drift with
dataset size, which is what a published benchmark needs. Wall-clock time is
reported beside them (median over repeats) but is hardware-dependent and is not
what any claim rests on.

The two axes are complementary rather than redundant, and the AI agent is why.
On the compliance score it lands within a few hundredths of ours — given the
register, it cites a basis, a retention, a notice and an officer correctly in
every run. On cost it looks as economical as ours — and the economy is partly
a shortfall: coverage 0.74–0.78 means it substituted a name for the record
number and an e-mail for the phone, lawful categories the score cannot see.
The two harder measures then separate the techniques where the score does
not: on the four trap tasks the agent held the line in none of twenty runs
under either briefing, and it reproduced its first decision in about half of
its repeats. Ours holds every trap and repeats itself by construction, because
the prose is not an input to it.

This table is the paper's central claim made concrete: compliance discriminates
between *techniques*, and it is produced by one harness that scores a real
public model and a hand-written baseline on equal terms.


## Purpose limitation, demonstrated

The benchmark varies the *technique* and holds the purpose fixed.
[`compliance.purpose_matrix`](../../src/compliance/purpose_matrix.py) does the
reverse: it takes one unchanged extraction and scores it against every purpose in
the policy. `python scripts/compare_purposes.py` runs it in both directions.

| Extraction | under `care_coordination` | under `billing_settlement` |
|------------|--------------------------:|---------------------------:|
| care pull (identifiers + clinical) | **1.000** | 0.857 — out of scope: clinical, quasi_identifier |
| billing pull (identifiers + financial + contact) | 0.857 — out of scope: contact, financial | **1.000** |
| billing pull, retained 365 days | 0.786 — also breaches the 90-day ceiling | **1.000** |

The records, the manifest and the seven rules are identical down each column.
Only the purpose changed. Two things follow that a single-purpose policy could not
show:

**Compliance is not a property of a data pull.** It is a property of a pull
together with the purpose it was made for. The same records are lawful and
unlawful at once, depending on what they are for.

**The failure runs in both directions, for different reasons.** Care coordination
may not see financial or contact data; billing may not see clinical data. Neither
purpose is a relaxation of the other, so "out of scope" means *not necessary for
this purpose*, not *more sensitive*. The third row adds a second axis to the same
point: billing may hold data for a year against its audit obligation, which is a
different necessity rather than a laxer one.

One honest caveat, stated in the code as well: when an extraction is re-scored
under a purpose it did not declare, its privacy notice is treated as not covering
that purpose — because a notice describes a specific purpose to the Data
Principal. That is a consequence of the substitution, not an adjustment made to
produce the result.

## End to end, on synthetic data

Live HIS access is not usable, so the pipeline runs against self-generated data:

```
data_synthetic.catalogue        field inventory: name -> HIS layer -> DPDP category
data_synthetic.generators       Faker-seeded plain-dict records per catalogue field
extraction.adapters.MockHISDataSource
                                fetch(layer, fields=[...]) -> records projected to
                                the requested fields  (stand-in for Tier 2 scraping)
compliance.checkers.run_all     score the run -> ComplianceReport
```

Three demos:

- `python scripts/run_benchmark.py` — **the headline**: every technique
  compared, the table above; the AI agents replay committed recordings.
- `python scripts/run_synthetic_extraction.py` — one technique, three
  configurations (compliant / partial / careless), records from the generator.
- `python scripts/score_extraction_run.py` — hand-built records, isolates the
  rules with no generator or adapter in the way.

## Assumptions in play (accepted as the working set)

- The five-layer HIS model ([`interop/layers.py`](../../src/interop/layers.py)) —
  a working reconstruction; the team has accepted it for now and will reconfigure
  if real HIS access shows a different structure.
- The three purposes and their allowed-category sets; the role → purpose and role → artefact assignments in `roles.py`.
- Staff names categorised as `administrative`, not `direct_identifier`.
- Rules cite DPDP principles by name; exact section numbers are a report-time
  reference task, deliberately not pinned in code.
