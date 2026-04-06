---
paths:
  - "src/**/*.py"
  - "data/**/*"
  - "reports/**/*"
---

# Task Completion Verification Protocol

**At the end of EVERY task, Claude MUST verify the output works correctly.** This is non-negotiable.

## For Python Source Code Changes

1. Verify the package imports cleanly: `python3 -c "import src"`
2. Run tests if they exist: `python -m pytest tests/ -v`
3. Confirm no syntax errors in modified files
4. Spot-check the output of any changed function with a simple call

## For Database / Schema Changes (`src/compiler/schema.py`, `src/compiler/db.py`)

```bash
# Re-initialize the database
python scripts/init_db.py

# Verify the wells table exists and has correct columns
python3 -c "
from src.compiler.db import get_engine
from sqlalchemy import inspect
eng = get_engine()
cols = [c['name'] for c in inspect(eng).get_columns('wells')]
print('Columns:', cols)
"
```

- Verify `data/wells.db` was created (exists, size > 0)
- Verify `wells` table is present with all expected columns
- Confirm `data/raw/` was NOT modified: `git diff data/raw/`

## For ETL Loader Changes (`src/compiler/loader.py`)

```bash
python -m src.compiler.loader data/raw/yourfile.csv 2>&1
```

- Verify row count in DB after load is reasonable
- Spot-check: key fields (well_id, status, county) are non-null
- Confirm source file was NOT modified

## For Agent Changes (`src/agent/`)

1. Run a smoke test: `python -m src.agent.main --query "list active wells"`
2. Verify the response is structured (not an error or empty)
3. Confirm the agent queries `data/wells.db`, not hardcoded values

## For Report Changes (`src/reports/`)

1. Generate a test report: `python -m src.reports.generate --output reports/ --format html`
2. Verify the output file exists and is non-empty
3. Open the report: `open reports/*.html`
4. Spot-check that data values match the DB

## Verification Checklist

```
[ ] No import errors or syntax failures
[ ] Tests pass (or no tests exist yet — note this)
[ ] data/wells.db exists and wells table is present
[ ] Raw data in data/raw/ untouched
[ ] Output files created with expected content
[ ] Reported results to user with file paths
```

## Common Pitfalls

- **Stale DB:** Schema changed but `init_db.py` not re-run → re-run it
- **Hardcoded paths:** Use `pathlib.Path` and relative paths from project root
- **Silent failures:** Check return values and file sizes, don't assume success
- **Schema drift:** Column names in code diverge from `src/compiler/schema.py` → always reference schema.py
