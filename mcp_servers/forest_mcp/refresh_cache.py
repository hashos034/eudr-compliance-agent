"""Measure tree cover loss for every plot and save the results as the local cache.

Run it:  uv run python -m mcp_servers.forest_mcp.refresh_cache

It reads the University of Maryland's public Global Forest Change rasters, the
data behind Global Forest Watch's tree cover loss layer. Only the matching parts of
a file are downloaded, so no plot shape is uploaded anywhere.

The cache and this script's output hold results only, never coordinates.
"""

import json
import math
from datetime import date
from pathlib import Path

import rasterio
from rasterio.mask import mask
from shapely import affinity
from shapely.geometry import Point, mapping, shape

from mcp_servers.forest_mcp.plots import geometry_hash, load_plots
from mcp_servers.forest_mcp.server import DEFAULT_CACHE_FILE

DATASET = "GFC-2025-v1.13"
RASTER_URL = f"https://storage.googleapis.com/earthenginepartners-hansen/{DATASET}/Hansen_{DATASET}_{{layer}}_{{tile}}.tif"

# The EUDR defines forest as more than 10% canopy cover. The canopy layer is from 2000.
MIN_CANOPY_PCT = 10

M_PER_DEG_LAT = 111_320
NOT_IN_PLOT = 255


def is_usable(geometry: dict) -> bool:
    """Whether the shape can be measured: coordinates in range, rings closed, valid shape."""
    rings = [[geometry["coordinates"]]] if geometry["type"] == "Point" else geometry["coordinates"]
    for ring in rings:
        if any(not (-180 <= lon <= 180 and -90 <= lat <= 90) for lon, lat in ring):
            return False
        if geometry["type"] == "Polygon" and ring[0] != ring[-1]:
            return False
    return shape(geometry).is_valid


def area_to_measure(geometry: dict, declared_area_ha: float):
    """The shape to measure. A point becomes a circle of the plot's declared area."""
    shp = shape(geometry)
    if not isinstance(shp, Point):
        return shp
    radius_deg = math.sqrt(declared_area_ha * 10_000 / math.pi) / M_PER_DEG_LAT
    return affinity.scale(shp.buffer(radius_deg), xfact=1 / math.cos(math.radians(shp.y)))


def tile_name(lon: float, lat: float) -> str:
    """The name of the 10x10 degree file holding a location, from its top-left corner."""
    top = math.ceil(lat / 10) * 10
    left = math.floor(lon / 10) * 10
    return f"{abs(top):02d}{'N' if top >= 0 else 'S'}_{abs(left):03d}{'E' if left >= 0 else 'W'}"


def tile_of(shp) -> str:
    """The file holding the whole shape. Clipping at a file's edge would undercount loss."""
    west, south, east, north = shp.bounds
    tile = tile_name(west, north)
    if tile != tile_name(east, south):
        raise RuntimeError("A plot crosses two raster files, which this script doesn't support.")
    return tile


def loss_per_year(loss_years, canopy, pixel_ha: float) -> dict[str, float]:
    """Add up the loss per year. Loss pixels hold 1 for 2001 up to 25 for 2025, and 0 for no loss."""
    pixels: dict[int, int] = {}
    for loss_year, canopy_pct in zip(loss_years.ravel().tolist(), canopy.ravel().tolist()):
        if loss_year not in (0, NOT_IN_PLOT) and canopy_pct > MIN_CANOPY_PCT:
            year = 2000 + loss_year
            pixels[year] = pixels.get(year, 0) + 1
    return {str(year): round(count * pixel_ha, 4) for year, count in sorted(pixels.items())}


def measure(shp) -> dict:
    tile = tile_of(shp)
    with rasterio.open(RASTER_URL.format(layer="lossyear", tile=tile)) as loss_file:
        with rasterio.open(RASTER_URL.format(layer="treecover2000", tile=tile)) as canopy_file:
            loss_years, transform = mask(loss_file, [mapping(shp)], crop=True, filled=True, nodata=NOT_IN_PLOT)
            canopy, _ = mask(canopy_file, [mapping(shp)], crop=True, filled=True, nodata=NOT_IN_PLOT)

    # A pixel is a fixed fraction of a degree, so pixels get narrower away from the equator.
    pixel_m = abs(transform.e) * M_PER_DEG_LAT
    pixel_ha = pixel_m * pixel_m * math.cos(math.radians(shp.centroid.y)) / 10_000
    pixels_in_plot = int((loss_years != NOT_IN_PLOT).sum())
    if pixels_in_plot == 0:
        raise RuntimeError("A plot covers no raster pixels, so its loss can't be measured.")
    return {
        "status": "checked",
        "measured_area_ha": round(pixels_in_plot * pixel_ha, 4),
        "loss_ha_by_year": loss_per_year(loss_years, canopy, pixel_ha),
    }


def build_record(feature: dict) -> dict:
    geometry = feature["geometry"]
    fingerprint = {"geometry_sha256": geometry_hash(geometry)}
    if not is_usable(geometry):
        return {**fingerprint, "status": "not_checked"}
    return {**fingerprint, **measure(area_to_measure(geometry, feature["properties"]["declared_area_ha"]))}


def main(cache_file: Path = DEFAULT_CACHE_FILE) -> None:
    plots = {}
    for plot_id, feature in load_plots().items():
        plots[plot_id] = build_record(feature)
        print(plot_id, plots[plot_id]["status"], plots[plot_id].get("loss_ha_by_year", ""), flush=True)

    # Written only after every plot succeeded, so a network failure can't leave half a cache.
    cache_file.parent.mkdir(exist_ok=True)
    cache = {
        "dataset": DATASET,
        "min_canopy_pct": MIN_CANOPY_PCT,
        "fetched_on": date.today().isoformat(),
        "plots": plots,
    }
    cache_file.write_text(json.dumps(cache, indent=2) + "\n")
    print(f"wrote {len(plots)} plots")


if __name__ == "__main__":
    main()
