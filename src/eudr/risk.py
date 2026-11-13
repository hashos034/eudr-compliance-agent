"""Turns the agents' verdicts into a risk decision. Plain code, no LLM.

The EUDR only lets a product onto the EU market if the risk that it is linked to
deforestation or illegal production is "negligible". This file applies that rule:
one failed plot or one missing legality document blocks the whole shipment.

This replaces the planned regulation agent. A country's risk class is a fact from
an EU list, not a judgment, so a lookup table is safer than asking an LLM.
"""

from typing import Literal

from pydantic import BaseModel

from eudr.schemas import Shipment, ShipmentCheck

CountryRisk = Literal["low", "standard", "high"]

# Commission Implementing Regulation (EU) 2025/1093 classifies every country.
# Only the coffee origins in this project are listed. The four "high" countries
# are the full high-risk list, so anything else not listed is standard.
COUNTRY_RISK: dict[str, CountryRisk] = {
    "BR": "standard",
    "CO": "standard",
    "ET": "standard",
    "VN": "standard",
    "BY": "high",
    "KP": "high",
    "MM": "high",
    "RU": "high",
}

# Due diligence a country's class requires (EUDR Articles 10, 11 and 13).
DUE_DILIGENCE: dict[CountryRisk, str] = {
    "low": "simplified due diligence (Article 13)",
    "standard": "full due diligence: information, risk assessment and mitigation (Articles 9 to 11)",
    "high": "full due diligence, with enhanced scrutiny by the authorities (Article 16)",
}


class RiskAssessment(BaseModel):
    shipment_id: str
    plot_risk: dict[str, Literal["negligible", "non_negligible"]]
    country_risk: dict[str, CountryRisk]
    blocking_issues: list[str]
    can_draft_dds: bool


def country_risk(country: str) -> CountryRisk:
    return COUNTRY_RISK.get(country, "standard")


def assess(shipment: Shipment, check: ShipmentCheck, supplier_countries: dict[str, str]) -> RiskAssessment:
    plot_risk = {
        plot.plot_id: "negligible" if plot.status == "approved" else "non_negligible" for plot in check.plots
    }
    issues = [f"Plot {plot.plot_id} failed: {plot.reason}" for plot in check.plots if plot.status != "approved"]
    issues += [
        f"Supplier {supplier.supplier_id} has no proof of legality on file"
        for supplier in check.suppliers
        if supplier.legality != "documented"
    ]
    countries = sorted({supplier_countries[s] for s in shipment.supplier_ids})
    return RiskAssessment(
        shipment_id=shipment.shipment_id,
        plot_risk=plot_risk,
        country_risk={country: country_risk(country) for country in countries},
        blocking_issues=issues,
        can_draft_dds=not issues,
    )
