# Demo Guide — how to run this project and what to show

This guide assumes **no prior involvement in the project**. Follow it top to
bottom. Every command is copy-paste. Nothing here touches the internet or any
real hospital system — it all runs on fake data on your own machine.

---

## 1. What this project does (read once)

Hospitals keep patient data in large software systems (a "HIS" — Hospital
Information System). Pulling data out of them automatically ("scraping") can
easily break India's data-protection law, the **DPDP Act 2023**.

This project builds a small tool that **gives a data-scraping job a compliance
score** — a number from 0 to 1, plus a pass/fail on seven separate rules (one per
DPDP data-protection principle) — so different scraping methods can be compared on
how lawful they are, not just on how fast they run.

We do not have access to a real hospital system yet, so the tool is exercised
against **synthetic (fake) data** the project generates itself.

---

## 2. One-time setup

### 2a. Install Python

You need **Python 3.10 or newer**.

- Windows: download from <https://www.python.org/downloads/> and, in the
  installer, tick **"Add Python to PATH"**.
- Mac: `brew install python` (or the python.org installer).
- Linux: it is almost certainly already installed.

Check it works — open a terminal (PowerShell on Windows) and run:

```
python --version
```

You should see something like `Python 3.12.x`. If Windows says "not recognized",
close and reopen the terminal, or try `py --version`.

### 2b. Get the project code

If you were given a folder, skip this. Otherwise:

```
git clone https://github.com/aysk1209/his-scraping-dpdp-project.git
cd his-scraping-dpdp-project
```

If you already have the folder, just `cd` into it.

### 2c. Install the project's dependencies

This creates a private, isolated area for the project's libraries so nothing
else on your machine is affected.

**Windows (PowerShell):**

```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Mac / Linux:**

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If PowerShell blocks the activate script, run this once and try again:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

You will know it worked when your prompt shows `(.venv)` at the start.

> From now on, every time you open a new terminal to use this project, `cd` into
> the folder and run the activate line (`.venv\Scripts\Activate.ps1` or
> `source .venv/bin/activate`) again. The `pip install` step is only needed once.

---

## 3. Running the demos

There are **four demo programs**. Each prints a scorecard and saves report files.

### Demo 0 — one patient, end to end (show this first)

```
python scripts/trace_one_patient.py
```

Takes a **single** synthetic patient and walks it through every stage of the
pipeline, printing each one: the raw record as the source holds it (25 fields
across 4 HIS layers) -> the task's declared minimum field set -> a field-by-field
table mapping each field to its DPDP category and whether it is in scope ->
the compliance manifest each technique emits -> all seven rules with a written
reason each -> the score.

The same patient is run through both our compliance-aware technique (**1.000**)
and the coverage-optimised baseline (**0.131**), so the gap is visible field by
field. Use this to explain *how* the score is produced; use Demo A to show that
it holds at scale.

### Demo A — compare scraping methods (the headline)

```
python scripts/run_benchmark.py
```

This runs **three different scraping methods** against the same fake hospital
(three extraction tasks each) and scores every run on compliance:

| Method | What it does | Score you'll see |
|--------|--------------|------------------|
| compliance-aware (ours) | takes only the data the job needs, does the paperwork | **1.000** |
| minimising, undocumented | takes only what it needs, but skips paperwork/security | **~0.500** |
| unconstrained (baseline) | grabs everything on the page, documents nothing | **~0.131** |

The output also shows: a few sample (fake) patient records, a per-task score
table, what each task actually needs, and **what each method pulled** — e.g. the
baseline grabs *600 records across 4 layers* including 150 billing and 150
contact fields it was never asked for, versus *300 records across 2 layers* for
the compliance-aware method.

### The cost table underneath it

A second table reports what each method **cost**, which answers the obvious
question a score alone invites — *what do you give up to be compliant?*

| Method | Excess ratio | Fields pulled | Fetches |
|--------|-------------:|--------------:|--------:|
| compliance-aware (ours) | 1.00 | 750 | 6 |
| minimising, undocumented | 1.00 | 750 | 6 |
| unconstrained (baseline) | 5.00 | 3750 | 12 |

**Excess ratio** is the number to point at: how many fields a method pulled for
every one the job actually required. The compliant method pulls exactly what is
needed (1.00); the baseline pulls five times that. All three obtain everything
the tasks require, so nobody is winning by doing less work — the "coverage"
column in the real output is 1.00 across the board.

The point to make out loud: **the baseline's surplus is not just waste, it is
precisely the overreach the law objects to.** Here, compliance is the cheap
option.

**This is the main thing to show** — the core argument: compliance is a number
that separates good methods from bad ones.

### Demo A2 — the same data pull, judged two ways

```
python scripts/compare_purposes.py
```

Demo A changes the *method* and keeps the job the same. This one does the
opposite: it keeps the data pull exactly the same and changes only **what the
data is for**.

A hospital does two entirely legitimate things. A clinician needs a patient's
diagnosis and medication. The accounts office needs the invoice and an address to
send it to. Both pulls are done properly, by the same careful method. Then each is
scored against *both* jobs:

| The data pulled | Judged as care coordination | Judged as billing |
|-----------------|----------------------------:|------------------:|
| diagnosis + medication | **1.000** — fine | 0.857 — clinical data is none of billing's business |
| invoice + address | 0.857 — billing data is none of care's business | **1.000** — fine |

**Nothing about the extraction changed between the columns. Only the reason for it
did.** That is the whole idea of purpose limitation, shown rather than asserted.

The point to make out loud: **neither job is "stricter" than the other.** Care may
see clinical data and not billing data; billing may see billing data and not
clinical data, and may keep it for a year rather than 90 days because an audit
requires it. So "out of scope" does not mean "too sensitive" — it means *not
needed for this particular job*. A scraping method cannot be compliant in the
abstract, only compliant for a stated purpose.

### Demo A3 — who may be told to do what

```
python scripts/show_role_access.py
```

Shows what each staff role (reception, nurse, administrator) may be instructed to
do, and puts the same request through all three at once. A receptionist asking
about a diagnosis is declined; a nurse asking to raise an invoice is declined; the
administrator is declined from a claim that carries diagnosis codes. **Every
refusal names the DPDP rule that produced it.**

The point to make out loud: a role's access is not a list someone typed. It is
*derived* — from the purposes the role lawfully acts under, and from the HL7 /
FHIR / DICOM / ISO-IEEE-11073 artefacts it handles under the standards. The same
policy table that scores the scraping benchmark decides what the assistant may say
to whom. This is the compliance half of the staff-guidance agent; the agent itself
sits on top of it.

### Demo D — the assistant, in conversation

```
python scripts/ask_agent.py
python scripts/ask_agent.py --interactive
```

Four short scenes. A receptionist registers a walk-in and gets numbered steps,
each tagged with where in the HIS it happens and, where it matters, a one-line
reason (search before creating; read the notice before saving). The same
receptionist then asks what is wrong with the patient — and is refused, **before
being asked for a single detail**, with the rule named and a pointer to who *can*
answer. An administrator types just "insurance" and is asked which of two things
they meant. A nurse records vitals, then asks to raise the bill and is refused for
the opposite reason.

The point to make out loud: **there is no AI model in this.** It is a fixed list
of hospital functions, word matching, and templates — and one call to the
compliance policy before it speaks. The reason it is in a compliance project at
all is that the refusal comes from the same table that scores the scraping
benchmark. If someone asks "how is it trained?", the answer is: it isn't, by
design.

Use `--interactive` if a reviewer wants to type their own request.

### The mock hospital portal (what the scraper will point at)

```
python -m tools.mock_portal --records 500
```

Then open <http://127.0.0.1:8765/> in a browser and sign in as **frontdesk /
letmein**. You will see a plain hospital-style portal: four modules (Registration,
Clinical Records, Departmental Orders, Billing & Accounts), each a paginated table
with a search box and an "Open" link per record that shows the fields the table
does not.

It is deliberately built as a system **we do not control**: a login form with a
token, a session cookie, a redirect if you are not signed in, no API, and a
`robots.txt` that disallows everything. The point is that the scraper has to do
what it would do against a real hospital portal — nothing here is arranged for its
convenience. Use `--records 5000` to make it page for a long time, and
`--latency-ms 40` to make it feel remote. Stop it with Ctrl-C.

### Demo B — one method, three configurations

```
python scripts/run_synthetic_extraction.py
```

Takes a single method and runs it carefully, half-carefully, and carelessly,
using fake patient records generated on the spot. Expected:
**1.000 / ~0.500 / ~0.131**. Useful for showing *why* a score moves.

### Demo C — the rules on their own

```
python scripts/score_extraction_run.py
```

The seven rules scored against hand-written examples, with no data generator in
the way. Prints every rule, pass/fail, and a plain-English reason
(e.g. *"Out-of-scope category extracted: financial"*). Expected:
**1.000 / ~0.500 / ~0.107**.

### The test suite (optional but reassuring)

```
python -m pytest -q
```

Runs every automated check on the code. You should see **`91 passed`**. This
confirms the rules, the fake-data generator, the extraction methods, and the
comparison harness all behave as intended.

---

## 4. What to show the reviewers

A five-minute walkthrough. Have a terminal open in the project folder with the
environment activated.

1. **The mechanism, on one record:** `python scripts/trace_one_patient.py`.
   Walk the panel down the stages — the record, the task, the category table,
   the manifest, the seven rules, the score. This answers "what is actually
   happening" before any aggregate number is shown.

2. **The one-page explanation.** Open
   [`docs/compliance/approach.md`](docs/compliance/approach.md). Read out the
   "The claim" section — that compliance becomes a *measured number*, produced by
   the same tool for any scraping method.

3. **Run Demo A live:** `python scripts/run_benchmark.py`. Point at the
   comparison table — our method 1.00, the coverage-optimised baseline 0.13, on
   the same seven rules. This is the core result.

   Then drop to the cost table underneath and make the second point: the
   baseline pulls **5x** the fields the purpose requires, at the same coverage.
   Compliance did not cost anything here — the surplus the baseline pays for is
   the same surplus the minimisation rule penalises. (This answers the Review-I
   panel's request to show processing time; wall-clock is in the table too, but
   the excess ratio is the number that reproduces on any machine.)

4. **Run Demo A2** — `python scripts/compare_purposes.py`. This is the second
   result to show, and the one that is hardest to argue with: the same records,
   the same paperwork, the same seven rules, lawful for one purpose and not for
   another — in both directions. It is the DPDP purpose-limitation principle
   turned into an experiment.

5. **Run Demo B** if asked why a score moves:
   `python scripts/run_synthetic_extraction.py` — same method, three
   configurations, each rule failing with a stated reason.

6. **Show a saved artifact.** Open `docs/benchmark_results/benchmark.md` and
   `docs/benchmark_results/care-pull--compliance-aware--purpose-matrix.md` — both
   results as files. This is the evidence the research paper is built on.

6. **Run the tests:** `python -m pytest -q` → `91 passed`. Shows the work is
   real, checked code, not slideware.

**Three points to make while doing this:**

- Compliance is **measured, not asserted** — the score comes out of rules, each
  tied to a DPDP Act 2023 principle.
- The **same harness** scores every method on equal terms. Right now the baseline
  is a stand-in for a coverage-optimised scraper (cf. AutoScraper); swapping in a
  real implementation is the next step, and the table is already built for it.
- It **works today with zero hospital access**. When real access arrives, the
  data source is swapped by one configuration change — the rest of the pipeline
  is unaffected by design.

---

## 5. Where the output goes

The demos write files into `docs/benchmark_results/`:

- `benchmark.json` / `benchmark.md` — the method-comparison table (Demo A).
- `<run-name>.json` / `<run-name>.md` — individual scorecards (Demos B and C).

The `.md` files are formatted scorecards, ready to paste into slides or the
report. `benchmark.md` is committed to the repo as a browsable copy of the
current result (viewable on GitHub without running anything); everything else
here regenerates on each run and is not tracked. See
[`docs/benchmark_results/README.md`](docs/benchmark_results/README.md).

---

## 6. If something goes wrong

| Symptom | Fix |
|---------|-----|
| `python: not recognized` (Windows) | Reopen the terminal, or use `py` instead of `python`. |
| `No module named compliance` / `faker` | The environment isn't active or dependencies aren't installed — redo section 2c. |
| PowerShell won't run `Activate.ps1` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then retry. |
| `pytest: command not found` | Use `python -m pytest -q` (with the leading `python -m`). |
