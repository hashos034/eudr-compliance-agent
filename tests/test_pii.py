"""Proves personal data doesn't reach the LLM. None of these call the LLM or cost anything."""

import asyncio
import re
from pathlib import Path

import pytest

from eudr.agents import orchestrator
from eudr.cost_tracker import CostTracker
from eudr.guardrails.pii import Pseudonymizer
from eudr.schemas import PlotCheck, ShipmentCheck, SupplierCheck
from eudr.supplier_data import load_known_pii, load_suppliers

ROOT = Path(__file__).resolve().parents[1]
SHIPMENTS = sorted((ROOT / "data" / "shipments").glob("*.json"))
ALL_NOTES = [supplier["notes"] for supplier in load_suppliers().values()]

# Values written into the notes, including ones the structured data doesn't hold.
PLANTED = [
    "Meseret Alemayehu Gebre",
    "+251 911 482 736",
    "Edilson Andrés Muñoz Gaitán",
    "Luz Marina Quintero Ospina",
    "CC 1.083.927.415",
    "Rogério Tavares Junqueira",
    "Nguyễn Thị Thu Hằng",
    "+84 905 318 472",
    "Gilmar José Stedile",
    "Carlos Mendoza",
    "carlos.mendoza@example.com",
]


@pytest.fixture
def pseudonymizer() -> Pseudonymizer:
    return Pseudonymizer(load_known_pii())


@pytest.mark.parametrize("value", PLANTED)
def test_planted_personal_data_is_removed(pseudonymizer, value):
    assert any(value in note for note in ALL_NOTES), "the planted value should be in the data"
    cleaned = [pseudonymizer.pseudonymize(note) for note in ALL_NOTES]
    assert not any(value in note for note in cleaned)


def test_the_model_catches_a_name_that_is_in_no_list():
    # Empty known_pii, so only the NLP model can find this.
    result = Pseudonymizer({}).pseudonymize("Our field agent Carlos Mendoza visited the farm.")
    assert "Carlos Mendoza" not in result
    assert "<PERSON_1>" in result


def test_national_id_formats_are_caught_without_a_known_list():
    for national_id in ["ET-FIN-1111-2222-33", "CC 1.234.567.890", "CPF 111.222.333-44", "CCCD 012345678901"]:
        assert national_id not in Pseudonymizer({}).pseudonymize(f"The ID is {national_id}.")


def test_compliance_signal_survives(pseudonymizer):
    note = "Land title for Edilson Andrés Muñoz Gaitán's farm is still pending at the municipality."
    result = pseudonymizer.pseudonymize(note)
    assert "Land title" in result and "still pending" in result


def test_same_person_gets_the_same_token(pseudonymizer):
    first = pseudonymizer.pseudonymize("Carlos Mendoza called.")
    second = pseudonymizer.pseudonymize("We phoned Carlos Mendoza back.")
    token = re.search(r"<PERSON_\d+>", first).group()
    assert token in second


def test_restore_brings_back_the_original(pseudonymizer):
    for note in ALL_NOTES:
        assert pseudonymizer.restore(pseudonymizer.pseudonymize(note)) == note


def test_final_check_stops_a_leak_without_repeating_the_value(pseudonymizer):
    with pytest.raises(RuntimeError) as error:
        pseudonymizer.assert_clean("Please call Almaz Girma Haile.")
    assert "Almaz" not in str(error.value)


def test_restored_output_has_real_names(pseudonymizer):
    token = pseudonymizer.pseudonymize("Carlos Mendoza").strip()
    plot = PlotCheck(plot_id="P1", status="approved", reason="ok", explanation="Fine.")
    supplier = SupplierCheck(supplier_id="S", legality="gap", explanation=f"{token} reports a gap.")
    check = ShipmentCheck(shipment_id="X", plots=[plot], suppliers=[supplier])
    restored = orchestrator.restore_personal_data(check, pseudonymizer)
    assert restored.suppliers[0].explanation == "Carlos Mendoza reports a gap."


@pytest.mark.parametrize("shipment_file", SHIPMENTS, ids=lambda path: path.stem)
def test_nothing_sent_to_the_llm_contains_personal_data_or_coordinates(monkeypatch, shipment_file):
    """Runs the real check up to the LLM call, and inspects everything that would be sent."""
    captured = {}

    async def fake_query(*, prompt, options):
        captured["sent"] = "\n".join(
            [prompt, options.system_prompt, *(agent.prompt for agent in options.agents.values())]
        )
        return
        yield

    monkeypatch.setattr(orchestrator, "query", fake_query)
    monkeypatch.setattr(CostTracker, "save", lambda self: None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")

    with pytest.raises(RuntimeError, match="without a valid verdict"):
        asyncio.run(orchestrator.check_shipment(shipment_file))

    sent = captured["sent"]
    known = [value for values in load_known_pii().values() for value in values]
    assert not [value for value in known + PLANTED if value in sent]
    assert not re.search(r"-?\d{1,3}\.\d{4,}", sent), "looks like a coordinate"
    assert "<PERSON_" in sent, "the notes should have been sent, pseudonymized"
