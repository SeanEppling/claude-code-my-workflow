# Plan: Local SQLite Database Setup

**Status:** DRAFT
**Date:** 2026-04-04

---

## Context

The data source is being changed from CSV/Excel flat files to a local SQLite database. SQLite is embedded (no server), zero-config, and produces a single portable `.db` file — ideal for local development and demo purposes.

No data is available yet, so this session only sets up the schema and DB infrastructure. Data loading will happen in a future session once Sean provides real well data.

**User answers:** SQLite engine, schema-only (no data yet).

---

## Approach

### Step 1 — Add SQLAlchemy to requirements.txt

Add `sqlalchemy>=2.0.0` to `requirements.txt`. SQLAlchemy Core (not ORM) provides a clean SQL abstraction that's more robust than raw `sqlite3` while staying lightweight. It also positions the project to swap to PostgreSQL later with minimal code changes.

### Step 2 — Create `src/compiler/schema.py`

Define the `wells` table using SQLAlchemy `Table` / `Column` definitions. Based on the field reference in `.claude/rules/knowledge-base-template.md`:

| Column | SQLAlchemy Type | Constraints |
|--------|----------------|-------------|
| `id` | Integer | Primary key, autoincrement |
| `well_id` | String(50) | Unique, not null |
| `well_name` | String(200) | Not null |
| `status` | String(50) | Not null (Active/Inactive/Plugged/Drilling/Permit) |
| `county` | String(100) | Not null |
| `state` | String(2) | Not null |
| `lease_code` | String(100) | Nullable |
| `operator` | String(200) | Nullable |
| `api_number` | String(14) | Unique, nullable |
| `lat` | Float | Nullable |
| `lon` | Float | Nullable |

### Step 3 — Create `src/compiler/db.py`

Database connection management:
- `DB_PATH` constant pointing to `data/wells.db`
- `get_engine()` — creates/returns SQLAlchemy engine for the SQLite file
- `get_connection()` — context manager for a DB connection
- `init_db()` — creates all tables if they don't exist (idempotent)

### Step 4 — Create `scripts/init_db.py`

Standalone script to initialize the database:
```bash
python scripts/init_db.py
```
- Calls `init_db()` from `src/compiler/db.py`
- Prints confirmation: table names + column counts
- Idempotent (safe to re-run)

### Step 5 — Update configuration files

| File | Change |
|------|--------|
| `CLAUDE.md` | Update Commands section (add `init_db`), update Data Sources table (CSV → SQLite), update folder structure note |
| `.claude/rules/beamer-quarto-sync.md` (data-source-of-truth) | Reference DB instead of CSV/Excel as source of truth |
| `.claude/rules/single-source-of-truth.md` | Update: `data/wells.db` is authoritative; raw imports derive from external sources |
| `.claude/rules/verification-protocol.md` | Add DB verification step: check `data/wells.db` exists, tables present |
| `.claude/rules/knowledge-base-template.md` | Add SQL schema section with actual CREATE TABLE reference |

### Step 6 — Update `.gitignore`

Add `data/wells.db` to `.gitignore` (DB file should not be committed — it's a derived artifact that gets created via `init_db.py`).

---

## Files to Create

| Path | Purpose |
|------|---------|
| `src/compiler/schema.py` | SQLAlchemy table definitions |
| `src/compiler/db.py` | Connection management + `init_db()` |
| `scripts/init_db.py` | CLI script to create DB and tables |

## Files to Modify

| File | Change |
|------|--------|
| `requirements.txt` | Add `sqlalchemy>=2.0.0` |
| `CLAUDE.md` | Update commands and data source section |
| `.claude/rules/beamer-quarto-sync.md` | DB as source of truth |
| `.claude/rules/single-source-of-truth.md` | DB as source of truth |
| `.claude/rules/verification-protocol.md` | Add DB check step |
| `.claude/rules/knowledge-base-template.md` | Add SQL schema reference |
| `.gitignore` | Add `data/wells.db` |

---

## Verification

1. `python scripts/init_db.py` runs without error
2. `data/wells.db` is created
3. `python -c "from src.compiler.db import get_engine; e = get_engine(); print(list(e.dialect.get_table_names(e.connect())))"` lists the `wells` table
4. `python3 -c "import src"` still passes
5. `data/wells.db` appears in `.gitignore` check

---

## Out of Scope (Next Sessions)

- ETL/loader script to import CSV or Excel data into the DB
- Query functions (`src/compiler/query.py`)
- Agent integration
- Synthetic seed data
