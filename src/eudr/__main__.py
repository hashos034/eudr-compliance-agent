"""Command line: uv run python -m eudr check data/shipments/shipment_01.json"""

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

from eudr.agents.orchestrator import check_shipment
from eudr.risk import assess
from eudr.schemas import Shipment
from eudr.supplier_data import load_supplier_countries


def main() -> int:
    parser = argparse.ArgumentParser(prog="eudr")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="Check a shipment file")
    check.add_argument("shipment", type=Path)
    args = parser.parse_args()

    load_dotenv()
    try:
        result, tracker = asyncio.run(check_shipment(args.shipment))
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Shipment {result.shipment_id}\n")
    for plot in result.plots:
        print(f"  {plot.plot_id}  {plot.status:<9} {plot.reason:<20} {plot.explanation}")

    print("\nProof of legality (from supplier notes):\n")
    for supplier in result.suppliers:
        print(f"  {supplier.supplier_id}  {supplier.legality:<11} {supplier.explanation}")

    shipment = Shipment.model_validate_json(args.shipment.read_text())
    risk = assess(shipment, result, load_supplier_countries())
    print("\nRisk (calculated in code):\n")
    print(f"  Country risk: {risk.country_risk}")
    if risk.can_draft_dds:
        print("  Negligible risk: a DDS can be drafted after human review.")
    for issue in risk.blocking_issues:
        print(f"  BLOCKED  {issue}")

    cost = tracker.summary()
    print(f"\nEstimated cost: ${cost['estimated_cost_usd'] or 0:.4f}")
    for name, usage in cost["agents"].items():
        print(f"  {name}: {usage['steps']} steps, {usage['input_tokens']} input tokens")
    return 0


if __name__ == "__main__":
    sys.exit(main())
