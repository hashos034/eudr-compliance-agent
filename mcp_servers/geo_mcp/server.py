"""geo-mcp: an MCP server that checks EUDR plot geolocation.

Tools take a plot ID, never coordinates, and return results without
coordinates or farmer details. That keeps location and personal data away
from the LLM.

Run it:          uv run python -m mcp_servers.geo_mcp.server
Inspect it:      npx @modelcontextprotocol/inspector uv run python -m mcp_servers.geo_mcp.server
"""

from fastmcp import FastMCP

from mcp_servers.geo_mcp import geometry
from mcp_servers.geo_mcp.plots import load_plots

mcp = FastMCP("geo-mcp")
PLOTS = load_plots()


def _get_plot(plot_id: str) -> dict:
    if plot_id not in PLOTS:
        raise ValueError(f"Unknown plot ID: {plot_id}")
    return PLOTS[plot_id]


@mcp.tool
def validate_geometry(plot_id: str) -> dict:
    """Check that a plot's geolocation is valid: coordinates in range, polygon rings closed, no self-intersections."""
    errors = geometry.validate_geometry(_get_plot(plot_id)["geometry"])
    return {"plot_id": plot_id, "valid": not errors, "errors": errors}


@mcp.tool
def calculate_area_ha(plot_id: str) -> dict:
    """Calculate a plot's area in hectares from its polygon. Points have area 0."""
    feature = _get_plot(plot_id)
    return {
        "plot_id": plot_id,
        "geometry_type": feature["geometry"]["type"],
        "area_ha": round(geometry.calculate_area_ha(feature["geometry"]), 2),
        "declared_area_ha": feature["properties"]["declared_area_ha"],
    }


@mcp.tool
def check_point_or_polygon(plot_id: str) -> dict:
    """Check the EUDR rule that plots larger than 4 ha are given as a polygon, not a single point."""
    feature = _get_plot(plot_id)
    errors = geometry.check_point_or_polygon(
        feature["geometry"], feature["properties"]["declared_area_ha"]
    )
    return {"plot_id": plot_id, "ok": not errors, "errors": errors}


# check_country comes in the next step: it needs country border data.

if __name__ == "__main__":
    mcp.run()
