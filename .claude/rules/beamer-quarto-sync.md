---
paths:
  - "data/**/*"
  - "src/**/*.py"
---

# Data Source of Truth: Sync Rule (MANDATORY)

**`data/wells.db` (SQLite) is the authoritative data store. All query results and reports derive from it. Never hand-edit the database or bypass the schema.**

## The Rule

When the schema or the data in `wells.db` changes, ALL downstream outputs that depend on it MUST be regenerated in the same task before reporting completion. Do NOT wait to be asked.

## Data Flow

```
data/raw/*.csv / *.xlsx     (external import input — do not modify programmatically)
        │
        ▼
src/compiler/loader.py      (ETL: normalize + insert into DB)
        │
        ▼
data/wells.db               (SOURCE OF TRUTH — SQLite)
        │
        ├── src/agent/      → conversational responses (derived)
        └── src/reports/    → reports/*.html / *.pdf (derived)
```

## Workflow (Every Time DB Schema or Data Changes)

1. Schema change → update `src/compiler/schema.py`, re-run `python scripts/init_db.py`
2. Data change → re-run the ETL loader against the source file
3. Regenerate any affected reports
4. Only then report task complete

## When NOT to Re-Run

- Compiler logic change only (no schema/data change) — re-run tests instead
- Documentation-only change
- Explicitly told to skip

## Enforcement

Before marking any data-related task complete, ask:
> "Is `data/wells.db` up to date with this change, and are all downstream outputs regenerated?"

If no, **you are NOT done.**
