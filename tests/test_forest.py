"""Tests for forest-mcp. They read the committed cache, so no network is needed."""

import asyncio
import json
import re

import pytest
from fastmcp import Client

from mcp_servers.forest_mcp import loss
from mcp_servers.forest_mcp.refresh_cache import is_usable, tile_name
from mcp_servers.forest_mcp.server import mcp

PLOT_IDS = [f"P{i:02d}" for i in range(1, 21)]


def call(tool: str, **arguments) -> dict:
    async def run():
        async with Client(mcp) as client:
            return (await client.call_tool(tool, arguments)).data

    return asyncio.run(run())


@pytest.mark.parametrize("plot_id", ["P19", "P20"])
def test_plots_with_loss_after_2020_are_flagged(plot_id):
    result = call("check_forest_loss", plot_id=plot_id)
    assert result["status"] == "checked"
    assert result["flagged"] is True
    assert result["loss_after_cutoff_ha"] >= loss.MIN_FLAG_HA


def test_loss_before_the_cutoff_is_not_flagged():
    """P18 lost trees in 2010 and 2013. That is legal under the EUDR."""
    result = call("check_forest_loss", plot_id="P18")
    assert result["flagged"] is False
    assert result["loss_up_to_cutoff_ha"] > 0


@pytest.mark.parametrize("plot_id", ["P07", "P12", "P15"])
def test_invalid_geometry_is_not_checked(plot_id):
    assert call("check_forest_loss", plot_id=plot_id)["status"] == "not_checked"


def test_unknown_plot_is_an_error():
    with pytest.raises(Exception, match="Unknown plot ID"):
        call("check_forest_loss", plot_id="P99")


def test_tool_results_never_contain_coordinates():
    coordinate = re.compile(r"-?\d+\.\d{3,}")
    for plot_id in PLOT_IDS:
        text = json.dumps(call("check_forest_loss", plot_id=plot_id))
        assert not coordinate.search(text), f"{plot_id} result looks like it holds a coordinate"


def test_missing_record_means_unknown_not_clean():
    result = loss.assess("P01", None)
    assert result["status"] == "no_data"
    assert result["flagged"] is None


def test_2020_counts_as_before_the_cutoff():
    record = {"status": "checked", "measured_area_ha": 10, "loss_ha_by_year": {"2020": 5.0}}
    assert loss.assess("X", record)["flagged"] is False


def test_tiny_loss_is_treated_as_noise():
    record = {"status": "checked", "measured_area_ha": 10, "loss_ha_by_year": {"2022": 0.08}}
    assert loss.assess("X", record)["flagged"] is False


def test_tile_name_uses_the_top_left_corner():
    assert tile_name(-64.3, -9.56) == "00N_070W"
    assert tile_name(38.2, 6.16) == "10N_030E"


def test_swapped_coordinates_are_not_usable():
    swapped = {"type": "Polygon", "coordinates": [[[12, 108], [12.1, 108], [12.1, 108.1], [12, 108]]]}
    assert not is_usable(swapped)
