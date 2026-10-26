"""Pure geometry checks for EUDR plots.

Every function takes a GeoJSON geometry dict, e.g.
    {"type": "Polygon", "coordinates": [[[lon, lat], [lon, lat], ...]]}
    {"type": "Point", "coordinates": [lon, lat]}

Nothing in here knows about MCP or LLMs, so it is easy to unit test.
"""

from shapely.geometry import shape  # noqa: F401  (you will need these)
from shapely.validation import explain_validity  # noqa: F401

# Above this size, the EUDR requires a polygon instead of a single point.
MAX_POINT_AREA_HA = 4.0


def validate_geometry(geometry: dict) -> list[str]:
    """Return a list of problems with the geometry. Empty list means valid.

    Checks, in this order:
    1. Every coordinate is in range: longitude -180..180, latitude -90..90.
    2. Every polygon ring is closed: its first point equals its last point.
    3. Shapely considers the shape valid (e.g. no self-intersections).

    Write each problem as a short human-readable string, for example
    "latitude 108.1 is out of range (-90..90)" or "ring is not closed".
    """
    # TODO(Hassan): implement the three checks.
    # Hints:
    # - For a Point, geometry["coordinates"] is ONE [lon, lat] pair.
    #   For a Polygon, it is a list of rings, each ring a list of [lon, lat].
    #   Writing a small helper that collects all pairs for either type helps.
    # - Remember the data checks: Shapely quietly closes open rings and
    #   doesn't know lat/lon ranges, so checks 1 and 2 need the RAW coordinates.
    # - For check 3: shape(geometry).is_valid, and explain_validity(...) says why.
    # - Tip: if check 1 or 2 already failed, return early; the Shapely
    #   result on broken input isn't meaningful.
    raise NotImplementedError


def calculate_area_ha(geometry: dict) -> float:
    """Area of a polygon in hectares (1 ha = 10,000 m²). A Point has area 0."""
    # TODO(Hassan): implement.
    # Hints:
    # - shape(geometry).area is in "square degrees", which is meaningless:
    #   a degree of longitude shrinks as you move away from the equator.
    # - Use pyproj's Geod to measure on the real Earth:
    #       from pyproj import Geod
    #       geod = Geod(ellps="WGS84")
    #       area_m2, _perimeter = geod.geometry_area_perimeter(shape(geometry))
    #   area_m2 can come back negative depending on the ring direction: use abs().
    raise NotImplementedError


def check_point_or_polygon(geometry: dict, declared_area_ha: float) -> list[str]:
    """EUDR rule: a plot larger than 4 ha must be a polygon, not a point.

    Return a list of problems (empty list means OK).
    """
    # TODO(Hassan): implement. For points, all you have is declared_area_ha.
    raise NotImplementedError
