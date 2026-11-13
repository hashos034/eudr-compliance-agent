"""forest-mcp: an MCP server that reports tree cover loss after the EUDR cut-off.

It only reads the local cache, so a check can't fail because a data provider is
down. The cache is written by refresh_cache.py. Tools take a plot ID, never
coordinates, and return results without coordinates or farmer details.

Run it:          uv run python -m mcp_servers.forest_mcp.server
Inspect it:      npx @modelcontextprotocol/inspector uv run python -m mcp_servers.forest_mcp.server
"""

import json
import os
from pathlib import Path

from fastmcp import FastMCP

from mcp_servers.forest_mcp import loss
from mcp_servers.forest_mcp.plots import geometry_hash, load_plots

DEFAULT_CACHE_FILE = Path(__file__).resolve().parent / "data" / "forest_cache.json"

mcp = FastMCP("forest-mcp")


def load_cache(path: Path | None = None) -> dict[str, dict]:
    """Return {plot_id: cache record}. A missing file means an empty cache, not a crash."""
    path = path or Path(os.environ.get("FOREST_MCP_CACHE_FILE", DEFAULT_CACHE_FILE))
    if not path.exists():
        return {}
    return json.loads(path.read_text())["plots"]


# Only the fingerprints are kept, so this process doesn't hold coordinates while serving.
PLOT_HASHES = {plot_id: geometry_hash(f["geometry"]) for plot_id, f in load_plots().items()}
CACHE = load_cache()


@mcp.tool
def check_forest_loss(plot_id: str) -> dict:
    """Report a plot's tree cover loss after the EUDR cut-off of 31 December 2020, and whether it is flagged."""
    if plot_id not in PLOT_HASHES:
        raise ValueError(f"Unknown plot ID: {plot_id}")
    record = CACHE.get(plot_id)
    # A record made for an older shape of this plot says nothing about the current one.
    if record and record["geometry_sha256"] != PLOT_HASHES[plot_id]:
        record = None
    return loss.assess(plot_id, record)


if __name__ == "__main__":
    mcp.run()
