---
paths:
  - "src/**/*.py"
  - "data/**/*"
  - "reports/**/*"
---

# Quality Gates & Scoring Rubrics

## Thresholds

- **80/100 = Commit** -- good enough to save
- **90/100 = PR** -- ready for deployment / interview demo
- **95/100 = Excellence** -- fully polished, production-ready

## Python Source Code (`src/**/*.py`)

| Severity | Issue | Deduction |
|----------|-------|-----------|
| Critical | Syntax error / import failure | -100 |
| Critical | Hardcoded absolute paths | -20 |
| Critical | Raw data file modified by code | -20 |
| Critical | Unhandled exception on valid input | -15 |
| Major | No input validation at data boundaries | -10 |
| Major | Missing docstring on public functions | -5 |
| Major | Unused imports | -3 |
| Minor | Lines > 100 chars (non-formula) | -1 per line |
| Minor | Magic numbers without comment | -2 |

## Data Quality (`data/**/*`)

| Severity | Issue | Deduction |
|----------|-------|-----------|
| Critical | Processed file is stale (older than raw) | -20 |
| Critical | Required field missing from schema | -15 |
| Critical | Duplicate well IDs in processed output | -15 |
| Major | Null values in required fields | -10 |
| Major | Schema mismatch between raw and CLAUDE.md | -5 |
| Minor | Inconsistent casing in categorical fields | -2 |

## Reports (`reports/**/*`)

| Severity | Issue | Deduction |
|----------|-------|-----------|
| Critical | Report fails to render | -100 |
| Critical | Data values don't match processed source | -20 |
| Major | Missing required sections (well ID, status, county) | -10 |
| Major | Broken links or missing images | -5 |
| Minor | Typo in report content | -2 |

## Enforcement

- **Score < 80:** Block commit. List blocking issues explicitly.
- **Score 80–89:** Allow commit, warn. List recommendations.
- **Score >= 90:** Approve for PR / demo.
- User can override with explicit justification.

## Quality Reports

Generated **only at merge time**. Use `templates/quality-report.md` for format.
Save to `quality_reports/merges/YYYY-MM-DD_[branch-name].md`.
