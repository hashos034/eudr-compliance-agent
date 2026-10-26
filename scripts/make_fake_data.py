"""Generate the fake test data: 5 suppliers, 20 plots and 2 shipments.

Run with: uv run python scripts/make_fake_data.py

All names, phone numbers and ID numbers are invented. They look realistic on
purpose, so the PII guardrail (Thursday) has something to catch.

GeoJSON coordinates are [longitude, latitude], the reverse of Google Maps.
"""

import json
import math
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# Metres per degree of latitude (roughly constant everywhere on Earth).
M_PER_DEG_LAT = 111_320

SUPPLIERS = [
    {
        "supplier_id": "SUP-001",
        "name": "Hawassa Highland Coffee Union",
        "country": "ET",
        "contact_name": "Meseret Alemayehu Gebre",
        "contact_phone": "+251 911 482 736",
        "contact_national_id": "ET-FIN-4827-3361-09",
    },
    {
        "supplier_id": "SUP-002",
        "name": "Cooperativa Cafetera Valle del Laboyos",
        "country": "CO",
        "contact_name": "Luz Marina Quintero Ospina",
        "contact_phone": "+57 312 584 2210",
        "contact_national_id": "CC 1.083.927.415",
    },
    {
        "supplier_id": "SUP-003",
        "name": "Fazenda Serra Azul Cafés Especiais",
        "country": "BR",
        "contact_name": "Rogério Tavares Junqueira",
        "contact_phone": "+55 35 99814-2307",
        "contact_national_id": "CPF 482.913.756-20",
    },
    {
        "supplier_id": "SUP-004",
        "name": "Dak Lak Robusta Trading Co.",
        "country": "VN",
        "contact_name": "Nguyễn Thị Thu Hằng",
        "contact_phone": "+84 905 318 472",
        "contact_national_id": "CCCD 066184002917",
    },
    {
        "supplier_id": "SUP-005",
        "name": "Cooperativa Agrícola Vale do Jamari",
        "country": "BR",
        "contact_name": "Edinaldo Pereira Bortolini",
        "contact_phone": "+55 69 99237-5841",
        "contact_national_id": "CPF 715.284.390-61",
    },
]

# Each plot: id, supplier, farmer (PII), kind of geometry, centre (lat, lon),
# area in ha, and the outcome we expect from geo-mcp (plus forest-mcp later).
PLOTS = [
    # --- SUP-001, Ethiopia (Sidama / Yirgacheffe) ---
    ("P01", "SUP-001", "Tesfaye Bekele Woldemariam", "+251 912 304 118", "polygon", (6.16, 38.20), 1.2, "ok"),
    ("P02", "SUP-001", "Almaz Girma Haile", "+251 916 775 092", "point", (6.70, 38.48), 0.8, "ok"),
    ("P03", "SUP-001", "Dawit Mekonnen Assefa", "+251 913 640 257", "point", (6.45, 38.35), 5.5, "point_too_large"),
    ("P04", "SUP-001", "Kebede Tolosa Fikru", "+251 918 223 905", "polygon", (-0.42, 36.95), 1.5, "country_mismatch"),  # actually in Kenya
    # --- SUP-002, Colombia (Huila) ---
    ("P05", "SUP-002", "Jhon Fredy Cuéllar Perdomo", "+57 315 220 8841", "polygon", (1.85, -76.05), 2.5, "ok"),
    ("P06", "SUP-002", "María Eugenia Rojas Trujillo", "+57 311 904 3376", "point", (2.20, -75.98), 1.5, "ok"),
    ("P07", "SUP-002", "Edilson Andrés Muñoz Gaitán", "+57 320 615 7702", "bowtie", (1.90, -76.00), 1.0, "invalid_geometry"),
    ("P08", "SUP-002", "Ana Lucía Bermeo Castro", "+57 318 477 1953", "polygon", (-0.93, -78.62), 1.8, "country_mismatch"),  # actually in Ecuador
    # --- SUP-003, Brazil (Sul de Minas) ---
    ("P09", "SUP-003", "José Carlos Ribeiro Mendes", "+55 35 99701-4482", "polygon", (-21.55, -45.43), 6.0, "ok"),  # large, but a polygon, so fine
    ("P10", "SUP-003", "Antônio Marcos Vilela Prado", "+55 35 98852-1907", "point", (-21.40, -45.20), 12.0, "point_too_large"),
    ("P11", "SUP-003", "Cláudia Regina Faria Lopes", "+55 35 99134-6620", "polygon", (-21.25, -45.00), 3.0, "ok"),
    ("P12", "SUP-003", "Sebastião Ferreira da Cunha", "+55 35 99488-0315", "unclosed", (-21.30, -45.10), 2.0, "invalid_geometry"),
    # --- SUP-004, Vietnam (Dak Lak) ---
    ("P13", "SUP-004", "Trần Văn Phúc", "+84 914 207 385", "point", (12.67, 108.05), 1.0, "ok"),
    ("P14", "SUP-004", "Lê Thị Mai Anh", "+84 935 662 019", "polygon", (12.80, 108.20), 2.0, "ok"),
    ("P15", "SUP-004", "Phạm Quốc Bảo", "+84 983 140 576", "swapped", (12.75, 108.10), 1.5, "invalid_geometry"),  # lat/lon swapped
    ("P16", "SUP-004", "Hoàng Minh Tuấn", "+84 906 891 234", "point", (12.60, 108.00), 4.8, "point_too_large"),
    # --- SUP-005, Brazil (Rondônia) ---
    ("P17", "SUP-005", "Valdecir Antônio Schmitz", "+55 69 99312-7046", "polygon", (-11.43, -61.45), 3.5, "ok"),
    ("P18", "SUP-005", "Rosilene Aparecida Kloster", "+55 69 98475-2391", "point", (-11.60, -61.30), 2.0, "ok"),
    # Candidates for forest loss after 2020 (Jaci-Paraná area). geo-mcp should pass
    # them; forest-mcp should flag them. TODO Wednesday: confirm against GFW data.
    ("P19", "SUP-005", "Gilmar José Stedile", "+55 69 99208-6614", "polygon", (-9.55, -64.30), 8.0, "forest_loss"),
    ("P20", "SUP-005", "Marcia Helena Porto Vieira", "+55 69 99671-0538", "polygon", (-9.70, -64.10), 5.0, "forest_loss"),
]


def rectangle(lat: float, lon: float, area_ha: float) -> list[list[float]]:
    """A closed rectangular ring of roughly `area_ha`, 1.5x wider than tall."""
    area_m2 = area_ha * 10_000
    height_m = math.sqrt(area_m2 / 1.5)
    width_m = 1.5 * height_m
    dlat = height_m / 2 / M_PER_DEG_LAT
    dlon = width_m / 2 / (M_PER_DEG_LAT * math.cos(math.radians(lat)))
    ring = [
        [lon - dlon, lat - dlat],
        [lon + dlon, lat - dlat],
        [lon + dlon, lat + dlat],
        [lon - dlon, lat + dlat],
        [lon - dlon, lat - dlat],  # first point repeated: the ring is closed
    ]
    return [[round(x, 6), round(y, 6)] for x, y in ring]


def make_geometry(kind: str, lat: float, lon: float, area_ha: float) -> dict:
    if kind == "point":
        return {"type": "Point", "coordinates": [lon, lat]}
    ring = rectangle(lat, lon, area_ha)
    if kind == "bowtie":
        # Swap two corners so the edges cross: a self-intersecting "bow-tie".
        ring[1], ring[2] = ring[2], ring[1]
    elif kind == "unclosed":
        ring = ring[:-1]  # last point no longer equals the first
    elif kind == "swapped":
        ring = [[y, x] for x, y in ring]  # [lat, lon] instead of [lon, lat]
    return {"type": "Polygon", "coordinates": [ring]}


def main() -> None:
    countries = {s["supplier_id"]: s["country"] for s in SUPPLIERS}

    features = []
    expected = {}
    for plot_id, sup, farmer, phone, kind, (lat, lon), area, outcome in PLOTS:
        features.append(
            {
                "type": "Feature",
                "geometry": make_geometry(kind, lat, lon, area),
                "properties": {
                    "plot_id": plot_id,
                    "supplier_id": sup,
                    "declared_country": countries[sup],
                    "declared_area_ha": area,
                    "farmer_name": farmer,
                    "farmer_phone": phone,
                },
            }
        )
        expected[plot_id] = outcome

    shipments = [
        {
            "shipment_id": "SHP-2026-001",
            "hs_code": "0901.11",  # coffee, not roasted, not decaffeinated
            "quantity_kg": 19_200,
            "production_period": {"start": "2026-03-01", "end": "2026-06-30"},
            "supplier_ids": ["SUP-001", "SUP-002", "SUP-005"],
            "plot_ids": ["P01", "P02", "P03", "P04", "P05", "P07", "P08", "P17", "P19"],
        },
        {
            "shipment_id": "SHP-2026-002",
            "hs_code": "0901.11",
            "quantity_kg": 21_600,
            "production_period": {"start": "2026-05-01", "end": "2026-08-31"},
            "supplier_ids": ["SUP-003", "SUP-004"],
            "plot_ids": ["P09", "P11", "P13", "P14"],
        },
    ]

    def write(path: Path, obj: object) -> None:
        path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
        print("wrote", path.relative_to(DATA.parent))

    write(DATA / "suppliers.json", SUPPLIERS)
    write(DATA / "plots" / "plots.geojson", {"type": "FeatureCollection", "features": features})
    write(DATA / "plots" / "expected_outcomes.json", expected)
    for i, shipment in enumerate(shipments, start=1):
        write(DATA / "shipments" / f"shipment_{i:02d}.json", shipment)


if __name__ == "__main__":
    main()
