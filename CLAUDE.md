# CLAUDE.md -- EOG Oil Well Information Compiler

**Project:** EOG Oil Well Information Compiler
**Owner:** Sean
**Branch:** main

---

## Core Principles

- **Plan first** -- enter plan mode before non-trivial tasks; save plans to `quality_reports/plans/`
- **Verify after** -- run tests and confirm output at the end of every task
- **Single source of truth** -- `data/wells.db` (SQLite) is the authoritative data store; all query and report outputs derive from it
- **Quality gates** -- nothing ships below 80/100
- **[LEARN] tags** -- when corrected, save `[LEARN:category] wrong → right` to MEMORY.md

---

## Project Purpose

An agentic AI tool that compiles and presents data about EOG Resources oil wells. Users can ask natural-language questions — which wells are active, which are in a given county, what are the lease codes for a given well — and receive structured answers or exportable reports. Built as both a functional tool and an interview demonstration of agentic AI design.

---

## Folder Structure

```
my-project/
├── CLAUDE.md                    # This file
├── .claude/                     # Rules, skills, agents, hooks
├── data/
│   ├── wells.db                 # SQLite database (authoritative data store)
│   ├── raw/                     # Source CSV/Excel imports (input to ETL)
│   └── processed/               # Intermediate outputs (if needed)
├── src/
│   ├── agent/                   # Conversational AI agent (Claude API)
│   ├── compiler/                # Core data compilation + query logic
│   └── reports/                 # Report generation (PDF/HTML)
├── reports/                     # Generated output reports
├── notebooks/                   # Jupyter exploration notebooks
├── scripts/                     # Utility scripts
├── requirements.txt             # Python dependencies
├── quality_reports/             # Plans, session logs, merge reports
├── explorations/                # Research sandbox
└── templates/                   # Session log, quality report templates
```

---

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Verify package structure
python -c "import src; print('OK')"

# Run tests
python -m pytest tests/ -v

# Initialize database (run once, or after schema changes)
python scripts/init_db.py

# Load data from CSV/Excel into the database
python -m src.compiler.loader data/raw/yourfile.csv

# Run agent (interactive)
python -m src.agent.main

# Generate report
python -m src.reports.generate --output reports/ --format html

# Quality score
python scripts/quality_score.py src/
```

---

## Quality Thresholds

| Score | Gate | Meaning |
|-------|------|---------|
| 80 | Commit | Good enough to save |
| 90 | PR | Ready for deployment / demo |
| 95 | Excellence | Interview-ready polish |

---

## Skills Quick Reference

| Command | What It Does |
|---------|-------------|
| `/proofread [file]` | Grammar/typo review |
| `/review-r [file]` | Code quality review (use for Python too) |
| `/commit [msg]` | Stage, commit, PR, merge |
| `/lit-review [topic]` | Literature/industry search + synthesis |
| `/research-ideation [topic]` | Generate feature ideas + strategies |
| `/interview-me [topic]` | Interactive interview to formalize a feature spec |
| `/data-analysis [dataset]` | End-to-end analysis with publication-ready output |
| `/learn [skill-name]` | Extract discovery into persistent skill |
| `/context-status` | Show session health + context usage |
| `/deep-audit` | Repository-wide consistency audit |

---

## Data Schema Reference

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `well_id` | string | Unique well identifier | `42-501-20130` |
| `well_name` | string | Human-readable well name | `JOHNSON 1H` |
| `status` | string | Active / Inactive / Plugged / Drilling | `Active` |
| `county` | string | County name | `Karnes` |
| `state` | string | State abbreviation | `TX` |
| `lease_code` | string | EOG lease identifier | `LC-7842` |
| `operator` | string | Operating company | `EOG Resources` |
| `api_number` | string | 14-digit API well number | `42-501-20130-0000` |
| `lat` | float | Latitude (WGS84) | `28.8423` |
| `lon` | float | Longitude (WGS84) | `-97.8801` |

*Update this table as actual data schema is confirmed from source files.*

---

## Modules

| Module | Path | Status | Description |
|--------|------|--------|-------------|
| Schema | `src/compiler/schema.py` | Done | SQLAlchemy `wells` table definition |
| DB Manager | `src/compiler/db.py` | Done | Connection manager + `init_db()` |
| ETL Loader | `src/compiler/loader.py` | Planned | Import CSV/Excel into `wells` table |
| Query Engine | `src/compiler/query.py` | Planned | Filter/search logic against DB |
| AI Agent | `src/agent/main.py` | Planned | Conversational interface via Claude API |
| Report Generator | `src/reports/generate.py` | Planned | Output HTML/PDF well reports |

---

## Data Sources

| Source | Path | Format | Description |
|--------|------|--------|-------------|
| Database | `data/wells.db` | SQLite | Authoritative data store (created by `init_db.py`) |
| Raw imports | `data/raw/` | CSV/Excel | Input files for ETL — do not modify programmatically |
