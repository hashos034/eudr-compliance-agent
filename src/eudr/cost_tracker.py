"""Logs what each check costs, as one JSON line per run in logs/costs.jsonl.

What the SDK can and can't tell us:
- Total cost and per-model tokens are accurate for the whole run, subagents
  included. The dollar figure is an estimate from the SDK's price table, not a bill.
- Per-agent, only API steps and input tokens are reliable. The SDK's per-step
  output token count is a placeholder, so we don't report it per agent.
"""

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from claude_agent_sdk import AssistantMessage, ResultMessage, ToolUseBlock

LOG_FILE = Path(__file__).resolve().parents[2] / "logs" / "costs.jsonl"
ORCHESTRATOR = "orchestrator"


@dataclass
class AgentUsage:
    steps: int = 0
    input_tokens: int = 0


class CostTracker:
    def __init__(self, shipment_id: str, log_file: Path = LOG_FILE) -> None:
        self.shipment_id = shipment_id
        self.log_file = log_file
        self.agents: dict[str, AgentUsage] = defaultdict(AgentUsage)
        self.total_cost_usd: float | None = None
        self.output_tokens_by_model: dict[str, int] = {}
        self._agent_names: dict[str, str] = {}
        self._seen_message_ids: set[str] = set()

    def record(self, message: object) -> None:
        if isinstance(message, AssistantMessage):
            self._record_step(message)
        elif isinstance(message, ResultMessage):
            self.total_cost_usd = message.total_cost_usd
            self.output_tokens_by_model = {
                model: usage["outputTokens"] for model, usage in (message.model_usage or {}).items()
            }

    def _record_step(self, message: AssistantMessage) -> None:
        for block in message.content:
            if isinstance(block, ToolUseBlock) and block.name in ("Agent", "Task"):
                self._agent_names[block.id] = block.input.get("subagent_type", "unknown")

        # One API response can arrive as several messages with the same ID.
        if not message.usage or message.message_id in self._seen_message_ids:
            return
        self._seen_message_ids.add(message.message_id)

        name = ORCHESTRATOR
        if message.parent_tool_use_id:
            name = self._agent_names.get(message.parent_tool_use_id, "unknown")
        usage = self.agents[name]
        usage.steps += 1
        usage.input_tokens += (
            message.usage.get("input_tokens", 0)
            + message.usage.get("cache_read_input_tokens", 0)
            + message.usage.get("cache_creation_input_tokens", 0)
        )

    def summary(self) -> dict:
        return {
            "shipment_id": self.shipment_id,
            "estimated_cost_usd": self.total_cost_usd,
            "output_tokens_by_model": self.output_tokens_by_model,
            "agents": {name: asdict(usage) for name, usage in self.agents.items()},
        }

    def save(self) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        entry = {"timestamp": datetime.now(UTC).isoformat(), **self.summary()}
        with self.log_file.open("a") as f:
            f.write(json.dumps(entry) + "\n")
