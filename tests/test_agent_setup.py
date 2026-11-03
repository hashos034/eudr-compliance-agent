"""Checks on the agent setup. None of these call the LLM or cost anything."""

import asyncio
import json

import pytest
from claude_agent_sdk import AssistantMessage, ToolUseBlock
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from eudr.agents.orchestrator import (
    GEO_TOOLS,
    assert_all_plots_covered,
    assert_tools_are_locked_down,
    build_options,
    check_shipment,
    geo_server_config,
)
from eudr.cost_tracker import CostTracker
from eudr.schemas import PlotCheck, Shipment, ShipmentCheck


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


@pytest.mark.parametrize("tool", ["Read", "Bash", "Grep", "WebFetch", "mcp__geo__check_country"])
def test_run_stops_if_orchestrator_has_another_tool(tool):
    with pytest.raises(RuntimeError, match="unexpected tools"):
        assert_tools_are_locked_down(["Agent", tool])


def test_expected_orchestrator_tools_pass():
    assert_tools_are_locked_down(["Task", "StructuredOutput"])


async def _server_tool_names() -> list[str]:
    config = geo_server_config()
    transport = StdioTransport(command=config["command"], args=config["args"], env=config["env"])
    async with Client(transport) as client:
        return [tool.name for tool in await client.list_tools()]


def test_geo_tool_names_match_the_real_server():
    names = asyncio.run(_server_tool_names())
    assert sorted(f"mcp__geo__{name}" for name in names) == sorted(GEO_TOOLS)


def test_empty_prompt_stops_before_any_llm_call(tmp_path):
    with pytest.raises(RuntimeError, match="GEO_SUBAGENT_PROMPT is empty"):
        asyncio.run(check_shipment(tmp_path / "unused.json", geo_prompt=" "))


def _verdicts(*plot_ids: str) -> ShipmentCheck:
    return ShipmentCheck(
        shipment_id="S1",
        plots=[PlotCheck.model_construct(plot_id=plot_id) for plot_id in plot_ids],
    )


def test_all_plots_covered_passes_when_they_match():
    assert_all_plots_covered(Shipment(shipment_id="S1", plot_ids=["P1", "P2"]), _verdicts("P2", "P1"))


@pytest.mark.parametrize("returned", [("P1",), ("P1", "P2", "P3"), ("P1", "P1")])
def test_all_plots_covered_catches_missing_extra_and_duplicate(returned):
    with pytest.raises(RuntimeError, match="don't match"):
        assert_all_plots_covered(Shipment(shipment_id="S1", plot_ids=["P1", "P2"]), _verdicts(*returned))


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
