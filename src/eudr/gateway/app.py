"""HTTP API for the same flow as the CLI.

Run it:  uv run uvicorn eudr.gateway.app:app --reload
Docs:    http://localhost:8000/docs

Every endpoint needs the X-API-Key header to match EUDR_API_KEY. A check takes
about a minute, so POST /checks answers at once with status "running", and the
agents work in the background. Poll GET /checks/{id} until it is awaiting_review.
"""

import os
import secrets

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Security
from fastapi.responses import PlainTextResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from eudr.review import service
from eudr.review.service import ReviewError
from eudr.review.store import CheckRecord, CheckStore
from eudr.dds import load_plot_geometries
from eudr.supplier_data import load_suppliers

load_dotenv()

app = FastAPI(title="EUDR compliance agent", version="1.0.0")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_store() -> CheckStore:
    return CheckStore()


def require_api_key(key: str | None = Security(api_key_header)) -> None:
    expected = os.environ.get("EUDR_API_KEY")
    if not expected:
        raise HTTPException(503, "EUDR_API_KEY is not set on the server.")
    # compare_digest takes the same time for any wrong key, so timing gives nothing away.
    if not key or not secrets.compare_digest(key, expected):
        raise HTTPException(401, "Missing or wrong API key.")


class ProductionPeriod(BaseModel):
    start: str
    end: str


class ShipmentIn(BaseModel):
    shipment_id: str = Field(pattern=r"^[A-Za-z0-9-]{1,40}$")
    supplier_ids: list[str] = Field(min_length=1)
    plot_ids: list[str] = Field(min_length=1)
    hs_code: str | None = None
    quantity_kg: float | None = None
    production_period: ProductionPeriod | None = None


class Approval(BaseModel):
    reviewer: str
    comment: str = ""


class Rejection(BaseModel):
    reviewer: str
    reason: str


class CheckSummary(BaseModel):
    check_id: str
    shipment_id: str
    status: str


async def run_in_background(store: CheckStore, record: CheckRecord) -> None:
    try:
        await service.run(store, record)
    except Exception:
        pass  # service.run already saved the failure on the record


@app.post("/checks", status_code=202, response_model=CheckSummary, dependencies=[Depends(require_api_key)])
def start_check(shipment: ShipmentIn, background: BackgroundTasks, store: CheckStore = Depends(get_store)):
    unknown = (set(shipment.supplier_ids) - set(load_suppliers())) | (set(shipment.plot_ids) - set(load_plot_geometries()))
    if unknown:
        raise HTTPException(422, f"Unknown supplier or plot IDs: {sorted(unknown)}")
    record = store.create(shipment.model_dump(exclude_none=True))
    background.add_task(run_in_background, store, record)
    return CheckSummary(check_id=record.check_id, shipment_id=shipment.shipment_id, status=record.status)


@app.get("/checks", response_model=list[CheckSummary], dependencies=[Depends(require_api_key)])
def list_checks(store: CheckStore = Depends(get_store)):
    return [
        CheckSummary(check_id=r.check_id, shipment_id=r.shipment["shipment_id"], status=r.status)
        for r in store.list()
    ]


@app.get("/checks/{check_id}", response_model=CheckRecord, dependencies=[Depends(require_api_key)])
def get_check(check_id: str, store: CheckStore = Depends(get_store)):
    """The check with real names restored, for the reviewer."""
    try:
        return store.view(check_id)
    except KeyError:
        raise HTTPException(404, "No such check.")


@app.post("/checks/{check_id}/approve", response_model=CheckSummary, dependencies=[Depends(require_api_key)])
async def approve_check(check_id: str, approval: Approval, store: CheckStore = Depends(get_store)):
    try:
        record = await service.approve(store, check_id, approval.reviewer, approval.comment)
    except KeyError:
        raise HTTPException(404, "No such check.")
    except ReviewError as error:
        raise HTTPException(409, str(error))
    return CheckSummary(check_id=check_id, shipment_id=record.shipment["shipment_id"], status=record.status)


@app.post("/checks/{check_id}/reject", response_model=CheckSummary, dependencies=[Depends(require_api_key)])
def reject_check(check_id: str, rejection: Rejection, store: CheckStore = Depends(get_store)):
    try:
        record = service.reject(store, check_id, rejection.reviewer, rejection.reason)
    except KeyError:
        raise HTTPException(404, "No such check.")
    except ReviewError as error:
        raise HTTPException(409, str(error))
    return CheckSummary(check_id=check_id, shipment_id=record.shipment["shipment_id"], status=record.status)


@app.get("/checks/{check_id}/dds", response_class=PlainTextResponse, dependencies=[Depends(require_api_key)])
def get_dds(check_id: str, store: CheckStore = Depends(get_store)):
    try:
        path = store.dds_path(check_id)
    except KeyError:
        raise HTTPException(404, "No such check.")
    if not path.exists():
        raise HTTPException(404, "No DDS draft. A check gets one only after approval.")
    return PlainTextResponse(path.read_text(), media_type="text/markdown")


@app.get("/health")
def health():
    return {"status": "ok"}
