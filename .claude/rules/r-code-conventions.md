---
paths:
  - "**/*.R"
---

# R Code Standards

> **ARCHIVED — This project uses Python, not R.**
> This rule file is retained for reference in case R scripts are added later (e.g., exploratory data analysis, spatial visualization with ggplot2/sf).
>
> If R is reintroduced, restore this rule by removing this notice and updating the `paths:` frontmatter.

## If R Is Added Later

Apply these standards:
- `set.seed()` called once at top (YYYYMMDD format)
- All packages loaded via `library()` at top
- All paths relative to project root
- `snake_case` function names
- Roxygen-style documentation
- No hardcoded absolute paths
