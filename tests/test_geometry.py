"""Unit tests for geo-mcp's geometry functions, using the fake plots."""

import pytest

from mcp_servers.geo_mcp.countries import load_countries
from mcp_servers.geo_mcp.geometry import find_country, validate_geometry
from mcp_servers.geo_mcp.plots import load_plots

PLOTS = load_plots()


def geom(plot_id: str) -> dict:
    return PLOTS[plot_id]["geometry"]


@pytest.mark.parametrize("plot_id", ["P01", "P02", "P05", "P09", "P13", "P19"])
def test_valid_plots_have_no_errors(plot_id):
    assert validate_geometry(geom(plot_id)) == []


def test_bowtie_polygon_is_invalid():
    errors = validate_geometry(geom("P07"))
    assert len(errors) == 1
    assert "intersection" in errors[0].lower()


def test_unclosed_ring_is_invalid():
    errors = validate_geometry(geom("P12"))
    assert len(errors) == 1
    assert "closed" in errors[0].lower()


def test_swapped_lat_lon_is_out_of_range():
    errors = validate_geometry(geom("P15"))
    assert errors, "lat/lon swapped should give an error"
    assert "latitude" in errors[0].lower()


@pytest.mark.parametrize(
    "plot_id, country",
    [("P01", "ET"), ("P05", "CO"), ("P09", "BR"), ("P13", "VN"), ("P04", "KE"), ("P08", "EC")],
)
def test_find_country(plot_id, country):
    assert find_country(geom(plot_id), load_countries()) == country


def test_find_country_in_the_ocean_is_none():
    atlantic = {"type": "Point", "coordinates": [-30.0, 0.0]}
    assert find_country(atlantic, load_countries()) is None


def test_tool_results_never_contain_coordinates():
    """Design rule: coordinates must never reach the LLM, not even inside an error message."""
    import asyncio
    import json
    import re

    from mcp_servers.geo_mcp.server import mcp

    # Any number with 3+ decimals, or a "[x y]" pair, looks like a coordinate.
    coordinate = re.compile(r"-?\d+\.\d{3,}|\[-?\d+(\.\d+)? -?\d+(\.\d+)?\]")
    tools = ["validate_geometry", "calculate_area_ha", "check_point_or_polygon", "check_country"]

    async def call_all():
        for plot_id in PLOTS:
            for tool in tools:
                result = await mcp.call_tool(tool, {"plot_id": plot_id})
                text = json.dumps(result.structured_content)
                assert not coordinate.search(text), f"{tool}({plot_id}) leaks coordinates: {text}"

    asyncio.run(call_all())
