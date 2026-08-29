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
score** — a number from 0 to 1, plus a pass/fail on four separate rules — so
different scraping methods can be compared on how lawful they are, not just on
how fast they run.

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

There are **two demo programs**. Both print a scorecard and save report files.

### Demo A — the rules on their own

```
python scripts/score_extraction_run.py
```

This has three make-believe scraping jobs written into it and scores each one:

| Job | Meaning | Score you'll see |
|-----|---------|------------------|
| `compliant` | did everything by the book | **1.000** |
| `partial`  | took only the data it needed, but skipped paperwork and some security | **~0.625** |
| `careless` | grabbed everything, documented nothing | **~0.188** |

For each job it prints every rule, whether it passed, and a plain-English reason
(e.g. *"Out-of-scope category extracted: financial"*).

### Demo B — the full pipeline on fake hospital data

```
python scripts/run_synthetic_extraction.py
```

Same three-way spread, but this time the records are not hand-written — the
program:

1. generates fake patient records for four areas of a hospital system,
2. "extracts" a selection of fields from them (a careful selection, a careful
   selection with sloppy paperwork, and a grab-everything selection),
3. scores each one.

Expected: **1.000 / ~0.625 / ~0.229**.

### The test suite (optional but reassuring)

```
python -m pytest -q
```

Runs every automated check on the code. You should see **`54 passed`**. This
confirms the rules, the fake-data generator, and the extraction step all behave
as intended.

---

## 4. What to show the reviewers

A five-minute walkthrough. Have a terminal open in the project folder with the
environment activated.

1. **The one-page explanation.** Open
   [`docs/compliance/approach.md`](docs/compliance/approach.md). Read out the
   "The claim" section — that compliance becomes a *measured number*, produced by
   the same tool for any scraping method.

2. **Run Demo B live:** `python scripts/run_synthetic_extraction.py`. Point at
   the three scores at the bottom (1.00 / 0.63 / 0.23). Note that the "careless"
   job fails each rule with a specific stated reason.

3. **Show a saved artifact.** Open
   `docs/benchmark_results/synthetic-careless.md` — a clean scorecard table.
   This is the kind of evidence file the research paper will be built on.

4. **Run the tests:** `python -m pytest -q` → `54 passed`. Shows the work is
   real, checked code, not slideware.

**Three points to make while doing this:**

- Compliance is **measured, not asserted** — the score comes out of rules, each
  tied to a DPDP Act 2023 principle.
- The **same scorer** will later grade an off-the-shelf scraping method
  (AutoScraper) through the exact same rules. That side-by-side comparison is the
  core of the paper.
- It **works today with zero hospital access**. When real access arrives, the
  data source is swapped by one configuration change — the rest of the pipeline
  is unaffected by design.

---

## 5. Where the output goes

Both demos write files into `docs/benchmark_results/`:

- `<run-name>.json` — machine-readable, for later analysis and comparison.
- `<run-name>.md` — a formatted scorecard, ready to paste into slides or the
  report.

These files are regenerated every time you run a demo, and are intentionally
excluded from version control.

---

## 6. If something goes wrong

| Symptom | Fix |
|---------|-----|
| `python: not recognized` (Windows) | Reopen the terminal, or use `py` instead of `python`. |
| `No module named compliance` / `faker` | The environment isn't active or dependencies aren't installed — redo section 2c. |
| PowerShell won't run `Activate.ps1` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then retry. |
| `pytest: command not found` | Use `python -m pytest -q` (with the leading `python -m`). |
