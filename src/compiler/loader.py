"""
ETL loader: imports well data from a CSV file into data/wells.db.

Supports two CSV formats automatically detected by column presence:

Format A (wells_starter.csv):
  Columns: API #, Well Name, Status, County (with embedded state e.g. "Webb County, TX"),
           Latitude, Longitude
  - County field "Webb County, TX" → county="Webb", state="TX"

Format B (wells_eog_400.csv and similar):
  Columns: API #, Well Name, Lease No, Operator Name, County, State, Latitude,
           Longitude, Longitude (duplicate header → Longitude.1)
  - County field "Butte County" or "Sabine Parish" (no embedded state)
  - State in separate column
  - When Latitude is blank: Longitude col holds lat, Longitude.1 holds lon

Normalizations applied (both formats):
  - County stripped of " County" / " Parish" suffix → plain name
  - Status normalized to Title Case; blank → None
  - Lat/Lon of 0.0 or NaN treated as missing → None
  - API # used as both api_number and well_id
  - Duplicate API numbers are skipped (INSERT OR IGNORE)

Usage:
    python -m src.compiler.loader data/raw/wells_starter.csv
    python -m src.compiler.loader data/raw/wells_eog_400.csv --dry-run
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
from sqlalchemy import text

from src.compiler.db import get_connection, init_db
from src.compiler.schema import wells


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _parse_county_state(raw: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse "Webb County, TX" → ("Webb", "TX").
    Strips the " County" or " Parish" suffix and extracts the 2-letter state code.
    Returns (raw.strip(), None) if no embedded state found.
    Returns (None, None) if input is blank.
    """
    if not isinstance(raw, str) or not raw.strip():
        return None, None
    parts = raw.strip().split(",")
    if len(parts) == 2:
        county_part = parts[0].strip()
        state_part = parts[1].strip()
    else:
        county_part = raw.strip()
        state_part = None
    # Strip " County" or " Parish" suffix (case-insensitive)
    for suffix in (" county", " parish"):
        if county_part.lower().endswith(suffix):
            county_part = county_part[: -len(suffix)].strip()
            break
    return county_part or None, state_part


def _strip_county_suffix(raw: str) -> Optional[str]:
    """
    Strip " County" or " Parish" suffix from a standalone county field.
    E.g. "Butte County" → "Butte", "Sabine Parish" → "Sabine".
    Returns None if blank.
    """
    if not isinstance(raw, str) or not raw.strip():
        return None
    county = raw.strip()
    for suffix in (" county", " parish"):
        if county.lower().endswith(suffix):
            county = county[: -len(suffix)].strip()
            break
    return county or None


def _normalize_status(raw) -> Optional[str]:
    """Title-case the status; treat blank/NaN as None."""
    if pd.isna(raw) or str(raw).strip() == "":
        return None
    return str(raw).strip().title()


def _normalize_coord(val) -> Optional[float]:
    """Treat 0.0 or NaN as None (missing coordinates)."""
    if pd.isna(val):
        return None
    try:
        f = float(val)
    except (ValueError, TypeError):
        return None
    return None if f == 0.0 else f


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def _is_format_b(df: pd.DataFrame) -> bool:
    """
    Return True if the DataFrame matches Format B:
    has a separate 'State' column and a duplicate 'Longitude' header
    (pandas auto-renames to 'Longitude.1').
    """
    return "State" in df.columns and "Longitude.1" in df.columns


# ---------------------------------------------------------------------------
# Row builders — one per format
# ---------------------------------------------------------------------------

def _build_row_format_a(row: pd.Series) -> Optional[dict]:
    """
    Build an insert dict from a Format A row.
    County field contains embedded state: "Webb County, TX".
    """
    api = str(row.get("API #", "")).strip()
    if not api:
        return None

    county, state = _parse_county_state(str(row.get("County", "")))

    lat = _normalize_coord(row.get("Latitude"))
    lon = _normalize_coord(row.get("Longitude"))

    return {
        "well_id":    api,
        "api_number": api,
        "well_name":  str(row.get("Well Name", "")).strip() or None,
        "status":     _normalize_status(row.get("Status")),
        "lease_code": None,
        "operator":   None,
        "county":     county,
        "state":      state,
        "lat":        lat,
        "lon":        lon,
    }


def _build_row_format_b(row: pd.Series) -> Optional[dict]:
    """
    Build an insert dict from a Format B row.
    County and State are separate columns.
    When Latitude is blank: Longitude holds lat, Longitude.1 holds lon.
    """
    api = str(row.get("API #", "")).strip()
    if not api:
        return None

    county = _strip_county_suffix(str(row.get("County", "")))
    state = str(row.get("State", "")).strip().upper() or None

    # Coordinate logic: if Latitude is blank, Longitude col = lat, Longitude.1 = lon
    raw_lat = row.get("Latitude")
    raw_lon = row.get("Longitude")
    raw_lon1 = row.get("Longitude.1")

    if pd.isna(raw_lat) or str(raw_lat).strip() == "":
        lat = _normalize_coord(raw_lon)
        lon = _normalize_coord(raw_lon1)
    else:
        lat = _normalize_coord(raw_lat)
        lon = _normalize_coord(raw_lon)

    lease_raw = str(row.get("Lease No", "")).strip()
    operator_raw = str(row.get("Operator Name", "")).strip()

    return {
        "well_id":    api,
        "api_number": api,
        "well_name":  str(row.get("Well Name", "")).strip() or None,
        "status":     _normalize_status(row.get("Status", "")),
        "lease_code": lease_raw if lease_raw and lease_raw.lower() != "nan" else None,
        "operator":   operator_raw if operator_raw and operator_raw.lower() != "nan" else None,
        "county":     county,
        "state":      state,
        "lat":        lat,
        "lon":        lon,
    }


# ---------------------------------------------------------------------------
# Core ETL
# ---------------------------------------------------------------------------

def load_csv(filepath: Path, dry_run: bool = False) -> dict:
    """
    Load a CSV of well data into data/wells.db.

    Automatically detects Format A (embedded county+state) vs Format B
    (separate State column, shifted lat/lon columns).

    Returns a summary dict with inserted, skipped, and error counts.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Source file not found: {filepath}")

    df = pd.read_csv(filepath, dtype=str)  # read all as str to avoid silent coercions

    format_b = _is_format_b(df)
    fmt_label = "B (separate state + dual-lon)" if format_b else "A (embedded county/state)"
    print(f"Detected format: {fmt_label}")

    inserted = 0
    skipped = 0
    errors = []

    init_db()

    rows = []
    for _, row in df.iterrows():
        try:
            if format_b:
                record = _build_row_format_b(row)
            else:
                record = _build_row_format_a(row)
        except Exception as exc:
            errors.append(f"Row parse error: {exc} — {row.get('API #', '?')}")
            continue

        if record is None:
            errors.append(f"Row missing API #: {row.to_dict()}")
            continue

        rows.append(record)

    if dry_run:
        print(f"[dry-run] Would attempt to insert {len(rows)} rows.")
        for r in rows[:20]:
            print(f"  {r['api_number']:20s}  {(r['well_name'] or ''):40s}  "
                  f"{r['status'] or 'None':12s}  {r['county']}, {r['state']}")
        if len(rows) > 20:
            print(f"  ... ({len(rows) - 20} more rows not shown)")
        return {"inserted": 0, "skipped": 0, "errors": errors, "dry_run": True}

    with get_connection() as conn:
        for record in rows:
            try:
                result = conn.execute(
                    text(
                        "INSERT OR IGNORE INTO wells "
                        "(well_id, api_number, well_name, status, county, state, "
                        " lat, lon, lease_code, operator) "
                        "VALUES (:well_id, :api_number, :well_name, :status, :county, :state, "
                        "        :lat, :lon, :lease_code, :operator)"
                    ),
                    record,
                )
                if result.rowcount == 1:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as exc:
                errors.append(f"{record['api_number']}: {exc}")
        conn.commit()

    return {"inserted": inserted, "skipped": skipped, "errors": errors}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Load well data CSV into data/wells.db")
    parser.add_argument("filepath", help="Path to the source CSV file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print rows that would be inserted without writing to DB")
    args = parser.parse_args()

    summary = load_csv(args.filepath, dry_run=args.dry_run)

    print(f"\nLoad complete:")
    print(f"  Inserted : {summary['inserted']}")
    print(f"  Skipped  : {summary['skipped']} (duplicate API # or already in DB)")
    if summary["errors"]:
        print(f"  Errors   : {len(summary['errors'])}")
        for e in summary["errors"]:
            print(f"    {e}")
    else:
        print(f"  Errors   : 0")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    main()
