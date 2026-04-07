"""
Generate an interactive HTML map of EOG well locations.

Uses Leaflet.js (loaded from CDN) — no extra Python dependencies.
Wells are color-coded by state and show a popup with details on click.
Wells missing coordinates are excluded.

Usage:
    python scripts/generate_map.py
    python scripts/generate_map.py --output reports/custom_map.html

Output: reports/wells_map.html (opens in any browser)
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.compiler.db import get_connection
from sqlalchemy import text

# Color palette — one per state, colorblind-friendly
STATE_COLORS = {
    "TX": "#e63946",  # red
    "NM": "#f4a261",  # orange
    "CO": "#2a9d8f",  # teal
    "MS": "#457b9d",  # blue
    "CA": "#8338ec",  # purple
    "KS": "#fb8500",  # amber
    "LA": "#06d6a0",  # green
    "ND": "#ef476f",  # pink
    "OH": "#118ab2",  # steel blue
}
DEFAULT_COLOR = "#888888"

STATUS_ICONS = {
    "producing": "▲",
    "active":    "●",
    "new":       "◆",
}


def fetch_wells():
    with get_connection() as conn:
        rows = conn.execute(text(
            "SELECT well_name, api_number, county, state, status, "
            "       operator, lease_code, lat, lon "
            "FROM wells "
            "WHERE lat IS NOT NULL AND lon IS NOT NULL "
            "ORDER BY state, well_name"
        )).fetchall()
    return [dict(r._mapping) for r in rows]


def build_geojson(wells):
    features = []
    for w in wells:
        status = (w["status"] or "").lower()
        icon = STATUS_ICONS.get(status, "○")
        popup_lines = [
            f"<strong>{w['well_name']}</strong>",
            f"API: {w['api_number']}",
            f"County: {w['county']}, {w['state']}",
        ]
        if w.get("status"):
            popup_lines.append(f"Status: {w['status']}")
        if w.get("operator"):
            popup_lines.append(f"Operator: {w['operator']}")
        if w.get("lease_code"):
            popup_lines.append(f"Lease: {w['lease_code']}")

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [w["lon"], w["lat"]],
            },
            "properties": {
                "popup": "<br>".join(popup_lines),
                "color": STATE_COLORS.get(w["state"], DEFAULT_COLOR),
                "state": w["state"],
                "icon": icon,
            },
        })
    return {"type": "FeatureCollection", "features": features}


def state_legend_html(wells):
    states = sorted(set(w["state"] for w in wells))
    items = []
    for s in states:
        color = STATE_COLORS.get(s, DEFAULT_COLOR)
        count = sum(1 for w in wells if w["state"] == s)
        items.append(
            f'<div class="legend-item">'
            f'<span class="legend-dot" style="background:{color}"></span>'
            f'{s} ({count})'
            f'</div>'
        )
    return "\n".join(items)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EOG Oil Well Map</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #1a1a2e; color: #eee; }}
    header {{
      padding: 12px 20px;
      background: #16213e;
      border-bottom: 1px solid #0f3460;
      display: flex;
      align-items: center;
      gap: 16px;
    }}
    header h1 {{ font-size: 1.1rem; font-weight: 600; color: #e2e8f0; }}
    header .subtitle {{ font-size: 0.8rem; color: #94a3b8; }}
    #map {{ height: calc(100vh - 50px); width: 100%; }}
    .legend {{
      background: rgba(22, 33, 62, 0.95);
      border: 1px solid #0f3460;
      border-radius: 6px;
      padding: 10px 14px;
      font-size: 0.78rem;
      line-height: 1.6;
      min-width: 110px;
    }}
    .legend h4 {{ margin-bottom: 6px; font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }}
    .legend-item {{ display: flex; align-items: center; gap: 6px; }}
    .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}
    .leaflet-popup-content-wrapper {{ border-radius: 6px; }}
    .leaflet-popup-content {{ font-size: 0.82rem; line-height: 1.6; }}
    .leaflet-popup-content strong {{ font-size: 0.9rem; }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>EOG Resources — Oil Well Map</h1>
      <div class="subtitle">{well_count} wells with coordinates &nbsp;·&nbsp; {state_count} states</div>
    </div>
  </header>
  <div id="map"></div>

  <script>
    const geojson = {geojson};

    const map = L.map('map', {{ preferCanvas: true }}).setView([38.5, -98.0], 5);

    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19
    }}).addTo(map);

    function pointToLayer(feature, latlng) {{
      return L.circleMarker(latlng, {{
        radius: 5,
        fillColor: feature.properties.color,
        color: '#fff',
        weight: 0.5,
        opacity: 0.9,
        fillOpacity: 0.85,
      }});
    }}

    function onEachFeature(feature, layer) {{
      layer.bindPopup(feature.properties.popup, {{ maxWidth: 260 }});
      layer.on('mouseover', function() {{ this.openPopup(); }});
    }}

    L.geoJSON(geojson, {{ pointToLayer, onEachFeature }}).addTo(map);

    // Legend
    const legend = L.control({{ position: 'bottomright' }});
    legend.onAdd = function() {{
      const div = L.DomUtil.create('div', 'legend');
      div.innerHTML = '<h4>State</h4>{legend_items}';
      return div;
    }};
    legend.addTo(map);
  </script>
</body>
</html>
"""


def generate(output_path: Path):
    wells = fetch_wells()
    if not wells:
        print("No wells with coordinates found in database.")
        return

    geojson = build_geojson(wells)
    states = set(w["state"] for w in wells)
    legend = state_legend_html(wells)

    html = HTML_TEMPLATE.format(
        well_count=len(wells),
        state_count=len(states),
        geojson=json.dumps(geojson),
        legend_items=legend,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"Map written to: {output_path}")
    print(f"Wells plotted: {len(wells)}")
    print(f"States: {', '.join(sorted(states))}")


def main():
    parser = argparse.ArgumentParser(description="Generate interactive well map")
    parser.add_argument(
        "--output", default="reports/wells_map.html",
        help="Output HTML file path (default: reports/wells_map.html)"
    )
    args = parser.parse_args()
    generate(Path(args.output))


if __name__ == "__main__":
    main()
