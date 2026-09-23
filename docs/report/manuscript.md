# Measuring Data-Protection Compliance of Hospital Data Extraction Techniques: Executable DPDP Act Rules and a Benchmark Against Public AI Models

*Manuscript, draft 1, 2026-09-23. A condensation of Chapters 3–7 of the
project report, in a generic IEEE conference shape (~3,600 words and three
tables, before references);
the target venue and page budget are to be decided with the guide, and the text
is to be cut to that budget. The two result tables are generated from the
artefacts by `python tools/report_tables.py`. Group voice; references are the
report's verified IEEE list.*

*Authors: Avanindra, Ananya — School of Electronics Engineering (SENSE), VIT
Chennai. Guide: Dr. Manoj Kumar.*

---

**Abstract** — Techniques for extracting data from hospital information
systems are evaluated on whether they run, how much they extract and what they
cost — never on whether the extraction was lawful. We make compliance with
India's Digital Personal Data Protection Act, 2023 a measured property of an
extraction technique. Seven of the Act's principles become executable rules
over a manifest that every run must file — what was extracted, for which
purpose, on which basis, kept for how long, under which safeguards — and the
rules score field categories, never values. The rules are set beside a cost
profile metered at the data-source boundary, in which the fields a technique
pulls beyond the purpose's need are simultaneously a cost and the overreach
data minimisation forbids. Two further measures separate declarations from
facts: manifest veracity, which checks each declared control against what the
deployment can show, and trap tasks, whose wording invites a violation the
purpose does not permit. We compare a rule-driven technique with three publicly
available AI models given the same job, briefed with field names only, and with
a coverage-optimised baseline, on synthetic data, on a login-gated portal
scraped by a real browser, and on a public export we did not generate. The
models match the rule-driven technique on the manifest they declare, but take
1.4–1.7 times the fields the tasks need while obtaining only 74–81 % of them;
unaided, none holds a single trap; handed the purpose policy itself, all obey
its numbers and two of three still take data its categories forbid; and none
reproduces its own decisions reliably. The rule-driven technique holds every
trap, reproduces itself in every repeat, and loads 32 pages where the baseline
loads 440. We contribute (i) executable compliance rules over an extraction
manifest, (ii) a benchmark whose cost measure is also a compliance measure,
with veracity, trap and stability measures beside it, (iii) a purpose matrix
showing compliance to be a property of a pull and its purpose together, and
(iv) an end-to-end pipeline — structure discovery, pseudonymised export
verified by audit, and a role-gated staff assistant — in which the same policy
table does the scoring and the gating.

*Index Terms* — data protection, DPDP Act 2023, hospital information systems,
web data extraction, compliance measurement, data minimisation, large language
models, benchmarking.

---

## I. Introduction

A hospital information system (HIS) holds the most sensitive personal data an
organisation keeps: identities, diagnoses, prescriptions, payments. Data leaves
such systems constantly — for referrals, billing, registries, analytics — and
increasingly by automated extraction: browser automation against a portal, a
scheduled export, or, most recently, an AI agent told what is wanted and left
to fetch it [2]–[5]. The literature evaluates these techniques on whether they
execute, how much of the target they extract, and at what cost [1]–[5]. It does
not ask whether a given extraction was lawful.

India's Digital Personal Data Protection Act, 2023 (DPDP Act) [13] asks exactly
that. Processing must be for a specified, lawful purpose; data must be limited
to what that purpose needs; it must be kept no longer than the purpose
requires, protected by reasonable safeguards, and disclosed to the person it
concerns; and the fiduciary must be able to *demonstrate* all of it. Analyses
of the Act for healthcare are doctrinal [10], [11], and compliance guidance for
scraping is a checklist [12]. None scores a technique.

We treat compliance as a property of an extraction technique that can be
measured, compared and verified. Our claim is not that one technique is
lawful; it is that lawfulness can be scored, per principle, on the same scale
for every technique, and set beside cost — and that doing so separates
techniques that look alike on every conventional metric. The claim is tested
against three publicly available AI models, the class of technique most likely
to be deployed next and the one whose compliance is least transparent.

We make it without a hospital's data. A hospital export is the personal data
of its patients and may never be released to a research project; we do not
assume it. The evaluation runs on synthetic data, on a login-gated portal that
a real browser scrapes, and on a public export we did not generate, and every
number is regenerable from the repository.

## II. Related Work

**Web data extraction.** Surveys of scraping tools classify techniques by
mechanism [1]. Recent work uses language-model agents to generate or execute
extractors: AutoScraper progressively builds a scraper from page structure and
reports executability and correctness [2]; AXE lowers cross-domain extraction
cost [3]; WebLists converts agent execution on interactive sites into
replayable programs [4]; Co-Scraper prunes the DOM by query and synthesises
reusable scrapers [5]. Their metrics are correctness, coverage and cost; none
records the purpose of an extraction or scores it against one.

**Measurement of scraping behaviour.** Web-measurement studies observe what
scrapers do after the fact — whether they evade bot detection [6] or honour
`robots.txt` [7]. They measure behaviour across the web, not the compliance of
a technique against a statute.

**Hospital information systems and interoperability.** Enterprise-architecture
work decomposes a HIS into functional layers [8]; HL7 FHIR is the dominant
interoperability standard for research use [9]. These describe what a HIS is
and how data moves between systems, not the lawfulness of moving it.

**Data protection for health data.** The DPDP Act's implications for healthcare
have been analysed doctrinally [10] and turned into recommendations for the
sector [11]; the legal and ethical considerations of research scraping have
been set out as a checklist [12]. The mechanisms we build on — tokenisation of
identifiers [14], role-based access control in HIS [15] and audit logs [16] —
are each described in isolation and never composed into an evaluation.

**The gap.** Extraction techniques are evaluated without reference to the law
that governs their output, and the law is analysed without a way to evaluate a
technique against it. We close the gap by making the law's principles
executable over a record every technique must produce.

## III. Compliance as Executable Rules

**The manifest.** Every extraction run files an `ExtractionRun` manifest: the
purpose it serves and whether one was specified; the lawful basis and its
reference; declared onward uses; retention and the deletion mechanism; the
security posture (transport and at-rest encryption, access control,
pseudonymisation of identifiers); the notice given; and governance controls
(audit log, accountable party, record of processing). Beside it the run lists
what it extracted as *categories* — direct identifier, quasi-identifier,
contact, clinical, financial, administrative — derived from a field catalogue
that maps every field of a five-layer HIS model [8] to its category. The rules
never see a value, so the artefacts they produce contain no personal data.

**Seven rules.** Each principle is one rule with its own check mechanism and a
score in [0, 1]:

- *DM-01, data minimisation* — extracted categories within the purpose's
  permitted set; and, for a task about one patient, records read against that
  patient's own, counted by the harness, not declared by the technique.
- *LB-01, lawful basis* — a recognised basis, declared with a reference.
- *SL-01, storage limitation* — retention within the purpose's ceiling, and a
  deletion mechanism.
- *SS-01, security safeguards* — the share of required safeguards in place.
- *PL-01, purpose limitation* — a specified, recognised purpose; declared onward
  uses assessed for compatibility against the other purposes' envelopes.
- *NT-01, notice* — a notice recorded that covers the declared purpose.
- *AC-01, accountability* — the share of governance controls in place.

The Act has no free-standing minimisation article; DM-01 derives from s.6(1)
read with s.4(1). The mapping of every rule to its sections was verified
against the Gazette text [13].

**A purpose policy, deliberately non-nested.** Three purposes are modelled —
care coordination, billing settlement, patient registration — each with a
permitted category set, a retention ceiling (90, 365 and 180 days) and a
pseudonymisation requirement. No purpose's permitted set contains another's,
and a test asserts it. The property matters: if purposes nested, compliance
would reduce to a strictness ranking, and "out of scope" would mean "more
sensitive". Non-nested, it means *not necessary for this purpose* — the Act's
own test. Claims adjudication, which needs clinical codes for a financial
purpose and would nest, is left unmodelled for that reason.

## IV. Techniques and the Benchmark

**The adapter boundary.** Every technique reads data only through one
interface, `fetch(layer, fields, where)`, implemented by an in-memory source, a
browser-driven portal adapter and a file-backed dataset adapter. Techniques
written against the first run against the others unchanged, which tests
assert, and everything a technique does is observable at the boundary.

**Techniques.** *Ours* pulls exactly what the purpose policy makes necessary
and files a full manifest from the policy and a capability register — a list
of the controls the deployment actually provides. *AI models* are given the
job in words, the purpose, the canonical catalogue's field names — never a
value — and the capability register, and decide for themselves what to pull and
what to declare; the pipeline performs the fetch. Three briefings are scored as
separate techniques: *unaided*; *told the Act*, adding the seven obligations in
plain words; and *told the policy*, adding the purpose's permitted categories,
its retention ceiling and every field's category, with the instruction that the
policy is binding whatever the wording asks — everything our technique reads.
Decisions are recorded once and replayed, so every result reproduces without a
network or a key, and several answers to one brief measure whether a model
repeats itself. The *baseline* pulls every field of every layer and declares
only its transport — the class of coverage-optimised scrapers against which
the literature evaluates.

**Cost, and the quantity that is two things at once.** A meter at the adapter
boundary counts fetches, records, fields, distinct fields and, on the portal,
real browser page loads. The *excess ratio* — distinct fields pulled over
fields the purpose requires — is a cost; it is also exactly the overreach
DM-01 penalises. Cost and compliance are not two axes that trade off: on this
axis they are one quantity seen twice. *Coverage* — needed fields obtained over
needed fields — is the guard rail against a technique that scores well by
pulling less than the task needs. When a *source* lacks a field, every
technique's coverage is capped; the ceiling is measured from the source, per
task — on a task about one patient, from that patient's records — so a
shortfall the data imposes is not blamed on a technique.

**Veracity and traps.** Rules score declarations, and a current model declares
well. Two measures test what declarations cannot. *Veracity* removes every
declared control the capability register cannot back and re-scores; four
controls are not attested but *demonstrated* by the pipeline itself — the
connection's observed scheme, an audit log written by the harness at the
metering boundary, an audit of the exported artefacts for raw identifiers, and
a retention sidecar that a purge erases and logs. *Trap tasks* are ordinary
requests whose wording invites a violation: reconcile an invoice "against the
diagnosis" (clinical data under billing), "note their insurance policy number"
at the registration desk (financial data under registration), "keep a copy for
the research registry" (an onward use), "kept on file for a year" (a care
retention four times the ceiling). A trap is *held* on a run that pulled
nothing out of scope, declared no onward use and kept retention within the
ceiling. Every repeat of every task is scored.

## V. The Pipeline Around the Benchmark

**Acquisition.** A login-gated portal fixture serves any source as
server-rendered HTML over TLS, built on the rule that the extractor does not
control it — no API, no hooks, portal vocabulary in its URLs. A real browser
logs in, crawls from the home page and infers each module's HIS layer from the
field names it finds, never from the URL; a map from display labels to
catalogue fields transfers the classification to a portal that shows labels.
The dataset adapter reads a directory of exported files, classifies each by its
columns, takes a column map, stacks one-file-per-concept tables into layers,
reads every value as text so identifiers keep their leading zeros, and refuses
an export it understands none of. A handling gate refuses to read any
non-synthetic directory unless it is git-ignored and carries a provenance note
stating its de-identification status.

**Export and the assistant.** Extracted rows are shaped to HL7 v2 and FHIR with
direct identifiers replaced by keyed tokens when the manifest declares it, and
the audit then searches the artefacts for every raw value extracted. A
rule-based staff assistant recognises one of thirteen functions and answers
with steps for the asker's role; whether a role may be told a function is
*derived* — the categories lawful under the role's purposes intersected with
those carried by the interoperability artefacts it handles — and the gate runs
before any detail is collected. The policy table that scores the benchmark is
the one that gates the assistant.

## VI. Evaluation

**Setup.** The in-memory workload has eight tasks, four of them traps, six
about one patient, over 50 synthetic records per layer. The portal workload has
four tasks (one trap) over 20 records per module, ten per page. The public
export is the Synthea sample: 108 synthetic patients in 18 CSV files, one per
clinical concept, that we did not generate. The three models are
`gemini-3.1-flash-lite` (five runs per task under each briefing) and
`claude-haiku-4-5` and `claude-sonnet-5` (two runs per task told the policy,
one unaided — the minimum that places a model in the tables and measures
whether it repeats itself), sampled at their providers' defaults.

**Table I.** One row per technique, each model told the policy; in memory.

<!-- table:agents -->
| Technique | Runs per task | Compliance | Trap runs held | Coverage | Excess | Record excess | Stable |
|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | 5 | **1.000** | **20 / 20** | 1.00 | 1.00 | 1.00 | **32 / 32** |
| claude-haiku-4-5, told the policy | 2 | 0.996 | 8 / 8 | 0.79 | 1.56 | 0.82 | 0 / 8 |
| claude-sonnet-5, told the policy | 2 | 0.994 | 6 / 8 | 0.81 | 1.66 | 0.91 | 6 / 8 |
| gemini-3.1-flash-lite, told the policy | 5 | 0.984 | 10 / 20 | 0.74 | 1.43 | 0.98 | 21 / 32 |
| unconstrained (baseline) | 5 | 0.100 | 0 / 20 | 1.00 | 7.77 | 136.4 | 32 / 32 |
<!-- /table:agents -->

**Compliance as scored is close; everything else is not.** On the compliance
score every model lands within a few hundredths of ours: each declares a lawful
basis, retention, a deletion mechanism, encryption, a notice and an accountable
party, and cites the register correctly (veracity 1.00 in all but one run).
The baseline scores 0.100 and fails every rule. The separation lies in the
columns the score does not show.

*Traps.* Unaided or told the Act, no model held a single trap run — 48 runs in
all. Told the policy, every model set every retention exactly at the purpose's
ceiling and dropped the onward use: all three obey the policy's numbers.
Whether they obey its categories differs: one model held all four traps; one
held three and took the diagnosis for billing in every run; one held the two
that turn on a number or a declaration and none of the two that turn on taking
a field. A sentence in the request outranked a table in the same prompt for two
of three models. Ours held all four in every run, because the wording is not an
input to it.

*Coverage and excess.* Told the policy, the models took 1.43–1.66 times the
fields the tasks need and obtained 74–81 % of the fields the tasks need — a
name where the task needs a record number, an e-mail where it needs a phone.
Each substitute is a lawful category, so the score is untouched; the job is
not done as specified. Over-collection and under-collection at once is why
excess and coverage must be read together.

*Stability.* Given the same brief again, the models reproduced their first
decision — the same fields and the same manifest structure — in 21 of 32, 6 of
8 and 0 of 8 repeats; the last changed its field selection in seven of eight
repeats while holding every trap. Ours and the baseline reproduced themselves
in every repeat: neither samples. A model's compliance is a sample from a
distribution, and deploying one deploys the distribution.

*Cost.* On the portal, ours reads a patient through the search box — 32 page
loads for the four tasks against the baseline's 440, a factor of fourteen, at
identical coverage; the baseline reads 50 times the patient's own records to
answer for one. The fields a model takes beyond the job cost real pages: 35, 36
and 55 page loads.

*Weights.* Re-scoring under twenty-one alternative weightings of the seven
rules never places a technique above ours or moves the baseline from last.
With DM-01 dropped, the models told the policy tie ours at 1.000: without the
minimisation rule, the difference is invisible to the score.

**Table II.** One unchanged extraction by our technique, judged under every
purpose (in memory).

| Pull | Care coordination | Billing settlement | Patient registration |
|---|---|---|---|
| Care pull (clinical, identifiers; 30 days) | **1.000** (declared) | 0.857 — clinical, quasi-identifier out of scope | 0.893 — clinical out of scope |
| Billing pull (financial, contact; 30 days) | 0.857 — contact, financial out of scope | **1.000** (declared) | 0.893 — financial out of scope |

The same records, manifest and rules score 1.000 under the declared purpose and
lower under another, in both directions: the care pull is unlawful for billing
because clinical data is not necessary to settle an account, and the billing
pull unlawful for care because financial and contact data are not necessary to
coordinate treatment. Compliance is a property of the pull and its purpose
together.

**Export audit.** For one patient's summary on the portal, our export — two HL7
v2 messages and four FHIR resources — contains no raw identifier among six
artefacts; the baseline's — 80 messages and 260 resources, read from every
module — contains 60 of the 60 raw identifiers it extracted. The manifest's
claim and the output's property agree in both cases, which is what makes the
manifest worth scoring.

**Table III.** The four-task workload on the public export.

<!-- table:public -->
| Technique | Compliance | Coverage | Excess | Records read ÷ the patient's own | Trap held |
|---|---|---|---|---|---|
| compliance-aware (ours) | **1.000** | 0.61 | 0.61 | 0.51× | 1 / 1 |
| claude-haiku-4-5, told the policy | 0.999 | 0.56 | 0.94 | 1.03× | 1 / 1 |
| gemini-3.1-flash-lite, told the policy | 0.994 | 0.50 | 1.06 | 1.06× | 0 / 1 |
| claude-sonnet-5, told the policy | 0.992 | 0.56 | 1.17 | 1.06× | 0 / 1 |
| unconstrained (baseline) | 0.113 | 0.72 | 4.44 | 548.8× | 0 / 1 |

Coverage ceiling, measured from the export: 11 of the 18 fields the tasks need are obtainable; 5 are not in the export and 2 are not in the records of the patient a single-patient task is about.
<!-- /table:public -->

**A structure we did not write.** The export passed through the handling gate
as real data. With a column map written once, 11 of its 18 files were read and
29 of its 258 columns entered the pipeline; the SSN, passport and licence
columns stopped at the adapter. The ranking held. Coverage fell for everyone
because the ceiling is the export's: five needed fields are not in it and two
are not in the chosen patient's records, and the technique that shows more
coverage than the ceiling — the baseline — reached it by reading other
patients' records. The run exposed five defects in the adapter that our own
data could not have, each now fixed and tested: identifiers read as numbers,
which silently broke the patient join; a dropped column counted against its
file; an export understood not at all still benchmarked, because an empty pull
breaks no rule; one table kept per layer; and a coverage ceiling taken from the
widest-reading technique.

## VII. Discussion and Threats to Validity

**What the results say.** A current model, given the facts, writes a manifest
as good as ours; the Act's paperwork is not where rule and model differ. They
differ where the Act's substance lies — what is taken, for what, and whether
the same answer comes twice — and those differences are visible only because
the benchmark measures coverage, traps and stability beside the score. Telling
a model the policy closes part of the gap and not the rest: it obeys numbers
and not categories, and for most models a sentence in the request outweighs
the policy in the same prompt. A rule-driven technique is immune not by tuning
but by construction: the wording is not an input to it.

**Threats.** The portal is our fixture; it demonstrates the mechanism of
browser-driven extraction, not robustness to a vendor's interface, which only
live access would test. No hospital data was used; the rules see categories,
not values, so the compliance figures do not depend on distributions, and a
public export narrowed the structural gap, but a hospital's own structure is
unseen. Two of three models were sampled twice per task: enough to show that
decisions vary, not to characterise the distribution, and the told-the-policy
differences between models are suggestive rather than established; the unaided
result — no trap held in 48 runs — is not. The capability register, the traps
and the baseline are ours; four register controls are demonstrated by the
pipeline rather than attested, each trap is a plausible request whose purpose
and needed fields are lawful, and the baseline is a lower bound on what a
published scraper, which declares no more, would score. The policy models three
purposes in one setting.

## VIII. Conclusion

Compliance with a data-protection law can be a measured property of an
extraction technique rather than a claim about a system. Seven executable rules
over a manifest, a cost measure that is also a compliance measure, and two
measures that separate declarations from facts distinguish techniques that
conventional metrics cannot: publicly available AI models that write a
faultless manifest take more than the job needs, obtain less of what it needs,
yield to the wording of a request, and do not repeat themselves, while a
rule-driven technique does the job, holds the line and repeats. The same policy
table that scores extraction gates what staff may be told, and every result is
regenerable from the repository, with no hospital data required.

---

## References

[1] R. N. R. Ruchitaa, S. Nandhakumar Raj, and M. Vijayalakshmi, "Web Scrapping Tools and Techniques: A Brief Survey," in *Proc. 2023 4th Int. Conf. Innovative Trends in Information Technology (ICITIIT)*, 2023.

[2] W. Huang *et al.*, "AutoScraper: A Progressive Understanding Web Agent for Web Scraper Generation," in *Proc. 2024 Conf. Empirical Methods in Natural Language Processing (EMNLP)*, Miami, FL, USA, 2024, pp. 2371–2389.

[3] A. Mansour, K. W. Alshaer, and M. Elsaban, "AXE: Low-Cost Cross-Domain Web Structured Information Extraction," arXiv:2602.01838, 2026.

[4] A. Bohra *et al.*, "WebLists: Extracting Structured Information from Complex Interactive Websites Using Executable LLM Agents," arXiv:2504.12682, 2025.

[5] S. Wang, J. Qiu, W. Zhang, and C. He, "Co-Scraper: Query-Aware DOM Pruning and Reusable Scraper Synthesis for Lightweight Web Data Extraction," arXiv:2606.14821, 2026.

[6] R. Gundelach, M. Mühlhauser, and D. Herrmann, "Detecting Bot Detection: Prevalence, Techniques, and Implications for Web Measurement Research," arXiv:2606.14525, 2025.

[7] T. Kim, K. Bock, C. Luo, A. Liswood, C. Poroslay, and E. Wenger, "Scrapers Selectively Respect robots.txt Directives: Evidence From a Large-Scale Empirical Study," in *Proc. 2025 ACM Internet Measurement Conf. (IMC)*, Madison, WI, USA, 2025, pp. 541–557, doi:10.1145/3730567.3764471.

[8] D. A. Purnawan and K. Surendro, "Building Enterprise Architecture for Hospital Information System," in *Proc. 2016 4th Int. Conf. Information and Communication Technology (ICoICT)*, Bandung, Indonesia, 2016.

[9] C. N. Vorisek, M. Lehne, S. A. I. Klopfenstein, P. J. Mayer, A. Bartschke, T. Haese, and S. Thun, "Fast Healthcare Interoperability Resources (FHIR) for Interoperability in Health Research: Systematic Review," *JMIR Medical Informatics*, vol. 10, no. 7, art. e35724, 2022, doi:10.2196/35724.

[10] V. Khanna and A. Kotwal, "Examining the Significance of the Digital Personal Data Protection Act, 2023 in the Context of the Healthcare Industry: A Comprehensive Analysis," *Discover Public Health*, vol. 22, art. 381, 2025, doi:10.1186/s12982-025-00757-6.

[11] A. Sood *et al.*, "Challenges and Recommendations for Enhancing Digital Data Protection in the Indian Medical Research and Healthcare Sector," *npj Digital Medicine*, vol. 8, art. 48, 2025, doi:10.1038/s41746-025-01448-x.

[12] M. A. Brown, A. Gruen, G. Maldoff, S. Messing, Z. Sanderson, and M. Zimmer, "Web Scraping for Research: Legal, Ethical, Institutional, and Scientific Considerations," *Big Data & Society*, 2025.

[13] *The Digital Personal Data Protection Act, 2023*, Act No. 22 of 2023, The Gazette of India, 11 Aug. 2023.

[14] C. V. Cook, "Tokenization techniques for privacy-preserving healthcare data: tokenization nuts and bolts," *Frontiers in Drug Safety and Regulation*, vol. 5, art. 1599217, 2025, doi:10.3389/fdsfr.2025.1599217.

[15] M. A. de Carvalho Junior and P. Bandiera-Paiva, "Health Information System Role-Based Access Control Current Security Trends and Challenges," *Journal of Healthcare Engineering*, vol. 2018, art. 6510249, 2018, doi:10.1155/2018/6510249.

[16] A. Rule, M. F. Chiang, and M. R. Hribar, "Using electronic health record audit logs to study clinical activity: a systematic review of aims, measures, and methods," *Journal of the American Medical Informatics Association*, vol. 27, no. 3, pp. 480–490, 2020, doi:10.1093/jamia/ocz196.
