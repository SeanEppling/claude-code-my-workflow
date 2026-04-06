---
paths:
  - "src/**/*.py"
  - "data/**/*"
  - "reports/**/*"
---

# Project Knowledge Base: EOG Oil Well Information Compiler

<!-- Claude reads this before modifying any source code or data pipeline.
     Update these tables as the actual data schema is confirmed. -->

## Well Data Field Reference

| Field | Type | Description | Example | Notes |
|-------|------|-------------|---------|-------|
| `well_id` | string | Unique well identifier | `42-501-20130` | State-county-sequence format |
| `well_name` | string | Human-readable name | `JOHNSON 1H` | `H` suffix = horizontal well |
| `status` | string | Operational status | `Active` | See Status Codes below |
| `county` | string | County name | `Karnes` | Title case, no "County" suffix |
| `state` | string | State abbreviation | `TX` | 2-letter uppercase |
| `lease_code` | string | EOG lease identifier | `LC-7842` | Format TBD from source data |
| `operator` | string | Operating company | `EOG Resources` | May vary (EOG Resources, Inc.) |
| `api_number` | string | 14-digit API number | `42-501-20130-0000` | Industry standard identifier |
| `lat` | float | Latitude WGS84 | `28.8423` | Decimal degrees |
| `lon` | float | Longitude WGS84 | `-97.8801` | Decimal degrees, negative = West |

*Update this table once actual raw CSV/Excel headers are confirmed.*

## Status Code Registry

| Code | Meaning | Query Alias |
|------|---------|-------------|
| `Active` | Currently producing | `active`, `producing` |
| `Inactive` | Not producing, not plugged | `inactive`, `shut in` |
| `Plugged` | Permanently abandoned | `plugged`, `abandoned` |
| `Drilling` | Being drilled | `drilling`, `in progress` |
| `Permit` | Permitted, not yet drilled | `permit`, `planned` |

*Confirm actual status values from raw data.*

## Geographic Conventions

| Convention | Rule | Example |
|------------|------|---------|
| County names | Title case, no "County" | `Karnes` not `KARNES COUNTY` |
| State | 2-letter abbreviation | `TX`, `ND`, `CO` |
| Coordinates | Decimal degrees, WGS84 | lat `28.84`, lon `-97.88` |
| Basin names | Title case | `Eagle Ford`, `Permian Basin` |

## Key EOG Operating Basins (Reference)

| Basin | States | Primary Formation |
|-------|--------|-----------------|
| Eagle Ford | TX | Eagle Ford Shale |
| Permian Basin | TX, NM | Wolfcamp, Spraberry |
| DJ Basin | CO, WY | Niobrara |
| Bakken | ND, MT | Bakken, Three Forks |
| Dorado | TX | Austin Chalk (gas) |

## Database Schema (SQLAlchemy)

Defined in `src/compiler/schema.py`. Reference this before writing any query or loader code.

```python
wells = Table("wells", metadata,
    Column("id",          Integer,     primary_key=True),
    Column("well_id",     String(50),  unique=True, nullable=False),
    Column("api_number",  String(14),  unique=True, nullable=True),
    Column("lease_code",  String(100), nullable=True),
    Column("well_name",   String(200), nullable=False),
    Column("operator",    String(200), nullable=True),
    Column("status",      String(50),  nullable=False),
    Column("county",      String(100), nullable=False),
    Column("state",       String(2),   nullable=False),
    Column("lat",         Float,       nullable=True),
    Column("lon",         Float,       nullable=True),
)
```

## Python Code Conventions (This Project)

| Rule | Convention | Anti-Pattern |
|------|-----------|-------------|
| Paths | `pathlib.Path` always | `os.path.join()`, hardcoded strings |
| DataFrames | `pandas` with explicit dtypes | Implicit type inference for IDs |
| Field names | `snake_case` matching raw CSV headers | Camel case, spaces |
| Null handling | Explicit `pd.isna()` checks | Assuming fields are populated |
| Column access | `df["column"]` | `df.column` (fragile with spaces) |

## Common Pitfalls

| Pitfall | Impact | Prevention |
|---------|--------|------------|
| API number format inconsistency | Duplicate wells in output | Normalize to 14-digit on load |
| Status value casing varies | Missed wells in filter | Normalize to Title Case on load |
| County name includes "County" | Query mismatches | Strip "County" suffix on load |
| Coordinates outside TX/US | Bad data in source | Validate lat/lon bounds on load |
| Lease code format varies | Join failures | Standardize prefix/format on load |

## Agent Query Patterns

| User Intent | Query Type | Example |
|------------|-----------|---------|
| Status lookup | Filter by status field | "Which wells are active?" |
| Geographic lookup | Filter by county/state | "Wells in Karnes County" |
| Identifier lookup | Filter by well_id / api_number | "Details on well 42-501-20130" |
| Lease query | Filter by lease_code | "Wells on lease LC-7842" |
| Count/summary | Aggregation | "How many active wells in TX?" |
