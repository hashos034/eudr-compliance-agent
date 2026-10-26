"""Unit tests for geo-mcp's geometry functions, using the fake plots."""

import pytest

from mcp_servers.geo_mcp.geometry import validate_geometry
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
