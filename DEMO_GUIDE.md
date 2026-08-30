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

There are **three demo programs**. Each prints a scorecard and saves report files.

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

The output also shows: a couple of sample (fake) patient records, a per-task
score table, what each task actually needs, and **what each method pulled** —
e.g. the baseline grabs *60 records across 4 layers* including billing and
contact details it was never asked for, versus *30 records across 2 layers* for
the compliance-aware method.

**This is the main thing to show** — the core argument: compliance is a number
that separates good methods from bad ones.

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

1. **The one-page explanation.** Open
   [`docs/compliance/approach.md`](docs/compliance/approach.md). Read out the
   "The claim" section — that compliance becomes a *measured number*, produced by
   the same tool for any scraping method.

2. **Run Demo A live:** `python scripts/run_benchmark.py`. Point at the
   comparison table — our method 1.00, the coverage-optimised baseline 0.13, on
   the same seven rules. This is the core result.

3. **Run Demo B** if asked why a score moves:
   `python scripts/run_synthetic_extraction.py` — same method, three
   configurations, each rule failing with a stated reason.

4. **Show a saved artifact.** Open `docs/benchmark_results/benchmark.md` — the
   comparison table as a file. This is the evidence the research paper is built on.

5. **Run the tests:** `python -m pytest -q` → `91 passed`. Shows the work is
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
