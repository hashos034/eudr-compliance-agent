"""Score the agent against plots and suppliers whose right answer we know.

Run it:  uv run python -m evals.run_evals            (one run, about $0.30)
         uv run python -m evals.run_evals --runs 3   (checks consistency)

All 20 plots and 5 suppliers go through the real agent as one shipment. The
scoring is plain code: the LLM never grades itself.

The number that matters most is unsafe approvals: a plot or supplier that should
fail but was passed. A wrong rejection costs a reviewer some time. A wrong
approval puts a non-compliant product on the EU market.
"""

import argparse
import asyncio
import json
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

from eudr.agents.orchestrator import check_shipment
from eudr.schemas import Shipment, ShipmentCheck

EVALS = Path(__file__).resolve().parent
CASES = json.loads((EVALS / "cases.json").read_text())


def eval_shipment() -> Shipment:
    return Shipment(
        shipment_id="EVAL-ALL",
        plot_ids=[case["plot_id"] for case in CASES["plots"]],
        supplier_ids=[case["supplier_id"] for case in CASES["suppliers"]],
    )


def score(check: ShipmentCheck) -> dict:
    """Compare one run with the expected answers."""
    plots = {plot.plot_id: plot for plot in check.plots}
    suppliers = {supplier.supplier_id: supplier for supplier in check.suppliers}
    mistakes = []
    unsafe = 0

    for case in CASES["plots"]:
        got = plots[case["plot_id"]]
        expected = case["expected_reason"]
        if got.reason != expected:
            mistakes.append({"id": case["plot_id"], "expected": expected, "got": got.reason})
        should_pass = expected == "ok"
        if got.status == "approved" and not should_pass:
            unsafe += 1

    for case in CASES["suppliers"]:
        got = suppliers[case["supplier_id"]].legality
        expected = case["expected_legality"]
        if got != expected:
            mistakes.append({"id": case["supplier_id"], "expected": expected, "got": got})
            if got == "documented":
                unsafe += 1

    total = len(CASES["plots"]) + len(CASES["suppliers"])
    plot_mistakes = sum(m["id"].startswith("P") for m in mistakes)
    return {
        "plot_accuracy": round(1 - plot_mistakes / len(CASES["plots"]), 3),
        "supplier_accuracy": round(1 - (len(mistakes) - plot_mistakes) / len(CASES["suppliers"]), 3),
        "overall_accuracy": round(1 - len(mistakes) / total, 3),
        "unsafe_approvals": unsafe,
        "mistakes": mistakes,
    }


async def run_once() -> dict:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "eval_shipment.json"
        path.write_text(eval_shipment().model_dump_json())
        started = time.monotonic()
        check, tracker = await check_shipment(path)
    return {
        **score(check),
        "seconds": round(time.monotonic() - started),
        "cost_usd": round(tracker.total_cost_usd or 0, 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=1)
    args = parser.parse_args()
    load_dotenv()

    runs = []
    for number in range(1, args.runs + 1):
        result = asyncio.run(run_once())
        runs.append(result)
        print(
            f"run {number}: plots {result['plot_accuracy']:.0%}, suppliers {result['supplier_accuracy']:.0%}, "
            f"unsafe approvals {result['unsafe_approvals']}, ${result['cost_usd']:.2f}, {result['seconds']}s"
        )
        for mistake in result["mistakes"]:
            print(f"    {mistake['id']}: expected {mistake['expected']}, got {mistake['got']}")

    report = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "cases": len(CASES["plots"]) + len(CASES["suppliers"]),
        "runs": runs,
    }
    out = EVALS / "results" / "latest.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"saved {out.relative_to(EVALS.parent)}")


if __name__ == "__main__":
    main()
