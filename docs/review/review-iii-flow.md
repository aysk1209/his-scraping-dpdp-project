# Review-III — presentation flow, executables, and what each moment rests on

The final review, **26.10.2026**. It decides most of the grade, so the flow is
built to show the most the project does, in the order that makes the claim
strongest: **the result first, the evidence live, the robustness against things
we did not build, then the finished deliverables.** The panel saw the pipeline
tour at Review-II; this review does not repeat it as a tour.

*The template and its rubric for Review-III had not arrived when this was
written (2026-10-06). The timings assume an 18-minute slot weighted like
Review-II (technical depth and implementation quality carrying most marks);
re-budget them against the rubric when it arrives.*

---

## 0. Before the room

| Do | Why |
|---|---|
| `python -m playwright install chromium` (once per machine) | the portal and update demos drive a real browser |
| `python scripts/run_pipeline.py` once, discard the output | warms Chromium and the imports |
| `python tools/build_review_pages.py` | rebuilds every page from the current results (~2 min) |
| Open `docs/review/index.html`, then each page in its own tab; press `A+` on each | the interactive half of the demo, offline |
| Open `docs/benchmark_results/benchmark.md`, `benchmark-portal.md`, `benchmark-portal-v2.md` | the fallback if anything fails |
| Terminal: font ≥ 16 pt, ≥ 100 columns | the tables are wide |
| No key, no network needed | every AI decision is replayed from the committed recordings (`AI_AGENT_MODE=replay` by default) |

If the browser will not launch: `python scripts/run_benchmark.py` runs every
technique in memory in under three seconds, and the committed results files
carry the page-load numbers. Say so plainly and continue.

---

## 1. The flow (~18 minutes)

| # | Beat | Time | Where | What it proves |
|---|---|---|---|---|
| 0 | Start `python scripts/run_pipeline.py` **before speaking** | — | terminal | it runs behind beats 1–3 (~2.5 min) |
| 1 | The claim, with numbers | 1:00 | slide | compliance can be measured |
| 2 | Why it is hard | 1:30 | slide | the gap in the literature |
| 3 | One picture | 1:00 | slide | one policy table, three uses |
| 4 | **Rules vs AI agents** | 3:30 | `rules-vs-just-ai.html` + finished terminal | the contribution |
| 5 | Compliance is enforced, not declared | 2:00 | terminal stages 4, 5, 7 + `journey.html` | evidence, not paperwork |
| 6 | Data we did not make | 2:00 | `dataset-walkthrough.html`, `real-data.html` | the path holds on unseen data |
| 7 | **The HIS is updated** | 3:00 | `his-update.html`, then `assistant.html` (hand over the keyboard) | maturity: nothing hard-coded |
| 8 | A patient asks | 1:00 | `python scripts/answer_access_request.py` | the Act's right of access, answered from evidence |
| 9 | Rigour | 0:45 | slide | reproducible, tested, honest about uncertainty |
| 10 | Deliverables and limits | 1:15 | slide | report, manuscript, what is not claimed |
| 11 | Close | 0:30 | slide | the one sentence |

### Beat 1 — the claim (slide)

> DPDP compliance can be a **measured property of a scraping technique**. Ours
> scores 1.000, holds every trap in 20 of 20 runs, does the whole job and gives
> the same answer every time, and loads 32 pages for what the "grab everything"
> baseline needs 440 pages and a score of 0.11 to do.

### Beat 3 — one picture (slide)

Sources → Acquisition → Extraction → {Scoring, Export, Guidance} ← **one policy
table**. It scores the extraction, gates what leaves as HL7/FHIR, and gates
what the assistant may tell a member of staff.

### Beat 4 — rules vs AI agents (the contribution)

Four public models — Gemini flash-lite, Claude Haiku 4.5, Sonnet 5.5 and Opus
5.5 — each recorded five times per task under three briefings (480 decisions),
handed the job, the purpose and the field *names*, never a value.

Say, in this order:

1. **Without our policy, no model is reliable.** Unaided or told the Act in
   plain words, the models held **35 of 160** trap runs (95% interval
   0.16–0.29); Gemini and Haiku held none.
2. **Handed the policy word for word, the three Claude models hold every trap**
   (60 of 60) and Gemini still takes the diagnosis for billing in every run.
   *They comply when given the table our technique applies directly.*
3. **Even then they do 71–78% of the job** and take up to 1.6× the fields the
   purpose needs; Sonnet 5.5 scores a perfect 1.000 *while doing 71% of the
   job* — the compliance score alone cannot tell compliance from doing less,
   which is why the benchmark reports coverage beside it.
4. **And they do not repeat themselves**: 5–21 of 32 repeats reproduced the
   first decision, and no model's 95% interval reaches 0.81. Ours: 32 of 32,
   by construction.

On the page: the briefing selector (unaided → told the Act → told the policy)
shows the trap column filling as the policy is handed over; the coverage column
does not.

### Beat 5 — enforced, not declared

From the terminal the pipeline just finished:
- **[4] NORMALISE**: ours exports two HL7 messages and four FHIR resources with
  every identifier replaced by a token — the export audit finds **0** raw
  identifiers; the baseline's export carries **60 of 60**.
- **[5] PURPOSE**: the same pull scores **1.0 for care, 0.83 for billing** —
  compliance is a property of a pull *and* its purpose.
- **[7] RETAIN**: the purge the manifest names erases the export on the day,
  and the erasure is in the audit log.

Then `journey.html`: one line of a patient file through all seven stages; pick
`SSN` (stopped at the door) and `Id` (pseudonymised, erased on schedule).

### Beat 6 — data we did not make

`dataset-walkthrough.html`: Synthea's public sample, 18 files we never saw —
**29 of 258** columns admitted, SSN and passport stopped by the adapter; the
ranking holds. `real-data.html`: the hospital's own collection register, 731
days, read through the same gate — aggregate, no patient in it, and the page
says what it can and cannot answer.

### Beat 7 — the HIS is updated (new since Review-II)

`his-update.html`. A simulated vendor release: every module renamed and moved,
billing split in two, fields moved onto record pages, headers relabelled, every
button renamed.

- Tab 1: the change report, written by the comparison of two crawls.
- Tab 2: pick *administrator*, then *discharge a patient and release the bed*:
  before and after side by side. **25 of 29 tasks re-worded themselves; nothing
  in the code changed.**
- Tab 3: the two changes nothing could predict ("Unit", "Close episode") are
  **withheld with the reason, not guessed**. Press *Confirm both proposals*:
  29 of 29.
- Tab 4: the scraper on the updated portal — **14 of 14 rows identical** on
  compliance, coverage and traps; only the cost moved (32 → 53 page loads,
  because the release put fields behind record pages).

Then `assistant.html` and hand over the keyboard: pick a role, type anything a
receptionist or a nurse would say. Reception asking for a diagnosis is refused
before being asked a single detail, with the rule cited. `help` lists the
role's 10–16 tasks; a patient asking for a copy of their data is a privacy
request the desk logs and routes.

### Beat 8 — a patient asks

```
python scripts/answer_access_request.py
```

The data-protection contact's tool. The patient's summary: what was read, for
which purpose, which categories, what was exported and the date it will be
erased — no value from the record, the record number masked. Then the line that
lands: **a patient no task was about** had their records read by ours in **2 of
8** runs (the whole-ward tasks) and by the baseline in **8 of 8**.

### Beat 9 — rigour (slide)

- the full test suite (count from `pytest -q`), and CI re-derives the
  benchmark and every report table on each push;
- AI decisions recorded once and replayed, so the numbers reproduce on any
  machine without a key;
- every run scored, not a best draw; 95% intervals beside every model count.

### Beat 10 — deliverables and limits (slide)

The report (eight chapters, appendices A–E, every table generated from the
results), the manuscript (venue: *fill in*), the code and the review pages.
Limits stated plainly: a portal we built rather than a vendor's; no
patient-level hospital data (assumed never to arrive — the public export and
the hospital's aggregate register stand in); five samples per model;
one-provider-family models plus one other.

### Beat 11 — close

> The rules that make an AI agent compliant are the rules we built; our
> technique applies them directly — completely, identically every time, and
> provably, from the evidence it leaves behind.

---

## 2. Questions to expect, and where the answer is

| Question | Answer, briefly | Evidence |
|---|---|---|
| "Isn't 5 samples too few?" | Intervals are printed; the conclusions that matter hold at the interval's edge (no model's repeatability reaches 0.81; unaided traps 0.16–0.29) | ch7 §7.8, Table 1 |
| "Sonnet scores 1.000 too — so why yours?" | It does 71% of the job and repeats itself 18 of 32 times; it complied because it was handed our policy | Table 1, weight sweep |
| "Would a better prompt fix the models?" | Possibly the traps; three of four already hold them told the policy. It does not fix coverage or determinism | ch7 §7.8 |
| "What if the vendor changes the screens?" | Beat 7: one crawl; 14/14 scraper rows identical; the assistant re-words, and withholds what it cannot place | `his-update.html` |
| "Is the assistant an LLM?" | No. Rules, a registry, the policy gate. Deterministic by choice | ch6 §6.4 |
| "Where is the hospital's data?" | Assumed never to arrive (privacy); public export + aggregate register; the path is one column map away | ch5, ch7 §7.7 |
| "Which DPDP sections?" | Rules name principles; the section mapping was verified against the Gazette text | `docs/compliance/dpdp-provision-map.md` |

---

## 3. The executables, one line each

| Command | Shows |
|---|---|
| `python scripts/run_pipeline.py` | the whole chain, live, on the benchmarked portal |
| `python scripts/run_pipeline.py --layout v2` | the same chain on the updated portal (`benchmark-portal-v2`) |
| `python scripts/run_benchmark.py` | every technique in memory, under 3 s |
| `python scripts/check_ui_update.py` | the update, in the terminal |
| `python scripts/answer_access_request.py` | a patient's access request |
| `python scripts/ask_agent.py --interactive` | the assistant, typed |
| `python scripts/compare_purposes.py` | one pull, every purpose |
| `python tools/build_review_pages.py` | rebuild every page |
