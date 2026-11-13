"""Drafts a due diligence statement (DDS) for a check a human has approved.

The work is split by the project's main rule:
- The LLM writes one thing: a short risk assessment summary, from the check's
  pseudonymized results. It sees plot IDs and verdicts, never coordinates.
- Code builds everything else: operator, product, quantity, the plot geolocation
  required by EUDR Article 9, and the fixed statement text from Annex II.

The draft is for a person to check and file in the EU's information system.
Filing it is out of scope.
"""

import json
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
from pydantic import BaseModel

from eudr.agents.orchestrator import MODEL, ROOT
from eudr.review.store import CheckRecord
from eudr.risk import DUE_DILIGENCE
from eudr.supplier_data import DATA, load_suppliers

# Annex II, point 8 of Regulation (EU) 2023/1115.
STATEMENT = (
    "By submitting this due diligence statement the operator confirms that due diligence in "
    "accordance with Regulation (EU) 2023/1115 was carried out and that no or only a negligible "
    "risk was found that the relevant products do not comply with Article 3, point (a) or (b), "
    "of that Regulation."
)

SUMMARY_PROMPT = """\
You write the risk assessment summary of an EUDR due diligence statement for a coffee
shipment. A human compliance officer has already approved the check.

You receive the shipment's plot verdicts, the suppliers' legality results and each
production country's risk class. Write 3 to 5 plain sentences that say what was
checked (geolocation, tree cover loss after 31 December 2020, proof of legality), what
was found, and why the risk is negligible. Use only the facts you are given. Don't
add facts, numbers or legal claims of your own.

Placeholders such as <PERSON_1> stand in for personal data. Leave them out of the summary.
"""


class Summary(BaseModel):
    risk_assessment_summary: str


def summary_input(record: CheckRecord) -> str:
    """What the LLM sees: verdicts and IDs only. The record is still pseudonymized."""
    return json.dumps(
        {
            "shipment_id": record.shipment["shipment_id"],
            "plots": [plot.model_dump() for plot in record.result.plots],
            "suppliers": [supplier.model_dump() for supplier in record.result.suppliers],
            "country_risk": record.risk.country_risk,
        },
        ensure_ascii=False,
    )


async def write_summary(record: CheckRecord) -> tuple[str, float]:
    options = ClaudeAgentOptions(
        model=MODEL,
        system_prompt=SUMMARY_PROMPT,
        tools=[],
        permission_mode="dontAsk",
        setting_sources=[],
        strict_mcp_config=True,
        output_format={"type": "json_schema", "schema": Summary.model_json_schema()},
        max_turns=3,
        max_budget_usd=0.25,
        cwd=ROOT,
        env={"CLAUDE_CODE_DISABLE_TERMINAL_TITLE": "1"},
    )
    result = None
    async for message in query(prompt=summary_input(record), options=options):
        if isinstance(message, ResultMessage):
            result = message
    if result is None or result.subtype != "success" or not result.structured_output:
        raise RuntimeError("The DDS summary could not be written.")
    summary = Summary.model_validate(result.structured_output).risk_assessment_summary
    return summary, result.total_cost_usd or 0


def load_plot_geometries(plots_file: Path = DATA / "plots" / "plots.geojson") -> dict[str, dict]:
    collection = json.loads(plots_file.read_text())
    return {f["properties"]["plot_id"]: f for f in collection["features"]}


def plot_geojson(plot_ids: list[str]) -> dict:
    """The geolocation for the EU system: shape and plot ID only, without the farmer's details."""
    plots = load_plot_geometries()
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": plots[plot_id]["geometry"],
                "properties": {"plot_id": plot_id, "area_ha": plots[plot_id]["properties"]["declared_area_ha"]},
            }
            for plot_id in plot_ids
        ],
    }


def render(record: CheckRecord, summary: str, operator: dict | None = None) -> str:
    """Build the DDS draft in Markdown. Runs after the LLM step, so coordinates can go in."""
    operator = operator or json.loads((DATA / "operator.json").read_text())
    shipment = record.shipment
    suppliers = load_suppliers()
    review = record.review
    geojson = plot_geojson(shipment["plot_ids"])
    countries = ", ".join(f"{c} ({risk} risk)" for c, risk in record.risk.country_risk.items())
    due_diligence = {DUE_DILIGENCE[risk] for risk in record.risk.country_risk.values()}

    lines = [
        f"# Due diligence statement (draft): {shipment['shipment_id']}",
        "",
        "> Draft for review. Check every field before filing it in the EU information system.",
        "",
        "## 1. Operator",
        "",
        f"- **Name:** {operator['name']}",
        f"- **Address:** {operator['address']}",
        f"- **EORI:** {operator['eori']}",
        f"- **Activity:** {operator['activity']}",
        "",
        "## 2. Product",
        "",
        f"- **HS code:** {shipment.get('hs_code', 'not given')} (coffee)",
        f"- **Quantity:** {shipment.get('quantity_kg', 'not given')} kg net mass",
    ]
    period = shipment.get("production_period")
    if period:
        lines.append(f"- **Production period:** {period['start']} to {period['end']}")
    lines += [
        f"- **Countries of production:** {countries}",
        f"- **Due diligence applied:** {'; '.join(sorted(due_diligence))}",
        "",
        "## 3. Suppliers",
        "",
        *[
            f"- {s} {suppliers[s]['name']} ({suppliers[s]['country']})"
            for s in shipment["supplier_ids"]
        ],
        "",
        "## 4. Geolocation of plots",
        "",
        "| Plot | Type | Area (ha) | Geolocation |",
        "| --- | --- | --- | --- |",
    ]
    for feature in geojson["features"]:
        geometry = feature["geometry"]
        coordinates = geometry["coordinates"]
        if geometry["type"] == "Point":
            where = f"{coordinates[1]:.6f}, {coordinates[0]:.6f} (lat, lon)"
        else:
            where = f"polygon with {len(coordinates[0]) - 1} corners, see GeoJSON below"
        props = feature["properties"]
        lines.append(f"| {props['plot_id']} | {geometry['type']} | {props['area_ha']} | {where} |")
    lines += [
        "",
        "<details><summary>GeoJSON for upload</summary>",
        "",
        "```json",
        json.dumps(geojson, indent=2),
        "```",
        "",
        "</details>",
        "",
        "## 5. Risk assessment",
        "",
        summary,
        "",
        "## 6. Statement",
        "",
        STATEMENT,
        "",
        "## 7. Review",
        "",
        f"- **Approved by:** {review.reviewer} on {review.at}",
        f"- **Comment:** {review.comment or 'none'}",
        f"- **Check ID:** {record.check_id}",
        "",
    ]
    return "\n".join(lines)
