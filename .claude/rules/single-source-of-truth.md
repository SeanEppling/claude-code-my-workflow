---
paths:
  - "data/**/*"
  - "src/**/*.py"
  - "reports/**/*"
---

# Single Source of Truth: Enforcement Protocol

**`data/wells.db` (SQLite) is the authoritative data store for ALL well data.** Everything else is derived.

## The SSOT Chain

```
data/raw/*.csv / *.xlsx   (import input — do not modify programmatically)
  │
  └── src/compiler/loader.py → data/wells.db  (SOURCE OF TRUTH)
                                    │
                                    ├── src/agent/   → conversational responses (derived)
                                    └── src/reports/ → reports/*.html / *.pdf  (derived)

NEVER edit derived artifacts independently.
ALWAYS propagate changes from source → derived.
```

## DB Integrity Rules

- `data/wells.db` must NEVER be edited by hand
- All data enters the DB through `src/compiler/loader.py` (ETL)
- Schema is defined exclusively in `src/compiler/schema.py`
- If data is wrong, fix the source file and re-run the loader — never patch the DB directly

## Data Fidelity Checklist

```
[ ] DB was not modified by hand
[ ] Schema in src/compiler/schema.py matches CLAUDE.md Data Schema Reference
[ ] All report values trace back to a query against data/wells.db
[ ] No hardcoded well data values in src/agent/ or src/reports/
[ ] ETL loader ran without errors after any import
```

## Schema Change Protocol

If the `wells` table schema changes (column added, renamed, removed):
1. Update `src/compiler/schema.py` Column definitions
2. Update `CLAUDE.md` Data Schema Reference table
3. Update `.claude/rules/knowledge-base-template.md` field reference
4. Re-run `python scripts/init_db.py` (will apply changes on a new DB)
5. Re-run ETL loader to repopulate
6. Update `src/reports/` template field references if affected
