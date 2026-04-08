"""
MapGen — County Boundary Lookup & Mask System.

Loads U.S. Census Bureau TIGER/Line county boundaries and provides
lookup, listing, and clip-mask functions for county map products.
"""

import os
from functools import lru_cache

import geopandas as gpd
import numpy as np
import pyproj
from geopandas import GeoDataFrame
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MplPath
from shapely.geometry import LinearRing, MultiPolygon, Polygon
from shapely.ops import transform as shapely_transform

from utils.logging import safe_print

_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_ENGINE_DIR)
_SHAPEFILE_PATH = os.path.join(
    _PROJECT_DIR, "data", "counties", "cb_2023_us_county_500k.shp"
)

# State abbreviation -> FIPS mapping for convenience
_STATE_ABBREV_TO_FIPS: dict[str, str] = {}


@lru_cache(maxsize=1)
def _load_counties() -> GeoDataFrame:
    """Load the county shapefile (cached after first call)."""
    if not os.path.exists(_SHAPEFILE_PATH):
        raise FileNotFoundError(
            f"County shapefile not found at {_SHAPEFILE_PATH}. "
            "Run Phase 2 to download TIGER/Line data."
        )
    gdf = gpd.read_file(_SHAPEFILE_PATH)
    # Build state abbrev lookup
    for _, row in gdf[["STATEFP", "STUSPS"]].drop_duplicates().iterrows():
        _STATE_ABBREV_TO_FIPS[row["STUSPS"].upper()] = row["STATEFP"]
    return gdf


def _normalize_state(state: str) -> str:
    """Accept state abbreviation or full name, return STUSPS (e.g. 'VA')."""
    gdf = _load_counties()
    state_upper = state.strip().upper()

    # Check abbreviation first
    if state_upper in _STATE_ABBREV_TO_FIPS:
        return state_upper

    # Check full name
    match = gdf[gdf["STATE_NAME"].str.upper() == state_upper]
    if not match.empty:
        return match.iloc[0]["STUSPS"]

    raise ValueError(
        f"Unknown state: '{state}'. Use abbreviation (e.g. 'VA') or full name."
    )


def list_counties(state: str) -> list[str]:
    """Return sorted list of county names for a state."""
    gdf = _load_counties()
    stusps = _normalize_state(state)
    subset = gdf[gdf["STUSPS"] == stusps]
    return sorted(subset["NAME"].tolist())


def lookup_county(county_name: str, state: str) -> Polygon | MultiPolygon:
    """Look up a county polygon by name and state.

    Returns the county geometry in EPSG:4269 (NAD83, geographic).
    """
    gdf = _load_counties()
    stusps = _normalize_state(state)
    county_upper = county_name.strip().upper()

    matches = gdf[
        (gdf["STUSPS"] == stusps)
        & (gdf["NAME"].str.upper() == county_upper)
        # Exclude independent cities (LSAD=25) when a county (LSAD=06) exists
    ]

    if matches.empty:
        available = list_counties(state)
        raise ValueError(
            f"County '{county_name}' not found in {stusps}. "
            f"Available: {', '.join(available[:15])}..."
        )

    # Prefer actual county (LSAD=06) over independent city (LSAD=25)
    counties_only = matches[matches["LSAD"] == "06"]
    if not counties_only.empty:
        row = counties_only.iloc[0]
    else:
        row = matches.iloc[0]

    return row.geometry


def lookup_county_by_fips(fips_code: str) -> Polygon | MultiPolygon:
    """Look up a county polygon by FIPS GEOID (e.g. '51059')."""
    gdf = _load_counties()
    matches = gdf[gdf["GEOID"] == fips_code]
    if matches.empty:
        raise ValueError(f"No county found with FIPS code '{fips_code}'.")
    return matches.iloc[0].geometry


def get_county_bounds(
    county_name: str, state: str
) -> tuple[float, float, tuple[float, float, float, float]]:
    """Get center and bounding box for a county.

    Returns:
        (center_lat, center_lon, (minx, miny, maxx, maxy))
        where bbox is in EPSG:4269 (lon/lat order from shapely).
    """
    geom = lookup_county(county_name, state)
    centroid = geom.centroid
    bbox = geom.bounds  # (minx, miny, maxx, maxy) = (min_lon, min_lat, max_lon, max_lat)
    return centroid.y, centroid.x, bbox


def get_county_info(county_name: str, state: str) -> dict:
    """Get full metadata for a county (name, FIPS, state, etc.)."""
    gdf = _load_counties()
    stusps = _normalize_state(state)
    county_upper = county_name.strip().upper()

    matches = gdf[
        (gdf["STUSPS"] == stusps) & (gdf["NAME"].str.upper() == county_upper)
    ]
    if matches.empty:
        raise ValueError(f"County '{county_name}' not found in {stusps}.")

    counties_only = matches[matches["LSAD"] == "06"]
    row = counties_only.iloc[0] if not counties_only.empty else matches.iloc[0]

    return {
        "name": row["NAME"],
        "namelsad": row["NAMELSAD"],
        "state": row["STATE_NAME"],
        "stusps": row["STUSPS"],
        "fips": row["GEOID"],
    }


def county_polygon_in_crs(
    county_name: str, state: str, target_crs: str
) -> Polygon | MultiPolygon:
    """Get county polygon reprojected to the target CRS."""
    geom = lookup_county(county_name, state)
    source_crs = "EPSG:4269"

    transformer = pyproj.Transformer.from_crs(
        source_crs, target_crs, always_xy=True
    )
    projected = shapely_transform(transformer.transform, geom)
    return projected


def apply_county_crop(
    ax,
    fig,
    county_name: str,
    state: str,
    target_crs: str,
    bg_color: str = "#FFFFFF",
    border_width: float = 2.0,
) -> None:
    """Apply a county-boundary crop mask to the map axes.

    Same approach as circle/heart/house crops: draw a filled rectangle
    with the county shape cut out, then add a border stroke.
    """
    county_geom = county_polygon_in_crs(county_name, state, target_crs)

    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]
    pad = max(x_range, y_range) * 0.15

    # Outer rectangle (covers everything)
    rect_verts = [
        (xlim[0] - pad, ylim[0] - pad),
        (xlim[1] + pad, ylim[0] - pad),
        (xlim[1] + pad, ylim[1] + pad),
        (xlim[0] - pad, ylim[1] + pad),
        (xlim[0] - pad, ylim[0] - pad),
    ]
    rect_codes = [MplPath.MOVETO] + [MplPath.LINETO] * 3 + [MplPath.CLOSEPOLY]

    # Convert county geometry to matplotlib path vertices (hole)
    hole_verts, hole_codes = _geometry_to_mpl_hole(county_geom)

    all_verts = rect_verts + hole_verts
    all_codes = rect_codes + hole_codes

    mask_path = MplPath(all_verts, all_codes)
    mask_patch = PathPatch(
        mask_path,
        facecolor=bg_color,
        edgecolor="none",
        zorder=14,
        antialiased=True,
    )
    ax.add_patch(mask_patch)

    # Border stroke along county edge
    border_verts, border_codes = _geometry_to_mpl_path(county_geom)
    border_path = MplPath(border_verts, border_codes)
    border_patch = PathPatch(
        border_path,
        transform=ax.transData,
        facecolor="none",
        edgecolor=_border_color(bg_color),
        linewidth=border_width,
        zorder=15,
    )
    ax.add_patch(border_patch)

    safe_print(f"  County crop applied ({county_name}, {state})")


def _geometry_to_mpl_hole(
    geom: Polygon | MultiPolygon,
) -> tuple[list[tuple[float, float]], list[int]]:
    """Convert a Shapely polygon/multipolygon to reversed MPL path (for hole cutout)."""
    all_verts: list[tuple[float, float]] = []
    all_codes: list[int] = []

    polygons = geom.geoms if isinstance(geom, MultiPolygon) else [geom]

    for poly in polygons:
        # Exterior ring must be CW for hole (rect is CCW).
        # Shapefile data is often already CW; check before reversing.
        coords = list(poly.exterior.coords)
        if LinearRing(coords).is_ccw:
            coords = coords[::-1]
        if coords[-1] != coords[0]:
            coords.append(coords[0])
        all_verts.extend(coords)
        all_codes.extend(
            [MplPath.MOVETO]
            + [MplPath.LINETO] * (len(coords) - 2)
            + [MplPath.CLOSEPOLY]
        )

        # Interior rings (islands within the county — rare but handle them)
        for interior in poly.interiors:
            icoords = list(interior.coords)
            if icoords[-1] != icoords[0]:
                icoords.append(icoords[0])
            all_verts.extend(icoords)
            all_codes.extend(
                [MplPath.MOVETO]
                + [MplPath.LINETO] * (len(icoords) - 2)
                + [MplPath.CLOSEPOLY]
            )

    return all_verts, all_codes


def _geometry_to_mpl_path(
    geom: Polygon | MultiPolygon,
) -> tuple[list[tuple[float, float]], list[int]]:
    """Convert a Shapely polygon/multipolygon to an MPL path (for border stroke)."""
    all_verts: list[tuple[float, float]] = []
    all_codes: list[int] = []

    polygons = geom.geoms if isinstance(geom, MultiPolygon) else [geom]

    for poly in polygons:
        coords = list(poly.exterior.coords)
        if coords[-1] != coords[0]:
            coords.append(coords[0])
        all_verts.extend(coords)
        all_codes.extend(
            [MplPath.MOVETO]
            + [MplPath.LINETO] * (len(coords) - 2)
            + [MplPath.CLOSEPOLY]
        )

    return all_verts, all_codes


def _border_color(bg_color: str) -> str:
    """Return a suitable border color based on background luminance."""
    r = int(bg_color[1:3], 16)
    g = int(bg_color[3:5], 16)
    b = int(bg_color[5:7], 16)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b

    if luminance > 180:
        return "#2C2C2C"
    elif luminance > 80:
        factor = 0.6
        return (
            f"#{max(0,int(r*factor)):02x}"
            f"{max(0,int(g*factor)):02x}"
            f"{max(0,int(b*factor)):02x}"
        )
    else:
        factor = 1.4
        return (
            f"#{min(255,int(r*factor)):02x}"
            f"{min(255,int(g*factor)):02x}"
            f"{min(255,int(b*factor)):02x}"
        )
