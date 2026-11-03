"""Runs one shipment check: the orchestrator delegates to the geo subagent.

Most of this file enforces the data boundary. Agents get no file or shell
tools, so the only way they can learn about a plot is through geo-mcp, which
returns results and never coordinates.
"""

import json
import os
import sys
from pathlib import Path

from claude_agent_sdk import (
    AgentDefinition,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    query,
)

from eudr.agents.prompts import GEO_SUBAGENT_PROMPT, ORCHESTRATOR_PROMPT
from eudr.cost_tracker import CostTracker
from eudr.guardrails.pii import Pseudonymizer
from eudr.schemas import Shipment, ShipmentCheck
from eudr.supplier_data import load_known_pii, load_suppliers

ROOT = Path(__file__).resolve().parents[3]
MODEL = "claude-opus-5-5"
MAX_COST_USD = 1.0

GEO_TOOLS = [
    "mcp__geo__validate_geometry",
    "mcp__geo__calculate_area_ha",
    "mcp__geo__check_point_or_polygon",
    "mcp__geo__check_country",
]

# Everything the orchestrator itself may have. Its subagent is called through
# "Agent", which the SDK can also list as "Task".
ALLOWED_ORCHESTRATOR_TOOLS = {"Agent", "Task", "StructuredOutput"}


def geo_server_config() -> dict:
    """How to start geo-mcp as a separate process."""
    return {
        "type": "stdio",
        "command": sys.executable,
        "args": ["-m", "mcp_servers.geo_mcp.server"],
        "env": {"PYTHONPATH": str(ROOT)},
    }


def build_options(geo_prompt: str) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model=MODEL,
        system_prompt=ORCHESTRATOR_PROMPT,
        # The base tool list. Read, Bash and the rest are not in the session at all.
        tools=["Agent"],
        # Pre-approves these calls. dontAsk below denies everything else.
        allowed_tools=["Agent", *GEO_TOOLS],
        disallowed_tools=["Agent(fork)"],
        permission_mode="dontAsk",
        agents={
            "geo-checker": AgentDefinition(
                description="Checks the geolocation of EUDR plots by plot ID.",
                prompt=geo_prompt,
                tools=GEO_TOOLS,
                # Defined here and not on the orchestrator, so only this agent has geo-mcp.
                mcpServers=[{"geo": geo_server_config()}],
                model=MODEL,
                background=False,
            ),
        },
        # Ignore this machine's CLAUDE.md, settings and MCP servers, so the
        # agent's context is exactly what this file defines.
        setting_sources=[],
        strict_mcp_config=True,
        output_format={"type": "json_schema", "schema": ShipmentCheck.model_json_schema()},
        max_turns=15,
        max_budget_usd=MAX_COST_USD,
        # Without this the stream skips the subagent's final response, so the
        # cost tracker would undercount it.
        forward_subagent_text=True,
        cwd=ROOT,
        env={
            "CLAUDE_AGENT_SDK_DISABLE_BUILTIN_AGENTS": "1",
            "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",
            # Skips the background Haiku request that writes a session title.
            "CLAUDE_CODE_DISABLE_TERMINAL_TITLE": "1",
        },
    )


def assert_tools_are_locked_down(tools: list[str]) -> None:
    """Stop the run if the orchestrator was given any tool we didn't choose."""
    extra = set(tools) - ALLOWED_ORCHESTRATOR_TOOLS
    if extra:
        raise RuntimeError(f"Stopping: orchestrator has unexpected tools: {sorted(extra)}")


def assert_everything_covered(shipment: Shipment, check: ShipmentCheck) -> None:
    """The LLM could skip something, so code confirms each plot and supplier got exactly one result."""
    returned_plots = sorted(plot.plot_id for plot in check.plots)
    returned_suppliers = sorted(supplier.supplier_id for supplier in check.suppliers)
    if returned_plots != sorted(shipment.plot_ids) or returned_suppliers != sorted(shipment.supplier_ids):
        raise RuntimeError(
            f"Results don't match the shipment: got plots {returned_plots} "
            f"and suppliers {returned_suppliers}"
        )


def build_prompt(shipment: Shipment, pseudonymizer: Pseudonymizer) -> str:
    """What the LLM receives. Supplier notes are the only free text, and they go through the guardrail."""
    suppliers = load_suppliers()
    prompt = json.dumps(
        {
            "shipment_id": shipment.shipment_id,
            "plot_ids": shipment.plot_ids,
            "suppliers": [
                {
                    "supplier_id": supplier_id,
                    "note": pseudonymizer.pseudonymize(suppliers[supplier_id]["notes"]),
                }
                for supplier_id in shipment.supplier_ids
            ],
        },
        ensure_ascii=False,
    )
    pseudonymizer.assert_clean(prompt)
    return prompt


def restore_personal_data(check: ShipmentCheck, pseudonymizer: Pseudonymizer) -> ShipmentCheck:
    """Put real names back in the explanations. The result is for the human reviewer only."""

    def restored(item):
        return item.model_copy(update={"explanation": pseudonymizer.restore(item.explanation)})

    return check.model_copy(
        update={
            "plots": [restored(plot) for plot in check.plots],
            "suppliers": [restored(supplier) for supplier in check.suppliers],
        }
    )


async def check_shipment(path: Path, geo_prompt: str = GEO_SUBAGENT_PROMPT) -> tuple[ShipmentCheck, CostTracker]:
    if not geo_prompt.strip():
        raise RuntimeError("GEO_SUBAGENT_PROMPT is empty. Write it in src/eudr/agents/prompts.py.")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to .env.")

    shipment = Shipment.model_validate_json(path.read_text())
    pseudonymizer = Pseudonymizer(load_known_pii())
    prompt = build_prompt(shipment, pseudonymizer)
    tracker = CostTracker(shipment.shipment_id)
    result: ResultMessage | None = None

    try:
        async for message in query(
            prompt=prompt,
            options=build_options(geo_prompt),
        ):
            if isinstance(message, SystemMessage) and message.subtype == "init":
                assert_tools_are_locked_down(message.data["tools"])
            tracker.record(message)
            if isinstance(message, ResultMessage):
                result = message
    finally:
        tracker.save()

    if result is None or result.subtype != "success" or not result.structured_output:
        subtype = result.subtype if result else "no result"
        raise RuntimeError(f"The check ended without a valid verdict ({subtype}).")

    check = ShipmentCheck.model_validate(result.structured_output)
    assert_everything_covered(shipment, check)
    return restore_personal_data(check, pseudonymizer), tracker
