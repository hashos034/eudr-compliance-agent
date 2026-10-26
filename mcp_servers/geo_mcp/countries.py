"""Load country borders (Natural Earth 1:50m, public domain) as Shapely shapes."""

import json
from functools import cache
from pathlib import Path

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

COUNTRIES_FILE = Path(__file__).resolve().parent / "data" / "countries.geojson"


@cache
def load_countries() -> list[tuple[str, BaseGeometry]]:
    """Return [(ISO 3166 alpha-2 code, border shape), ...], e.g. [("ET", <MultiPolygon>), ...]."""
    collection = json.loads(COUNTRIES_FILE.read_text())
    return [(f["properties"]["iso_a2"], shape(f["geometry"])) for f in collection["features"]]
