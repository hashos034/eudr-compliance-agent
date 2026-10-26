"""Pure geometry checks for EUDR plots.

Every function takes a GeoJSON geometry dict, e.g.
    {"type": "Polygon", "coordinates": [[[lon, lat], [lon, lat], ...]]}
    {"type": "Point", "coordinates": [lon, lat]}

Nothing in here knows about MCP or LLMs, so it is easy to unit test.
"""

from pyproj import Geod
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from shapely.validation import explain_validity

# Above this size, the EUDR requires a polygon instead of a single point.
MAX_POINT_AREA_HA = 4.0

# The WGS84 ellipsoid: the model of the Earth's shape that GPS uses.
GEOD = Geod(ellps="WGS84")


def _rings(geometry: dict) -> list[list[list[float]]]:
    """The coordinate lists of a geometry: one 'ring' for a Point, all rings for a Polygon."""
    if geometry["type"] == "Point":
        return [[geometry["coordinates"]]]
    return geometry["coordinates"]


def validate_geometry(geometry: dict) -> list[str]:
    """Return a list of problems with the geometry. Empty list means valid.

    Checks, in this order:
    1. Every coordinate is in range: longitude -180..180, latitude -90..90.
    2. Every polygon ring is closed: its first point equals its last point.
    3. Shapely considers the shape valid (e.g. no self-intersections).
    """
    errors = []

    # 1. Range check on the raw numbers. Shapely doesn't know what a latitude is.
    #    Report only the first bad point per ring, to keep the message short.
    for ring in _rings(geometry):
        for lon, lat in ring:
            if not -180 <= lon <= 180:
                errors.append(f"longitude {lon} is out of range (-180..180)")
                break
            if not -90 <= lat <= 90:
                errors.append(f"latitude {lat} is out of range (-90..90)")
                break

    # 2. Closed check on the raw ring. Shapely would silently close it for us.
    if geometry["type"] == "Polygon":
        for ring in geometry["coordinates"]:
            if ring[0] != ring[-1]:
                errors.append("polygon ring is not closed (first point != last point)")

    # 3. Only ask Shapely once the raw data makes sense.
    if errors:
        return errors
    shp = shape(geometry)
    if not shp.is_valid:
        errors.append(f"invalid shape: {explain_validity(shp)}")
    return errors


def calculate_area_ha(geometry: dict) -> float:
    """Area of a polygon in hectares (1 ha = 10,000 m²). A Point has area 0."""
    if geometry["type"] == "Point":
        return 0.0
    # Measure on the curved Earth, not in "square degrees".
    area_m2, _perimeter = GEOD.geometry_area_perimeter(shape(geometry))
    return abs(area_m2) / 10_000


def find_country(geometry: dict, countries: list[tuple[str, BaseGeometry]]) -> str | None:
    """Return the ISO code of the country the plot lies in, or None if it's in none.

    `countries` is a list of (iso_code, border_shape) pairs, e.g. ("ET", <MultiPolygon>).
    """
    # TODO(Hassan): implement. About 5 lines.
    # Hints:
    # - Turn the plot into ONE point you can test: shape(geometry).representative_point()
    #   gives a point guaranteed to lie inside the shape (works for Points too).
    # - Loop over the (code, border) pairs and return the code of the first
    #   border that .contains(...) that point.
    # - If no border contains it (e.g. in the ocean), return None.
    raise NotImplementedError


def check_point_or_polygon(geometry: dict, declared_area_ha: float) -> list[str]:
    """EUDR rule: a plot larger than 4 ha must be a polygon, not a point.

    Return a list of problems (empty list means OK).
    """
    if geometry["type"] == "Point" and declared_area_ha > MAX_POINT_AREA_HA:
        return [
            f"plot is {declared_area_ha} ha but given as a point; "
            f"plots over {MAX_POINT_AREA_HA} ha need a polygon"
        ]
    return []
