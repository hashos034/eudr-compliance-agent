"""Reads supplier data in code. Nothing here goes to the LLM without the PII guardrail."""

import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"


def load_suppliers(path: Path = DATA / "suppliers.json") -> dict[str, dict]:
    return {supplier["supplier_id"]: supplier for supplier in json.loads(path.read_text())}


def load_known_pii() -> dict[str, list[str]]:
    """Every name, phone number and ID our own structured data holds."""
    suppliers = load_suppliers().values()
    plots = json.loads((DATA / "plots" / "plots.geojson").read_text())["features"]
    farmers = [plot["properties"] for plot in plots]
    return {
        "PERSON": [s["contact_name"] for s in suppliers] + [f["farmer_name"] for f in farmers],
        "PHONE_NUMBER": [s["contact_phone"] for s in suppliers] + [f["farmer_phone"] for f in farmers],
        "NATIONAL_ID": [s["contact_national_id"] for s in suppliers],
    }
