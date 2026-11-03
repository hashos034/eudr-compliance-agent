import pytest
from pydantic import ValidationError

from eudr.schemas import PlotCheck, Shipment


def make_plot(**changes) -> dict:
    fields = {
        "plot_id": "P07",
        "status": "rejected",
        "reason": "invalid_geometry",
        "explanation": "The polygon's ring is not closed.",
    }
    return fields | changes


def test_accepts_a_valid_verdict():
    assert PlotCheck(**make_plot()).status == "rejected"


@pytest.mark.parametrize("bad", [{"status": "maybe"}, {"reason": "looks_odd"}])
def test_rejects_values_outside_the_allowed_list(bad):
    with pytest.raises(ValidationError):
        PlotCheck(**make_plot(**bad))


def test_requires_an_explanation():
    fields = make_plot()
    del fields["explanation"]
    with pytest.raises(ValidationError):
        PlotCheck(**fields)


def test_shipment_drops_fields_the_llm_should_not_see():
    shipment = Shipment(shipment_id="S1", plot_ids=["P01"], supplier_ids=["SUP-001"])
    assert set(shipment.model_dump()) == {"shipment_id", "plot_ids"}
