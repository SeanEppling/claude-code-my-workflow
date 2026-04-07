"""
Visualization generators for EOG well data.

Each function writes a self-contained HTML file to the reports/ directory
and returns the absolute path to the file.

All Leaflet assets are loaded from unpkg CDN (requires internet).
Tile layer uses OpenStreetMap (reliable, no API key needed).

Public API:
    generate_map(state, county, status, operator, output_path) -> str
"""

import json
import re
from pathlib import Path
from typing import Optional

from sqlalchemy import text

from src.compiler.db import get_connection

REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"

# One color per state
STATE_COLORS = {
    "TX": "#e63946",
    "NM": "#f4a261",
    "CO": "#2a9d8f",
    "MS": "#457b9d",
    "CA": "#8338ec",
    "KS": "#fb8500",
    "LA": "#06d6a0",
    "ND": "#ef476f",
    "OH": "#118ab2",
}
DEFAULT_COLOR = "#aaaaaa"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_wells_for_map(
    state: Optional[str] = None,
    county: Optional[str] = None,
    status: Optional[str] = None,
    operator: Optional[str] = None,
) -> list:
    conditions = ["lat IS NOT NULL", "lon IS NOT NULL"]
    params: dict = {}

    if state:
        conditions.append("UPPER(state) = UPPER(:state)")
        params["state"] = state
    if county:
        conditions.append("LOWER(county) LIKE LOWER(:county)")
        params["county"] = f"%{county}%"
    if status:
        if status.lower() == "active":
            conditions.append("(LOWER(status) = 'active' OR LOWER(status) = 'producing')")
        else:
            conditions.append("LOWER(status) = LOWER(:status)")
            params["status"] = status
    if operator:
        conditions.append("LOWER(operator) LIKE LOWER(:operator)")
        params["operator"] = f"%{operator}%"

    where = "WHERE " + " AND ".join(conditions)
    with get_connection() as conn:
        rows = conn.execute(
            text(f"SELECT well_name, api_number, county, state, status, operator, lease_code, lat, lon "
                 f"FROM wells {where} ORDER BY state, well_name"),
            params,
        ).fetchall()
    return [dict(r._mapping) for r in rows]


def _safe_str(val) -> str:
    """Return val as string, empty string if None."""
    return str(val) if val is not None else ""


def _build_geojson(wells: list) -> dict:
    features = []
    for w in wells:
        lines = [f"<strong>{w['well_name']}</strong>",
                 f"API: {w['api_number']}",
                 f"{w['county']}, {w['state']}"]
        if w.get("status"):
            lines.append(f"Status: {w['status']}")
        if w.get("operator"):
            lines.append(f"Operator: {w['operator']}")
        if w.get("lease_code"):
            lines.append(f"Lease: {w['lease_code']}")

        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [w["lon"], w["lat"]]},
            "properties": {
                "popup": "<br>".join(lines),
                "color": STATE_COLORS.get(w["state"], DEFAULT_COLOR),
                "state": w["state"],
            },
        })
    return {"type": "FeatureCollection", "features": features}


def _legend_html(wells: list) -> str:
    states = sorted(set(w["state"] for w in wells))
    rows = []
    for s in states:
        color = STATE_COLORS.get(s, DEFAULT_COLOR)
        count = sum(1 for w in wells if w["state"] == s)
        rows.append(
            f'<div style="display:flex;align-items:center;gap:7px;margin:3px 0">'
            f'<span style="width:11px;height:11px;border-radius:50%;background:{color};flex-shrink:0"></span>'
            f'<span>{s} <span style="color:#94a3b8">({count})</span></span>'
            f'</div>'
        )
    return "".join(rows)


# ---------------------------------------------------------------------------
# Map generator
# ---------------------------------------------------------------------------

_MAP_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EOG Wells — {title}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html,body{{margin:0;padding:0;height:100%;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#1a1a2e;color:#eee}}
  #header{{padding:10px 18px;background:#16213e;border-bottom:2px solid #0f3460;display:flex;align-items:baseline;gap:14px}}
  #header h1{{font-size:1rem;font-weight:600;color:#e2e8f0;margin:0}}
  #header .sub{{font-size:.78rem;color:#94a3b8}}
  #map{{height:calc(100vh - 44px)}}
  .legend{{background:rgba(22,33,62,.95);border:1px solid #0f3460;border-radius:6px;padding:10px 14px;font-size:.78rem;line-height:1.5}}
  .legend h4{{margin:0 0 6px;font-size:.72rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.06em}}
  .leaflet-popup-content-wrapper{{border-radius:6px;font-size:.82rem}}
</style>
</head>
<body>
<div id="header">
  <h1>EOG Resources — Oil Well Map</h1>
  <span class="sub">{well_count} wells &nbsp;·&nbsp; {state_count} states &nbsp;·&nbsp; {filter_desc}</span>
</div>
<div id="map"></div>
<script>
(function(){{
  var geojson = {geojson_data};

  var map = L.map('map',{{preferCanvas:true}}).setView([38.5,-98.0],5);

  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{
    attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom:19
  }}).addTo(map);

  if(geojson.features.length>0){{
    var layer = L.geoJSON(geojson,{{
      pointToLayer:function(f,ll){{
        return L.circleMarker(ll,{{
          radius:5,fillColor:f.properties.color,
          color:'#fff',weight:0.6,opacity:.9,fillOpacity:.85
        }});
      }},
      onEachFeature:function(f,layer){{
        layer.bindPopup(f.properties.popup,{{maxWidth:280}});
        layer.on('mouseover',function(){{this.openPopup()}});
      }}
    }}).addTo(map);
    map.fitBounds(layer.getBounds(),{{padding:[30,30]}});
  }}

  var legend = L.control({{position:'bottomright'}});
  legend.onAdd = function(){{
    var d = L.DomUtil.create('div','legend');
    d.innerHTML = '<h4>State</h4>{legend_items}';
    return d;
  }};
  legend.addTo(map);
}})();
</script>
</body>
</html>
"""


def generate_map(
    state: Optional[str] = None,
    county: Optional[str] = None,
    status: Optional[str] = None,
    operator: Optional[str] = None,
    output_path: Optional[str] = None,
) -> str:
    """
    Generate an interactive Leaflet map of wells matching the given filters.
    Writes a self-contained HTML file to reports/ and returns the file path.

    All filters are optional — omit all to map every well with coordinates.
    """
    wells = _fetch_wells_for_map(state=state, county=county, status=status, operator=operator)

    if not wells:
        raise ValueError("No wells with coordinates match the given filters.")

    geojson = _build_geojson(wells)
    states = sorted(set(w["state"] for w in wells))
    legend = _legend_html(wells)

    # Build a human-readable filter description for the subtitle
    parts = []
    if state:   parts.append(state)
    if county:  parts.append(f"{county} County")
    if status:  parts.append(status)
    if operator: parts.append(operator)
    filter_desc = ", ".join(parts) if parts else "all wells"

    # Title slug for filename
    slug = re.sub(r"[^a-z0-9]+", "_", filter_desc.lower()).strip("_") or "all"

    if output_path:
        out = Path(output_path)
    else:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        out = REPORTS_DIR / f"map_{slug}.html"

    # Build HTML — use a manual replacement to avoid conflicts between
    # Python's str.format() and Leaflet's {s}/{z}/{x}/{y} tile placeholders.
    html = _MAP_HTML.format(
        title=filter_desc,
        well_count=len(wells),
        state_count=len(states),
        filter_desc=filter_desc,
        geojson_data=json.dumps(geojson, separators=(",", ":")),
        legend_items=legend,
    )

    out.write_text(html, encoding="utf-8")
    return str(out)
