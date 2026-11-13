"""Tests for the eval scoring itself, with made-up runs. No LLM calls."""

from evals.run_evals import CASES, eval_shipment, score
from eudr.schemas import PlotCheck, ShipmentCheck, SupplierCheck


def perfect_run() -> ShipmentCheck:
    plots = [
        PlotCheck(
            plot_id=case["plot_id"],
            status="approved" if case["expected_reason"] == "ok" else "rejected",
            reason=case["expected_reason"],
            explanation=".",
        )
        for case in CASES["plots"]
    ]
    suppliers = [
        SupplierCheck(supplier_id=case["supplier_id"], legality=case["expected_legality"], explanation=".")
        for case in CASES["suppliers"]
    ]
    return ShipmentCheck(shipment_id="EVAL-ALL", plots=plots, suppliers=suppliers)


def test_cases_cover_every_plot_and_supplier():
    shipment = eval_shipment()
    assert len(shipment.plot_ids) == 20
    assert len(shipment.supplier_ids) == 5


def test_perfect_run_scores_full_marks():
    result = score(perfect_run())
    assert result["overall_accuracy"] == 1
    assert result["unsafe_approvals"] == 0


def test_approving_a_deforested_plot_counts_as_unsafe():
    run = perfect_run()
    p19 = next(plot for plot in run.plots if plot.plot_id == "P19")
    p19.status, p19.reason = "approved", "ok"
    result = score(run)
    assert result["unsafe_approvals"] == 1
    assert result["mistakes"] == [{"id": "P19", "expected": "forest_loss", "got": "ok"}]


def test_wrong_rejection_is_a_mistake_but_not_unsafe():
    run = perfect_run()
    p01 = next(plot for plot in run.plots if plot.plot_id == "P01")
    p01.status, p01.reason = "rejected", "forest_data_missing"
    result = score(run)
    assert result["unsafe_approvals"] == 0
    assert result["plot_accuracy"] == 0.95
