"""The human review gate and the DDS draft. A fake summarizer stands in for the LLM."""

import asyncio
import json
import stat

import pytest

from eudr import dds
from eudr.review import service
from eudr.review.service import ReviewError
from eudr.review.store import CheckStore
from eudr.risk import assess
from eudr.schemas import PlotCheck, Shipment, ShipmentCheck, SupplierCheck

SHIPMENT = json.loads(open("data/shipments/shipment_03.json").read())
LOOKUP = {"<PERSON_1>": "Rogério Tavares Junqueira"}


def make_check(legality: str = "documented") -> ShipmentCheck:
    return ShipmentCheck(
        shipment_id=SHIPMENT["shipment_id"],
        plots=[
            PlotCheck(plot_id=p, status="approved", reason="ok", explanation="Passed all checks.")
            for p in SHIPMENT["plot_ids"]
        ],
        suppliers=[
            SupplierCheck(supplier_id="SUP-001", legality="documented", explanation="Titles on file."),
            SupplierCheck(supplier_id="SUP-003", legality=legality, explanation="<PERSON_1> sent the reports."),
        ],
    )


def awaiting_review(tmp_path, legality: str = "documented") -> tuple[CheckStore, str]:
    """A check as it looks after the agents ran: pseudonymized, with its lookup table apart."""
    store = CheckStore(tmp_path)
    record = store.create(SHIPMENT)
    record.result = make_check(legality)
    record.risk = assess(Shipment.model_validate(SHIPMENT), record.result, {"SUP-001": "ET", "SUP-003": "BR"})
    record.status = "awaiting_review"
    store.save(record)
    store.save_lookup_table(record.check_id, LOOKUP)
    return store, record.check_id


class FakeSummarizer:
    def __init__(self):
        self.seen = None

    async def __call__(self, record):
        self.seen = dds.summary_input(record)
        return "All plots passed. <PERSON_1> supplied the documents.", 0.01


def test_saved_check_is_pseudonymized_and_the_lookup_table_is_private(tmp_path):
    store, check_id = awaiting_review(tmp_path)
    saved = (tmp_path / check_id / "check.json").read_text()
    assert "Rogério" not in saved
    assert "<PERSON_1>" in saved
    mode = stat.S_IMODE((tmp_path / check_id / "pii_map.json").stat().st_mode)
    assert mode == 0o600


def test_reviewer_view_restores_names(tmp_path):
    store, check_id = awaiting_review(tmp_path)
    view = store.view(check_id)
    assert view.result.suppliers[1].explanation == "Rogério Tavares Junqueira sent the reports."


def test_approval_writes_a_dds_and_the_llm_sees_no_personal_data_or_coordinates(tmp_path):
    store, check_id = awaiting_review(tmp_path)
    summarizer = FakeSummarizer()
    record = asyncio.run(service.approve(store, check_id, "A. Reviewer", "Looks fine", summarize=summarizer))

    assert record.status == "approved"
    assert "Rogério" not in summarizer.seen
    assert "coordinates" not in summarizer.seen

    draft = store.dds_path(check_id).read_text()
    assert "SHP-2026-003" in draft
    assert "0901.11" in draft
    assert "Rogério Tavares Junqueira supplied the documents." in draft  # restored for the human
    assert '"coordinates"' in draft  # geolocation added by code, after the LLM step
    assert "A. Reviewer" in draft
    for plot_id in SHIPMENT["plot_ids"]:
        assert f"| {plot_id} |" in draft


def test_no_dds_before_approval(tmp_path):
    store, check_id = awaiting_review(tmp_path)
    assert not store.dds_path(check_id).exists()


def test_a_blocked_check_cannot_be_approved(tmp_path):
    store, check_id = awaiting_review(tmp_path, legality="gap")
    with pytest.raises(ReviewError, match="not negligible"):
        asyncio.run(service.approve(store, check_id, "A. Reviewer", summarize=FakeSummarizer()))
    assert not store.dds_path(check_id).exists()


def test_reject_needs_a_reason_and_ends_the_check(tmp_path):
    store, check_id = awaiting_review(tmp_path)
    with pytest.raises(ReviewError):
        service.reject(store, check_id, "A. Reviewer", "")
    service.reject(store, check_id, "A. Reviewer", "Supplier under investigation")
    with pytest.raises(ReviewError, match="rejected"):
        asyncio.run(service.approve(store, check_id, "A. Reviewer", summarize=FakeSummarizer()))


def test_check_ids_cannot_point_outside_the_store(tmp_path):
    with pytest.raises(KeyError):
        CheckStore(tmp_path).load("../../etc")
