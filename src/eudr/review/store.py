"""Keeps each check on disk while it waits for a human decision.

One folder per check, in checks/ (which git ignores):

    checks/<check_id>/check.json      the check, still pseudonymized
    checks/<check_id>/pii_map.json    placeholder -> real value, readable by the owner only
    checks/<check_id>/dds_draft.md    only after approval

The check and the lookup table are kept apart on purpose. The check is safe to
send to the LLM again (the DDS step does that), and real names only appear when
a person views it. In production both would live in a database, with the lookup
table encrypted. See docs/production-considerations.md.
"""

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from eudr.guardrails.pii import restore_with
from eudr.risk import RiskAssessment
from eudr.schemas import ShipmentCheck

CHECKS_DIR = Path(os.environ.get("EUDR_CHECKS_DIR", Path(__file__).resolve().parents[3] / "checks"))

Status = Literal["running", "awaiting_review", "approved", "rejected", "failed"]


class Review(BaseModel):
    decision: Literal["approved", "rejected"]
    reviewer: str
    comment: str
    at: str


class CheckRecord(BaseModel):
    check_id: str
    created_at: str
    status: Status
    shipment: dict
    result: ShipmentCheck | None = None
    risk: RiskAssessment | None = None
    cost_usd: float | None = None
    review: Review | None = None
    error: str | None = None


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class CheckStore:
    def __init__(self, root: Path = CHECKS_DIR) -> None:
        self.root = root

    def folder(self, check_id: str) -> Path:
        # Check IDs come from outside (the API), so they must not be able to point elsewhere.
        if not check_id.replace("-", "").isalnum():
            raise KeyError(check_id)
        return self.root / check_id

    def create(self, shipment: dict) -> CheckRecord:
        record = CheckRecord(
            check_id=f"chk-{uuid.uuid4().hex[:12]}",
            created_at=now(),
            status="running",
            shipment=shipment,
        )
        self.save(record)
        return record

    def save(self, record: CheckRecord) -> None:
        folder = self.folder(record.check_id)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "check.json").write_text(record.model_dump_json(indent=2))

    def load(self, check_id: str) -> CheckRecord:
        path = self.folder(check_id) / "check.json"
        if not path.exists():
            raise KeyError(check_id)
        return CheckRecord.model_validate_json(path.read_text())

    def list(self) -> list[CheckRecord]:
        if not self.root.exists():
            return []
        records = [CheckRecord.model_validate_json(p.read_text()) for p in self.root.glob("*/check.json")]
        return sorted(records, key=lambda record: record.created_at)

    def save_lookup_table(self, check_id: str, table: dict[str, str]) -> None:
        path = self.folder(check_id) / "pii_map.json"
        # Create it with owner-only permissions from the start, rather than fixing them after.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(table, f, ensure_ascii=False)

    def restore(self, check_id: str, text: str, inside_json: bool = False) -> str:
        path = self.folder(check_id) / "pii_map.json"
        table = json.loads(path.read_text()) if path.exists() else {}
        if inside_json:
            # Escape the values, so a quote in a name can't break the JSON around it.
            table = {token: json.dumps(value, ensure_ascii=False)[1:-1] for token, value in table.items()}
        return restore_with(table, text)

    def view(self, check_id: str) -> CheckRecord:
        """The record with real names restored. For the human reviewer, never for the LLM."""
        record = self.load(check_id)
        restored = self.restore(check_id, record.model_dump_json(), inside_json=True)
        return CheckRecord.model_validate_json(restored)

    def dds_path(self, check_id: str) -> Path:
        return self.folder(check_id) / "dds_draft.md"
