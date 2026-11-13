"""Load plots from the GeoJSON file. Coordinates stay inside this server.

A separate copy of geo-mcp's loader, because each MCP server stands on its own.
"""

import hashlib
import json
import os
from pathlib import Path

DEFAULT_PLOTS_FILE = Path(__file__).resolve().parents[2] / "data" / "plots" / "plots.geojson"


def load_plots(path: Path | None = None) -> dict[str, dict]:
    """Return {plot_id: GeoJSON feature}. Path can be overridden with FOREST_MCP_PLOTS_FILE."""
    path = path or Path(os.environ.get("FOREST_MCP_PLOTS_FILE", DEFAULT_PLOTS_FILE))
    collection = json.loads(path.read_text())
    return {f["properties"]["plot_id"]: f for f in collection["features"]}


def geometry_hash(geometry: dict) -> str:
    """A fingerprint of a plot's shape. If the shape changes, the fingerprint changes."""
    return hashlib.sha256(json.dumps(geometry, sort_keys=True).encode()).hexdigest()
