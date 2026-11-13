"""Checks on the agent setup. None of these call the LLM or cost anything."""

import asyncio
import json

import pytest
from claude_agent_sdk import AssistantMessage, ToolUseBlock
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from eudr.agents.orchestrator import (
    FOREST_TOOLS,
    GEO_TOOLS,
    assert_everything_covered,
    assert_tools_are_locked_down,
    build_options,
    check_shipment,
    forest_server_config,
    geo_server_config,
)
from eudr.cost_tracker import CostTracker
from eudr.schemas import PlotCheck, Shipment, ShipmentCheck, SupplierCheck


def test_orchestrator_only_gets_the_agent_tool():
    options = build_options("prompt")
    assert options.tools == ["Agent"]
    assert options.mcp_servers == {}
    assert options.permission_mode == "dontAsk"
    assert options.setting_sources == []


def test_geo_subagent_only_gets_geo_tools():
    geo = build_options("prompt").agents["geo-checker"]
    assert geo.tools == GEO_TOOLS
    assert all(tool.startswith("mcp__geo__") for tool in geo.tools)


def test_forest_subagent_only_gets_forest_tools():
    forest = build_options("prompt").agents["forest-checker"]
    assert forest.tools == FOREST_TOOLS
    assert [list(server) for server in forest.mcpServers] == [["forest"]]


@pytest.mark.parametrize("tool", ["Read", "Bash", "Grep", "WebFetch", "mcp__geo__check_country"])
def test_run_stops_if_orchestrator_has_another_tool(tool):
    with pytest.raises(RuntimeError, match="unexpected tools"):
        assert_tools_are_locked_down(["Agent", tool])


def test_expected_orchestrator_tools_pass():
    assert_tools_are_locked_down(["Task", "StructuredOutput"])


async def _server_tool_names(config: dict) -> list[str]:
    transport = StdioTransport(command=config["command"], args=config["args"], env=config["env"])
    async with Client(transport) as client:
        return [tool.name for tool in await client.list_tools()]


@pytest.mark.parametrize(
    "prefix, config, expected",
    [("geo", geo_server_config(), GEO_TOOLS), ("forest", forest_server_config(), FOREST_TOOLS)],
)
def test_tool_names_match_the_real_server(prefix, config, expected):
    names = asyncio.run(_server_tool_names(config))
    assert sorted(f"mcp__{prefix}__{name}" for name in names) == sorted(expected)


def test_empty_prompt_stops_before_any_llm_call(tmp_path):
    with pytest.raises(RuntimeError, match="GEO_SUBAGENT_PROMPT is empty"):
        asyncio.run(check_shipment(tmp_path / "unused.json", geo_prompt=" "))


SHIPMENT = Shipment(shipment_id="S1", supplier_ids=["SUP-1"], plot_ids=["P1", "P2"])


def _results(plot_ids: tuple[str, ...], supplier_ids: tuple[str, ...] = ("SUP-1",)) -> ShipmentCheck:
    return ShipmentCheck(
        shipment_id="S1",
        plots=[PlotCheck.model_construct(plot_id=plot_id) for plot_id in plot_ids],
        suppliers=[SupplierCheck.model_construct(supplier_id=s) for s in supplier_ids],
    )


def test_coverage_check_passes_when_everything_matches():
    assert_everything_covered(SHIPMENT, _results(("P2", "P1")))


@pytest.mark.parametrize(
    "returned",
    [
        _results(("P1",)),
        _results(("P1", "P2", "P3")),
        _results(("P1", "P1")),
        _results(("P1", "P2"), supplier_ids=()),
    ],
)
def test_coverage_check_catches_missing_extra_and_duplicate(returned):
    with pytest.raises(RuntimeError, match="don't match"):
        assert_everything_covered(SHIPMENT, returned)


def _step(message_id: str, input_tokens: int, parent: str | None = None, content=None) -> AssistantMessage:
    return AssistantMessage(
        content=content or [],
        model="m",
        parent_tool_use_id=parent,
        usage={"input_tokens": input_tokens},
        message_id=message_id,
    )


def test_tracker_splits_usage_per_agent_and_counts_each_response_once(tmp_path):
    tracker = CostTracker("S1", log_file=tmp_path / "costs.jsonl")
    call = ToolUseBlock(id="call_1", name="Agent", input={"subagent_type": "geo-checker"})

    tracker.record(_step("m1", 100, content=[call]))
    tracker.record(_step("m1", 100))  # same API response, must not count twice
    tracker.record(_step("m2", 40, parent="call_1"))
    tracker.save()

    agents = tracker.summary()["agents"]
    assert agents["orchestrator"] == {"steps": 1, "input_tokens": 100}
    assert agents["geo-checker"] == {"steps": 1, "input_tokens": 40}
    logged = json.loads((tmp_path / "costs.jsonl").read_text())
    assert logged["shipment_id"] == "S1"
