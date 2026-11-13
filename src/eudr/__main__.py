"""Command line.

    uv run python -m eudr check data/shipments/shipment_03.json
    uv run python -m eudr list
    uv run python -m eudr show <check_id>
    uv run python -m eudr approve <check_id> --reviewer "Your Name"
    uv run python -m eudr reject <check_id> --reviewer "Your Name" --reason "..."
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from eudr.review import service
from eudr.review.service import ReviewError
from eudr.review.store import CheckRecord, CheckStore


def print_check(record: CheckRecord) -> None:
    print(f"Check {record.check_id}  shipment {record.shipment['shipment_id']}  status: {record.status}\n")
    if record.error:
        print(f"  Error: {record.error}")
    if not record.result:
        return
    for plot in record.result.plots:
        print(f"  {plot.plot_id}  {plot.status:<9} {plot.reason:<20} {plot.explanation}")

    print("\nProof of legality (from supplier notes):\n")
    for supplier in record.result.suppliers:
        print(f"  {supplier.supplier_id}  {supplier.legality:<11} {supplier.explanation}")

    risk = record.risk
    print("\nRisk (calculated in code):\n")
    print(f"  Country risk: {', '.join(f'{c} {r}' for c, r in risk.country_risk.items())}")
    if risk.can_draft_dds:
        print("  Negligible risk. A reviewer can approve this check to draft the DDS.")
    for issue in risk.blocking_issues:
        print(f"  BLOCKED  {issue}")
    if record.review:
        review = record.review
        print(f"\n{review.decision.capitalize()} by {review.reviewer} on {review.at}. {review.comment}")
    if record.cost_usd is not None:
        print(f"\nEstimated LLM cost so far: ${record.cost_usd:.4f}")


def main() -> int:
    parser = argparse.ArgumentParser(prog="eudr")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="Check a shipment file and queue it for review")
    check.add_argument("shipment", type=Path)
    commands.add_parser("list", help="List checks and their status")
    show = commands.add_parser("show", help="Show a check, with names restored for the reviewer")
    show.add_argument("check_id")
    approve = commands.add_parser("approve", help="Approve a check and draft its DDS")
    approve.add_argument("check_id")
    approve.add_argument("--reviewer", required=True)
    approve.add_argument("--comment", default="")
    reject = commands.add_parser("reject", help="Reject a check")
    reject.add_argument("check_id")
    reject.add_argument("--reviewer", required=True)
    reject.add_argument("--reason", required=True)
    args = parser.parse_args()

    load_dotenv()
    store = CheckStore()
    try:
        if args.command == "check":
            record = store.create(json.loads(args.shipment.read_text()))
            asyncio.run(service.run(store, record))
            print_check(store.view(record.check_id))
            print(f"\nNext: review it, then `eudr approve {record.check_id} --reviewer ...` or `eudr reject ...`.")
        elif args.command == "list":
            for record in store.list():
                print(f"{record.check_id}  {record.shipment['shipment_id']}  {record.status}")
        elif args.command == "show":
            print_check(store.view(args.check_id))
        elif args.command == "approve":
            asyncio.run(service.approve(store, args.check_id, args.reviewer, args.comment))
            print(f"Approved. DDS draft written to {store.dds_path(args.check_id)}")
        elif args.command == "reject":
            service.reject(store, args.check_id, args.reviewer, args.reason)
            print("Rejected. No DDS will be drafted.")
    except KeyError as error:
        print(f"Error: no check with ID {error}", file=sys.stderr)
        return 1
    except (RuntimeError, ReviewError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
