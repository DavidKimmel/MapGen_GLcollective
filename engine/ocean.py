"""
MapGen — Coastline/Ocean Building.

Reconstructs ocean polygons by subtracting OSM land polygons from the viewport.
Supports both full-resolution (GPKG/SHP) and simplified land polygon datasets.

Ported from MapToPoster's create_map_poster.py.
"""

import os
import time

import geopandas as gpd
import pyproj
from shapely.geometry import box as shapely_box
from shapely.ops import unary_union

from utils.logging import safe_print

# Land polygon data paths (absolute)
_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_ENGINE_DIR)

LAND_POLYGONS_GPKG_FULL = os.path.join(
    _PROJECT_DIR, "data", "land-polygons-complete-3857", "land_polygons.gpkg"
)
LAND_POLYGONS_SHP_FULL = os.path.join(
    _PROJECT_DIR, "data", "land-polygons-complete-3857", "land_polygons.shp"
)
LAND_POLYGONS_SHP_SIMPLIFIED = os.path.join(
    _PROJECT_DIR, "data", "simplified-land-polygons-complete-3857",
    "simplified_land_polygons.shp",
)

_land_gdf_cache = None
_land_gdf_is_full_res = False


def _load_land_polygons(bbox_3857=None):
    """Load OSM land polygons — prefers full-res GPKG, falls back to simplified."""
    global _land_gdf_cache, _land_gdf_is_full_res

    gpkg_path = LAND_POLYGONS_GPKG_FULL
    full_path = LAND_POLYGONS_SHP_FULL
    full_res_path = None
    if os.path.exists(gpkg_path):
        full_res_path = gpkg_path
    elif os.path.exists(full_path):
        full_res_path = full_path

    if full_res_path is not None and bbox_3857 is not None:
        fmt = "GPKG" if full_res_path.endswith(".gpkg") else "SHP"
        safe_print(f"  Loading full-res land polygons [{fmt}] (bbox-filtered)...")
        t0 = time.time()
        gdf = gpd.read_file(full_res_path, bbox=bbox_3857)
        _land_gdf_is_full_res = True
        safe_print(f"  Full-res land polygons: {len(gdf)} features "
                   f"in viewport ({time.time() - t0:.1f}s)")
        return gdf

    if _land_gdf_cache is not None:
        return _land_gdf_cache

    simp_path = LAND_POLYGONS_SHP_SIMPLIFIED
    if not os.path.exists(simp_path):
        safe_print("[!] No land polygons found. Ocean fill will be skipped.")
        safe_print("    Download from: https://osmdata.openstreetmap.de/download/"
                   "land-polygons-complete-3857.zip")
        return None

    safe_print("  Loading simplified land polygons shapefile...")
    t0 = time.time()
    _land_gdf_cache = gpd.read_file(simp_path)
    _land_gdf_is_full_res = False
    safe_print(f"  Simplified land polygons loaded in {time.time() - t0:.1f}s "
               f"({len(_land_gdf_cache)} features)")
    return _land_gdf_cache


def build_ocean_polygons(point: tuple[float, float], dist: int, target_crs,
                         crop_xlim: tuple[float, float],
                         crop_ylim: tuple[float, float]) -> list:
    """Build ocean polygons by subtracting land from viewport.

    Strategy:
      1. Convert viewport bounds to EPSG:3857
      2. Clip pre-built land polygons to viewport
      3. Ocean = viewport - land
      4. Reproject back to target_crs
    """
    t0 = time.time()
    pad = 100
    vp_target = shapely_box(
        crop_xlim[0] - pad, crop_ylim[0] - pad,
        crop_xlim[1] + pad, crop_ylim[1] + pad,
    )

    transformer_to_3857 = pyproj.Transformer.from_crs(
        target_crs, "EPSG:3857", always_xy=True
    )
    transformer_from_3857 = pyproj.Transformer.from_crs(
        "EPSG:3857", target_crs, always_xy=True
    )

    x1_3857, y1_3857 = transformer_to_3857.transform(
        crop_xlim[0] - pad, crop_ylim[0] - pad
    )
    x2_3857, y2_3857 = transformer_to_3857.transform(
        crop_xlim[1] + pad, crop_ylim[1] + pad
    )
    vp_3857 = shapely_box(
        min(x1_3857, x2_3857), min(y1_3857, y2_3857),
        max(x1_3857, x2_3857), max(y1_3857, y2_3857),
    )

    bbox_tuple = (
        min(x1_3857, x2_3857), min(y1_3857, y2_3857),
        max(x1_3857, x2_3857), max(y1_3857, y2_3857),
    )
    land_gdf = _load_land_polygons(bbox_3857=bbox_tuple)
    if land_gdf is None:
        return []

    clipped = land_gdf.clip(vp_3857)
    if clipped.empty:
        safe_print("  No land in viewport — filling entire area as ocean")
        return [vp_target]

    land_union = unary_union(clipped.geometry)
    ocean_3857 = vp_3857.difference(land_union)

    if ocean_3857.is_empty:
        safe_print("  No ocean in viewport (inland city)")
        return []

    from shapely.ops import transform as shapely_transform
    ocean_target = shapely_transform(transformer_from_3857.transform, ocean_3857)
    ocean_target = ocean_target.intersection(vp_target)

    simplify_tol = 1 if _land_gdf_is_full_res else 10
    try:
        ocean_target = ocean_target.simplify(simplify_tol, preserve_topology=True)
    except Exception:
        pass

    elapsed = time.time() - t0
    ocean_area_km2 = ocean_target.area / 1e6
    ocean_pct = ocean_target.area / vp_target.area * 100
    safe_print(f"  Ocean fill: {ocean_area_km2:.1f} km2, "
               f"{ocean_pct:.0f}% of viewport ({elapsed:.2f}s)")

    result = []
    if ocean_target.geom_type == "Polygon":
        result.append(ocean_target)
    elif ocean_target.geom_type == "MultiPolygon":
        result.extend(ocean_target.geoms)
    elif ocean_target.geom_type == "GeometryCollection":
        for geom in ocean_target.geoms:
            if geom.geom_type in ("Polygon", "MultiPolygon"):
                if geom.geom_type == "MultiPolygon":
                    result.extend(geom.geoms)
                else:
                    result.append(geom)
    return result


def refine_ocean_with_harbors(ocean_polys: list, harbor_structures,
                              target_crs, crop_xlim: tuple[float, float],
                              crop_ylim: tuple[float, float]) -> list:
    """Carve harbor structures from ocean polygons to prevent floating rectangles."""
    if not ocean_polys or harbor_structures is None or harbor_structures.empty:
        return ocean_polys

    hs_carve = harbor_structures[
        harbor_structures.geometry.type.isin(["Polygon", "MultiPolygon"])
    ]
    if hs_carve.empty:
        return ocean_polys

    hs_carve_proj = hs_carve.to_crs(target_crs)
    _ocean_raw = unary_union(ocean_polys)
    vp_box = shapely_box(crop_xlim[0], crop_ylim[0], crop_xlim[1], crop_ylim[1])
    _land_boundary = vp_box.difference(_ocean_raw)
    _land_buffered = _land_boundary.buffer(5)

    land_touching = []
    floating_count = 0
    for _, row in hs_carve_proj.iterrows():
        if row.geometry.intersects(_land_buffered):
            land_touching.append(row.geometry)
        else:
            floating_count += 1

    if land_touching:
        hs_union = unary_union(land_touching).buffer(2)
        refined = []
        for poly in ocean_polys:
            try:
                diff = poly.difference(hs_union)
                if diff.is_empty:
                    continue
                if diff.geom_type == "Polygon":
                    refined.append(diff)
                elif diff.geom_type == "MultiPolygon":
                    refined.extend(diff.geoms)
                elif diff.geom_type == "GeometryCollection":
                    for g in diff.geoms:
                        if g.geom_type in ("Polygon", "MultiPolygon"):
                            if g.geom_type == "MultiPolygon":
                                refined.extend(g.geoms)
                            else:
                                refined.append(g)
            except Exception:
                refined.append(poly)
        safe_print(f"  Ocean refined: carved {len(land_touching)} harbor structures "
                   f"-> {len(refined)} polys (skipped {floating_count} floating)")
        return refined

    safe_print(f"  Ocean refined: no land-touching harbors "
               f"(skipped {floating_count} floating)")
    return ocean_polys
