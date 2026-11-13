"""The steps of a check, from start to DDS, shared by the CLI and the API.

    start  ->  running  ->  awaiting_review  ->  approved (DDS draft written)
                       \\->  failed           \\->  rejected

The human decision is a hard gate in code. No DDS is drafted before approval,
and a check with blocking issues cannot be approved at all, because the EUDR
forbids placing a product on the market unless its risk is negligible.
"""

from collections.abc import Awaitable, Callable

from eudr import dds
from eudr.agents.orchestrator import run_check
from eudr.review.store import CheckRecord, CheckStore, Review, now
from eudr.risk import assess
from eudr.schemas import Shipment
from eudr.supplier_data import load_supplier_countries

Summarizer = Callable[[CheckRecord], Awaitable[tuple[str, float]]]


class ReviewError(Exception):
    """The requested review step isn't allowed in the check's current state."""


async def run(store: CheckStore, record: CheckRecord) -> CheckRecord:
    """Run the agents for a check created with store.create, and save the result."""
    try:
        shipment = Shipment.model_validate(record.shipment)
        check, pseudonymizer, tracker = await run_check(shipment)
    except Exception as error:  # Saved, so the reviewer sees why a check failed.
        record.status, record.error = "failed", str(error)
        store.save(record)
        raise
    # The lookup table goes first, so a saved check can always be restored.
    store.save_lookup_table(record.check_id, pseudonymizer.lookup_table())
    record.result = check
    record.risk = assess(shipment, check, load_supplier_countries())
    record.cost_usd = tracker.total_cost_usd
    record.status = "awaiting_review"
    store.save(record)
    return record


async def approve(
    store: CheckStore,
    check_id: str,
    reviewer: str,
    comment: str = "",
    summarize: Summarizer | None = None,
) -> CheckRecord:
    record = store.load(check_id)
    if record.status != "awaiting_review":
        raise ReviewError(f"Check {check_id} is {record.status}, not awaiting review.")
    if not record.risk.can_draft_dds:
        raise ReviewError(
            "This check has blocking issues, so the risk is not negligible and it can't be approved: "
            + "; ".join(record.risk.blocking_issues)
        )
    if not reviewer.strip():
        raise ReviewError("A reviewer name is required.")

    record.review = Review(decision="approved", reviewer=reviewer, comment=comment, at=now())
    summarize = summarize or dds.write_summary  # looked up now, so tests can swap it
    summary, cost = await summarize(record)  # pseudonymized record in, so no names reach the LLM
    draft = dds.render(record, store.restore(check_id, summary))
    store.dds_path(check_id).write_text(draft)
    record.status = "approved"
    record.cost_usd = (record.cost_usd or 0) + cost
    store.save(record)
    return record


def reject(store: CheckStore, check_id: str, reviewer: str, comment: str) -> CheckRecord:
    record = store.load(check_id)
    if record.status != "awaiting_review":
        raise ReviewError(f"Check {check_id} is {record.status}, not awaiting review.")
    if not reviewer.strip() or not comment.strip():
        raise ReviewError("A reviewer name and a reason are required to reject a check.")
    record.review = Review(decision="rejected", reviewer=reviewer, comment=comment, at=now())
    record.status = "rejected"
    store.save(record)
    return record
