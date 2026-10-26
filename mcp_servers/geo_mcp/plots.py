"""Load plots from the GeoJSON file. Coordinates stay inside this server."""

import json
import os
from pathlib import Path

DEFAULT_PLOTS_FILE = Path(__file__).resolve().parents[2] / "data" / "plots" / "plots.geojson"


def load_plots(path: Path | None = None) -> dict[str, dict]:
    """Return {plot_id: GeoJSON feature}. Path can be overridden with GEO_MCP_PLOTS_FILE."""
    path = path or Path(os.environ.get("GEO_MCP_PLOTS_FILE", DEFAULT_PLOTS_FILE))
    collection = json.loads(path.read_text())
    return {f["properties"]["plot_id"]: f for f in collection["features"]}
