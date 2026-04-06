"""
Query functions for the EOG Oil Well database.

All functions return plain Python dicts/lists for easy JSON serialization.
These are pure query functions — no MCP, no I/O side effects.

Usage:
    from src.compiler.query import get_wells_by_status, count_wells
    results = get_wells_by_status("producing")
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import func, text

from src.compiler.db import get_connection


def _row_to_dict(row) -> Dict[str, Any]:
    """Convert a SQLAlchemy Row to a plain dict, omitting None values."""
    return {k: v for k, v in row._mapping.items() if v is not None}


def get_wells_by_status(status: str) -> List[Dict]:
    """
    Return all wells matching the given status (case-insensitive).
    E.g. "producing", "PRODUCING", "Producing" all work.
    """
    with get_connection() as conn:
        rows = conn.execute(
            text("SELECT * FROM wells WHERE LOWER(status) = LOWER(:status) ORDER BY well_name"),
            {"status": status},
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_wells_by_county(county: str, state: Optional[str] = None) -> List[Dict]:
    """
    Return all wells in a county (case-insensitive partial match).
    Optionally filter by 2-letter state code.
    E.g. get_wells_by_county("Lea") or get_wells_by_county("lea", "NM")
    """
    with get_connection() as conn:
        if state:
            rows = conn.execute(
                text(
                    "SELECT * FROM wells "
                    "WHERE LOWER(county) LIKE LOWER(:county) "
                    "AND UPPER(state) = UPPER(:state) "
                    "ORDER BY well_name"
                ),
                {"county": f"%{county}%", "state": state},
            ).fetchall()
        else:
            rows = conn.execute(
                text(
                    "SELECT * FROM wells "
                    "WHERE LOWER(county) LIKE LOWER(:county) "
                    "ORDER BY state, well_name"
                ),
                {"county": f"%{county}%"},
            ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_wells_by_state(state: str) -> List[Dict]:
    """
    Return all wells in a state (2-letter abbreviation, case-insensitive).
    E.g. get_wells_by_state("TX")
    """
    with get_connection() as conn:
        rows = conn.execute(
            text(
                "SELECT * FROM wells WHERE UPPER(state) = UPPER(:state) "
                "ORDER BY county, well_name"
            ),
            {"state": state},
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_well_by_api(api_number: str) -> Optional[Dict]:
    """
    Look up a single well by its API number.
    Returns None if not found.
    """
    with get_connection() as conn:
        row = conn.execute(
            text("SELECT * FROM wells WHERE api_number = :api"),
            {"api": api_number},
        ).fetchone()
    return _row_to_dict(row) if row else None


def search_wells(name_fragment: str) -> List[Dict]:
    """
    Case-insensitive search on well_name.
    E.g. search_wells("WHISTLER") returns all WHISTLER wells.
    """
    with get_connection() as conn:
        rows = conn.execute(
            text(
                "SELECT * FROM wells WHERE LOWER(well_name) LIKE LOWER(:q) "
                "ORDER BY well_name"
            ),
            {"q": f"%{name_fragment}%"},
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def count_wells(group_by: Optional[str] = None, state: Optional[str] = None) -> Any:
    """
    Count wells, optionally grouped by a field and/or filtered by state.
    group_by options: None (total), "status", "state", "county"
    state: 2-letter abbreviation to filter before counting (e.g. "NM")
    Returns an int (total) or list of {"group": value, "count": n} dicts.
    """
    allowed = {"status", "state", "county"}
    where = "WHERE UPPER(state) = UPPER(:state)" if state else ""
    params = {"state": state} if state else {}
    with get_connection() as conn:
        if group_by is None:
            return conn.execute(
                text(f"SELECT COUNT(*) FROM wells {where}"), params
            ).scalar()
        if group_by not in allowed:
            raise ValueError(f"group_by must be one of {allowed}, got '{group_by}'")
        rows = conn.execute(
            text(
                f"SELECT {group_by}, COUNT(*) as count FROM wells {where} "
                f"GROUP BY {group_by} ORDER BY count DESC"
            ),
            params,
        ).fetchall()
    return [{"group": r[0], "count": r[1]} for r in rows]


def query_wells(
    state: Optional[str] = None,
    county: Optional[str] = None,
    status: Optional[str] = None,
    operator: Optional[str] = None,
    has_coordinates: Optional[bool] = None,
    limit: int = 200,
    offset: int = 0,
) -> Dict:
    """
    Flexible multi-filter well query. All filters are optional and combinable.

    - state: 2-letter abbreviation, exact match (case-insensitive)
    - county: partial match (case-insensitive)
    - status: exact match (case-insensitive); "active" matches both Active and Producing
    - operator: partial match (case-insensitive)
    - has_coordinates: True = only wells with lat/lon, False = only wells missing coords
    - limit/offset: pagination (default limit 200)

    Returns {"total": int, "returned": int, "wells": [...]}
    """
    conditions = []
    params: Dict[str, Any] = {"limit": limit, "offset": offset}

    if state:
        conditions.append("UPPER(state) = UPPER(:state)")
        params["state"] = state

    if county:
        conditions.append("LOWER(county) LIKE LOWER(:county)")
        params["county"] = f"%{county}%"

    if status:
        # "active" intent returns both Active and Producing wells
        if status.lower() == "active":
            conditions.append("(LOWER(status) = 'active' OR LOWER(status) = 'producing')")
        else:
            conditions.append("LOWER(status) = LOWER(:status)")
            params["status"] = status

    if operator:
        conditions.append("LOWER(operator) LIKE LOWER(:operator)")
        params["operator"] = f"%{operator}%"

    if has_coordinates is True:
        conditions.append("lat IS NOT NULL AND lon IS NOT NULL")
    elif has_coordinates is False:
        conditions.append("(lat IS NULL OR lon IS NULL)")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    with get_connection() as conn:
        total = conn.execute(
            text(f"SELECT COUNT(*) FROM wells {where}"), params
        ).scalar()
        rows = conn.execute(
            text(
                f"SELECT * FROM wells {where} "
                f"ORDER BY state, county, well_name "
                f"LIMIT :limit OFFSET :offset"
            ),
            params,
        ).fetchall()

    return {
        "total": total,
        "returned": len(rows),
        "offset": offset,
        "wells": [_row_to_dict(r) for r in rows],
    }


def data_quality() -> Dict:
    """
    Return a data completeness report: null counts per field, broken down by state.
    Helps identify which wells and states have incomplete records.
    """
    with get_connection() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM wells")).scalar()

        # Null counts per nullable field
        null_counts = {}
        for field in ("status", "operator", "lease_code", "lat", "lon", "api_number"):
            null_counts[field] = conn.execute(
                text(f"SELECT COUNT(*) FROM wells WHERE {field} IS NULL")
            ).scalar()

        # Per-state completeness
        states = conn.execute(
            text("SELECT state, COUNT(*) as total, "
                 "SUM(CASE WHEN lat IS NULL OR lon IS NULL THEN 1 ELSE 0 END) as missing_coords, "
                 "SUM(CASE WHEN operator IS NULL THEN 1 ELSE 0 END) as missing_operator, "
                 "SUM(CASE WHEN lease_code IS NULL THEN 1 ELSE 0 END) as missing_lease "
                 "FROM wells GROUP BY state ORDER BY total DESC")
        ).fetchall()

    return {
        "total_wells": total,
        "null_counts": null_counts,
        "by_state": [
            {
                "state": r[0],
                "total": r[1],
                "missing_coords": r[2],
                "missing_operator": r[3],
                "missing_lease": r[4],
            }
            for r in states
        ],
    }


def get_wells_by_operator(operator_fragment: str) -> List[Dict]:
    """
    Case-insensitive substring search on operator name.
    E.g. get_wells_by_operator("EOG") returns all EOG Resources wells.
    """
    with get_connection() as conn:
        rows = conn.execute(
            text(
                "SELECT * FROM wells WHERE LOWER(operator) LIKE LOWER(:q) "
                "ORDER BY state, county, well_name"
            ),
            {"q": f"%{operator_fragment}%"},
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_wells_by_lease(lease_code: str) -> List[Dict]:
    """
    Look up wells by lease code (exact match, case-insensitive).
    E.g. get_wells_by_lease("LC-7842")
    """
    with get_connection() as conn:
        rows = conn.execute(
            text(
                "SELECT * FROM wells WHERE LOWER(lease_code) = LOWER(:lease) "
                "ORDER BY well_name"
            ),
            {"lease": lease_code},
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def list_all_wells(limit: int = 100, offset: int = 0) -> List[Dict]:
    """
    Return wells paginated, ordered by state then well_name.
    Default limit is 100; use offset for pagination.
    """
    with get_connection() as conn:
        rows = conn.execute(
            text(
                "SELECT * FROM wells ORDER BY state, county, well_name "
                "LIMIT :limit OFFSET :offset"
            ),
            {"limit": limit, "offset": offset},
        ).fetchall()
    return [_row_to_dict(r) for r in rows]
