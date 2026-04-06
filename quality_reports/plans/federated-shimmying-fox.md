# Plan: MCP Tool Server — Well Database Query Tools

**Status:** DRAFT
**Date:** 2026-04-04

---

## Context

Sean wants query tools that I (Claude Code) can call directly during our conversations when he asks questions about the database — "which wells are active?", "what's in Lea County?", etc. 

The correct mechanism for this is an **MCP (Model Context Protocol) server**: a local Python process that exposes query functions as tools. Once registered in Claude Code's settings, these tools appear in my toolset and I can call them like any other tool — getting real data from `data/wells.db` in real time, without needing a Bash call.

**Existing code to build on:**
- `src/compiler/db.py` — `get_connection()` context manager, `DB_PATH`
- `src/compiler/schema.py` — `wells` table with 11 columns
- `data/wells.db` — 50 wells loaded and verified

---

## Approach

### Step 1 — Install MCP SDK

Add `mcp>=1.0.0` to `requirements.txt`. The `mcp` package is Anthropic's official Python SDK for building MCP servers.

### Step 2 — Create `src/compiler/query.py`

Pure query functions (no MCP, no I/O) that the MCP server will call. Clean separation so these can also be used by the agent later.

Functions to implement:

| Function | Description |
|----------|-------------|
| `get_wells_by_status(status)` | Filter by status (case-insensitive) |
| `get_wells_by_county(county, state=None)` | Filter by county name (partial match ok), optionally by state |
| `get_wells_by_state(state)` | All wells in a given state |
| `get_well_by_api(api_number)` | Single well lookup by API # |
| `search_wells(name_fragment)` | Case-insensitive LIKE search on well_name |
| `count_wells(group_by=None)` | Total count, or grouped by "status" / "state" / "county" |
| `list_all_wells(limit=100)` | Paginated full table dump |

All functions return plain Python dicts/lists — easy to serialize to JSON for MCP.

### Step 3 — Create `src/mcp_server.py`

An MCP server using the `mcp` SDK (`FastMCP` pattern) that wraps each query function as a registered tool with:
- A clear name (e.g., `query_wells_by_status`)
- A description Claude will use to decide when to call it
- Typed parameters with descriptions

The server runs via stdio (standard MCP transport), started as a subprocess by Claude Code.

### Step 4 — Register the MCP server in Claude Code settings

Add an entry to `.claude/settings.json` (or create it) under `mcpServers`:

```json
{
  "mcpServers": {
    "well-db": {
      "command": "python3",
      "args": ["src/mcp_server.py"],
      "cwd": "/Users/sean/Desktop/my-project"
    }
  }
}
```

This makes the tools available in every Claude Code session in this project automatically.

### Step 5 — Update `requirements.txt` and verify

Add `mcp>=1.0.0`. Verify the server starts cleanly and tools are visible.

---

## Files to Create

| Path | Purpose |
|------|---------|
| `src/compiler/query.py` | Pure query functions against `data/wells.db` |
| `src/mcp_server.py` | MCP server exposing query functions as tools |

## Files to Modify

| File | Change |
|------|--------|
| `requirements.txt` | Add `mcp>=1.0.0` |
| `.claude/settings.json` | Register `well-db` MCP server |

---

## Tools Sean will be able to trigger by asking me

| Tool | Example trigger |
|------|----------------|
| `query_wells_by_status` | "Which wells are producing?" |
| `query_wells_by_county` | "What wells are in Lea County?" |
| `query_wells_by_state` | "Show me all Texas wells" |
| `get_well_by_api` | "Look up API 42-479-45324" |
| `search_wells` | "Find wells with WHISTLER in the name" |
| `count_wells` | "How many wells do we have by state?" |
| `list_all_wells` | "List all wells" |

---

## Verification

1. `pip3 install mcp` succeeds
2. `python3 src/mcp_server.py` starts without error (will wait for stdio input)
3. `.claude/settings.json` has the `well-db` entry
4. In a new Claude Code session, tools appear: I can call `query_wells_by_status(status="Producing")` and get back the 15 producing wells
