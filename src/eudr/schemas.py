"""The shapes of the data going into and coming out of a check.

Pydantic validates data against these classes. The LLM's answer has to fit
them, or it is rejected instead of being passed on as free text.
"""

from typing import Literal

from pydantic import BaseModel


class Shipment(BaseModel):
    """The only shipment fields the LLM sees. Any other field in the file is dropped."""

    shipment_id: str
    plot_ids: list[str]


class PlotCheck(BaseModel):
    """The verdict on one plot."""

    plot_id: str
    status: Literal["approved", "rejected"]
    reason: Literal["ok", "invalid_geometry", "point_too_large", "country_mismatch"]
    explanation: str


class ShipmentCheck(BaseModel):
    """The verdict on a whole shipment."""

    shipment_id: str
    plots: list[PlotCheck]
