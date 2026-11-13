from eudr.risk import assess, country_risk
from eudr.schemas import PlotCheck, Shipment, ShipmentCheck, SupplierCheck

SHIPMENT = Shipment(shipment_id="S1", supplier_ids=["SUP-1"], plot_ids=["P1", "P2"])
COUNTRIES = {"SUP-1": "BR"}


def check(p2_status="approved", p2_reason="ok", legality="documented") -> ShipmentCheck:
    return ShipmentCheck(
        shipment_id="S1",
        plots=[
            PlotCheck(plot_id="P1", status="approved", reason="ok", explanation="."),
            PlotCheck(plot_id="P2", status=p2_status, reason=p2_reason, explanation="."),
        ],
        suppliers=[SupplierCheck(supplier_id="SUP-1", legality=legality, explanation=".")],
    )


def test_clean_shipment_can_go_to_a_dds():
    risk = assess(SHIPMENT, check(), COUNTRIES)
    assert risk.can_draft_dds
    assert risk.blocking_issues == []
    assert risk.country_risk == {"BR": "standard"}


def test_one_failed_plot_blocks_the_shipment():
    risk = assess(SHIPMENT, check("rejected", "forest_loss"), COUNTRIES)
    assert not risk.can_draft_dds
    assert risk.plot_risk == {"P1": "negligible", "P2": "non_negligible"}
    assert risk.blocking_issues == ["Plot P2 failed: forest_loss"]


def test_a_legality_gap_blocks_the_shipment():
    risk = assess(SHIPMENT, check(legality="gap"), COUNTRIES)
    assert not risk.can_draft_dds
    assert "SUP-1" in risk.blocking_issues[0]


def test_unlisted_country_defaults_to_standard_and_high_risk_is_known():
    assert country_risk("XX") == "standard"
    assert country_risk("MM") == "high"
