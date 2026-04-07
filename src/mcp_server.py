"""
MCP server for the EOG Oil Well Information Compiler.

Implements the Model Context Protocol (JSON-RPC 2.0 over stdio) without
the mcp SDK, so it works on Python 3.9+.

Claude Code registers this server via .claude/settings.json and can then
call these tools directly in conversation.

Tools exposed:
  - query_wells            (flexible multi-filter — use first)
  - query_wells_by_status
  - query_wells_by_county
  - query_wells_by_state
  - query_wells_by_operator
  - query_wells_by_lease
  - get_well_by_api
  - search_wells
  - count_wells            (now supports state filter)
  - data_quality
  - list_all_wells

Start manually to test:
    python3 src/mcp_server.py
(Will wait for JSON-RPC messages on stdin.)
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure project root on path when run directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.compiler.query import (
    count_wells,
    data_quality,
    get_well_by_api,
    get_wells_by_county,
    get_wells_by_lease,
    get_wells_by_operator,
    get_wells_by_state,
    get_wells_by_status,
    list_all_wells,
    query_wells,
    search_wells,
)
from src.visualizations import generate_map

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("well-mcp")

# ---------------------------------------------------------------------------
# Tool definitions — what Claude sees when deciding which tool to call
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "query_wells_by_status",
        "description": (
            "Return all oil wells with a given operational status. "
            "Common values: Producing, Active, New. Case-insensitive."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Status to filter by, e.g. 'Producing', 'Active', 'New'",
                }
            },
            "required": ["status"],
        },
    },
    {
        "name": "query_wells_by_county",
        "description": (
            "Return all oil wells in a given county. "
            "County name is matched case-insensitively. "
            "Optionally filter by 2-letter state code."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "county": {
                    "type": "string",
                    "description": "County name, e.g. 'Lea', 'Webb', 'Reeves'",
                },
                "state": {
                    "type": "string",
                    "description": "Optional 2-letter state abbreviation, e.g. 'TX', 'NM'",
                },
            },
            "required": ["county"],
        },
    },
    {
        "name": "query_wells_by_state",
        "description": (
            "Return all oil wells in a given US state. "
            "Use the 2-letter state abbreviation (TX, NM, ND, OH, etc.)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "2-letter state abbreviation, e.g. 'TX', 'NM', 'ND'",
                }
            },
            "required": ["state"],
        },
    },
    {
        "name": "get_well_by_api",
        "description": (
            "Look up a single well by its API number. "
            "Returns all fields for that well, or null if not found."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "api_number": {
                    "type": "string",
                    "description": "API number, e.g. '42-479-45324'",
                }
            },
            "required": ["api_number"],
        },
    },
    {
        "name": "search_wells",
        "description": (
            "Search for wells by name fragment. "
            "Case-insensitive substring match on well name. "
            "E.g. 'WHISTLER' returns all WHISTLER wells."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name_fragment": {
                    "type": "string",
                    "description": "Partial well name to search for",
                }
            },
            "required": ["name_fragment"],
        },
    },
    {
        "name": "query_wells_by_operator",
        "description": (
            "Search for wells by operator/company name. "
            "Case-insensitive substring match — 'EOG' matches 'EOG Resources Inc.' "
            "Returns all wells operated by matching companies."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "operator_fragment": {
                    "type": "string",
                    "description": "Partial operator name to search for, e.g. 'EOG', 'Pioneer'",
                }
            },
            "required": ["operator_fragment"],
        },
    },
    {
        "name": "query_wells_by_lease",
        "description": (
            "Look up all wells on a given lease code. "
            "Exact match (case-insensitive) on the lease_code field."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "lease_code": {
                    "type": "string",
                    "description": "Lease code to look up, e.g. 'LC-7842'",
                }
            },
            "required": ["lease_code"],
        },
    },
    {
        "name": "query_wells",
        "description": (
            "Flexible multi-filter well query — use this when the question combines "
            "more than one criterion (e.g. 'active wells in NM', 'EOG wells in Eddy County', "
            "'wells in Colorado with coordinates'). All filters are optional and combinable. "
            "'active' status automatically includes both Active and Producing wells. "
            "Returns total match count plus paginated results."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "2-letter state abbreviation, e.g. 'NM', 'TX'",
                },
                "county": {
                    "type": "string",
                    "description": "County name (partial match), e.g. 'Eddy', 'Lea'",
                },
                "status": {
                    "type": "string",
                    "description": "Status filter: 'active' (includes Producing), 'producing', 'new', etc.",
                },
                "operator": {
                    "type": "string",
                    "description": "Operator name fragment, e.g. 'EOG'",
                },
                "has_coordinates": {
                    "type": "boolean",
                    "description": "true = only wells with lat/lon, false = only wells missing coordinates",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default 200)",
                },
                "offset": {
                    "type": "integer",
                    "description": "Offset for pagination (default 0)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "count_wells",
        "description": (
            "Count wells in the database, optionally grouped by a field and/or filtered by state. "
            "With no arguments returns total count. "
            "group_by options: 'status', 'state', 'county'. "
            "Add state to count only within that state (e.g. counties in NM)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "group_by": {
                    "type": "string",
                    "description": "Optional field to group by: 'status', 'state', or 'county'",
                },
                "state": {
                    "type": "string",
                    "description": "Optional 2-letter state filter, e.g. 'NM'",
                },
            },
            "required": [],
        },
    },
    {
        "name": "data_quality",
        "description": (
            "Return a data completeness report: how many wells are missing coordinates, "
            "operator names, lease codes, or other fields — broken down by state. "
            "Use this to understand data gaps before analysis or reporting."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "generate_map",
        "description": (
            "Generate an interactive HTML map of wells matching optional filters. "
            "Opens in any browser — wells are color-coded by state with clickable popups "
            "showing name, API, county, status, operator, and lease code. "
            "Returns the file path of the generated map. "
            "Use this whenever the user asks for a map, visualization, or wants to see where wells are."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "Filter to a single state, e.g. 'NM', 'TX'",
                },
                "county": {
                    "type": "string",
                    "description": "Filter to a county (partial match), e.g. 'Eddy'",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by status: 'active' includes Producing, 'producing', 'new'",
                },
                "operator": {
                    "type": "string",
                    "description": "Filter by operator name fragment, e.g. 'EOG'",
                },
            },
            "required": [],
        },
    },
    {
        "name": "list_all_wells",
        "description": (
            "List all wells in the database, paginated. "
            "Default returns up to 100 wells ordered by state, county, name."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of wells to return (default 100)",
                },
                "offset": {
                    "type": "integer",
                    "description": "Number of wells to skip for pagination (default 0)",
                },
            },
            "required": [],
        },
    },
]

# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

def dispatch_tool(name: str, args: Dict[str, Any]) -> Any:
    """Call the appropriate query function and return the result."""
    if name == "query_wells_by_status":
        return get_wells_by_status(args["status"])
    elif name == "query_wells_by_county":
        return get_wells_by_county(args["county"], args.get("state"))
    elif name == "query_wells_by_state":
        return get_wells_by_state(args["state"])
    elif name == "get_well_by_api":
        return get_well_by_api(args["api_number"])
    elif name == "search_wells":
        return search_wells(args["name_fragment"])
    elif name == "query_wells_by_operator":
        return get_wells_by_operator(args["operator_fragment"])
    elif name == "query_wells_by_lease":
        return get_wells_by_lease(args["lease_code"])
    elif name == "query_wells":
        return query_wells(
            state=args.get("state"),
            county=args.get("county"),
            status=args.get("status"),
            operator=args.get("operator"),
            has_coordinates=args.get("has_coordinates"),
            limit=args.get("limit", 200),
            offset=args.get("offset", 0),
        )
    elif name == "count_wells":
        return count_wells(args.get("group_by"), args.get("state"))
    elif name == "data_quality":
        return data_quality()
    elif name == "generate_map":
        path = generate_map(
            state=args.get("state"),
            county=args.get("county"),
            status=args.get("status"),
            operator=args.get("operator"),
        )
        import subprocess
        subprocess.Popen(["open", path])
        return {"file": path, "message": f"Map generated and opened: {path}"}
    elif name == "list_all_wells":
        return list_all_wells(
            limit=args.get("limit", 100),
            offset=args.get("offset", 0),
        )
    else:
        raise ValueError(f"Unknown tool: {name}")


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 over stdio (MCP transport)
# ---------------------------------------------------------------------------

def send(msg: Dict) -> None:
    """Write a JSON-RPC message to stdout, followed by newline."""
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def handle(request: Dict) -> None:
    """Process a single JSON-RPC request and send a response."""
    req_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params", {})

    try:
        # MCP initialization handshake
        if method == "initialize":
            send({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "well-db",
                        "version": "1.0.0",
                    },
                },
            })

        elif method == "notifications/initialized":
            # Notification — no response needed
            pass

        elif method == "tools/list":
            send({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": TOOLS},
            })

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            result = dispatch_tool(tool_name, tool_args)
            send({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2),
                        }
                    ]
                },
            })

        elif method == "ping":
            send({"jsonrpc": "2.0", "id": req_id, "result": {}})

        else:
            # Unknown method
            if req_id is not None:
                send({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                })

    except Exception as exc:
        log.exception("Error handling %s", method)
        if req_id is not None:
            send({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": str(exc)},
            })


def main() -> None:
    log.warning("well-db MCP server starting (stdio transport)")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            log.error("JSON parse error: %s", exc)
            continue
        handle(request)


if __name__ == "__main__":
    main()
