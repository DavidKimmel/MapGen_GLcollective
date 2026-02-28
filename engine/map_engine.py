"""
MapGen — OSM Data Fetching & Layer Rendering Engine.

Core map rendering infrastructure: fetches OSM data (street networks,
water, parks, buildings, landuse, waterways, natural areas, wetlands,
railways, cemetery/farmland, harbors), projects to CRS, and renders
each layer with proper z-ordering.

Ported from MapToPoster's create_map_poster.py with enhancements
from GeoLineCollective's map_engine.py.
"""

import time
from typing import cast

import geopandas as gpd
import numpy as np
import osmnx as ox
import pyproj
from geopandas import GeoDataFrame
from matplotlib.collections import PatchCollection
from matplotlib.patches import PathPatch as MplPathPatch, Polygon as MplPolygon
from matplotlib.path import Path as MplPath
from networkx import MultiDiGraph
from shapely.geometry import Point, box as shapely_box
from shapely.ops import unary_union

from utils.cache import cache_get, cache_set, CacheError, round_cache_key
from utils.logging import safe_print

# In-memory cache for CRS-projected GeoDataFrames.
# Key: (feature_cache_key, crs_string) -> projected GeoDataFrame
# Avoids repeated to_crs() calls on same data across renders.
_projected_cache: dict[tuple[str, str], GeoDataFrame] = {}
_PROJECTED_CACHE_MAX = 64


def project_cached(gdf: GeoDataFrame, target_crs, cache_key: str) -> GeoDataFrame:
    """Project a GeoDataFrame to target CRS with caching."""
    crs_str = str(target_crs)
    k = (cache_key, crs_str, id(gdf))
    if k in _projected_cache:
        return _projected_cache[k]
    projected = gdf.to_crs(target_crs)
    _projected_cache[k] = projected
    if len(_projected_cache) > _PROJECTED_CACHE_MAX:
        # Evict oldest entries
        keys = list(_projected_cache.keys())
        for old_key in keys[:len(keys) // 2]:
            _projected_cache.pop(old_key, None)
    return projected

# Reference distance for zoom scaling (tuned for close-up city maps)
REFERENCE_DIST = 8000


# ---------------------------------------------------------------------------
# OSM Data Fetching
# ---------------------------------------------------------------------------
def fetch_graph(point: tuple[float, float], dist: int) -> MultiDiGraph | None:
    """Fetch street network graph from OpenStreetMap with caching."""
    lat, lon = point
    rlat, rlon, rdist = round_cache_key(lat, lon, dist)
    graph_key = f"graph_{rlat}_{rlon}_{rdist}"
    cached = cache_get(graph_key)
    if cached is not None:
        safe_print(f"[OK] Using cached street network ({graph_key})")
        return cast(MultiDiGraph, cached)

    safe_print(f"  Downloading fresh street network (cache key: {graph_key})")
    try:
        g = ox.graph_from_point(
            point, dist=rdist, dist_type='bbox',
            network_type='all', truncate_by_edge=True,
        )
        time.sleep(0.5)
        try:
            cache_set(graph_key, g)
        except CacheError as e:
            safe_print(str(e))
        return g
    except Exception as e:
        safe_print(f"OSMnx error while fetching graph: {e}")
        return None


def fetch_features(point: tuple[float, float], dist: int, tags: dict,
                   name: str) -> GeoDataFrame | None:
    """Fetch geographic features from OpenStreetMap with caching."""
    lat, lon = point
    rlat, rlon, rdist = round_cache_key(lat, lon, dist)
    tag_str = "_".join(sorted(tags.keys()))
    feat_key = f"{name}_{rlat}_{rlon}_{rdist}_{tag_str}"
    cached = cache_get(feat_key)
    if cached is not None:
        safe_print(f"[OK] Using cached {name} ({feat_key})")
        return cast(GeoDataFrame, cached)

    safe_print(f"  Downloading fresh {name} (cache key: {feat_key})")
    try:
        data = ox.features_from_point(point, tags=tags, dist=rdist)
        time.sleep(0.3)
        try:
            cache_set(feat_key, data)
        except CacheError as e:
            safe_print(str(e))
        return data
    except Exception as e:
        safe_print(f"OSMnx error while fetching features: {e}")
        return None


def fetch_all_osm_data(point: tuple[float, float], dist: int,
                       theme: dict, detail_layers: bool = True) -> dict:
    """Fetch all OSM layers needed for map rendering.

    Args:
        point: (lat, lon) center point
        dist: Distance in meters
        theme: Theme dict (controls which optional layers are fetched)
        detail_layers: If True, fetch all 11 layers. If False, only roads+water+parks.

    Returns dict of GeoDataFrames (or None for each layer).
    """
    compensated_dist = int(dist * 1.1)

    # Always fetch: street network, water, parks
    safe_print("  [1/11] Downloading street network...")
    g = fetch_graph(point, compensated_dist)
    if g is None:
        raise RuntimeError("Failed to retrieve street network data.")

    safe_print("  [2/11] Downloading water features...")
    water = fetch_features(
        point, compensated_dist,
        tags={
            "natural": ["water", "bay", "strait"],
            "waterway": ["riverbank", "river", "canal"],
            "landuse": ["basin", "reservoir"],
        },
        name="water",
    )

    safe_print("  [3/11] Downloading parks/green spaces...")
    parks = fetch_features(
        point, compensated_dist,
        tags={"leisure": "park", "landuse": ["grass", "meadow", "forest"]},
        name="parks",
    )

    # Detail layers: only fetch when detail_layers=True
    buildings = None
    landuse = None
    waterway_lines = None
    natural_areas = None
    wetlands = None
    railways = None
    landuse_misc = None
    harbor_structures = None

    if detail_layers:
        if theme.get("buildings"):
            safe_print("  [4/11] Downloading building footprints...")
            buildings = fetch_features(
                point, compensated_dist,
                tags={"building": True},
                name="buildings",
            )
        else:
            safe_print("  [4/11] Skipping buildings (no theme color)")

        if theme.get("landuse_industrial") or theme.get("landuse_commercial"):
            safe_print("  [5/11] Downloading landuse areas...")
            landuse = fetch_features(
                point, compensated_dist,
                tags={"landuse": ["industrial", "commercial", "retail", "railway"]},
                name="landuse",
            )
        else:
            safe_print("  [5/11] Skipping landuse (no theme colors)")

        if theme.get("waterway_line"):
            safe_print("  [6/11] Downloading waterway lines...")
            waterway_lines = fetch_features(
                point, compensated_dist,
                tags={"waterway": ["river", "stream", "canal"]},
                name="waterway_lines",
            )
        else:
            safe_print("  [6/11] Skipping waterway lines (no theme color)")

        safe_print("  [7/11] Downloading natural areas...")
        natural_areas = fetch_features(
            point, compensated_dist,
            tags={"natural": ["wood", "scrub", "heath", "grassland", "bare_rock"]},
            name="natural_areas",
        )

        if theme.get("wetland_fill"):
            safe_print("  [8/11] Downloading wetlands...")
            wetlands = fetch_features(
                point, compensated_dist,
                tags={"natural": ["wetland", "mud"]},
                name="wetlands",
            )
        else:
            safe_print("  [8/11] Skipping wetlands (no theme color)")

        if theme.get("railway_line"):
            safe_print("  [9/11] Downloading railways...")
            railways = fetch_features(
                point, compensated_dist,
                tags={"railway": ["rail", "light_rail", "narrow_gauge"]},
                name="railways",
            )
        else:
            safe_print("  [9/11] Skipping railways (no theme color)")

        if theme.get("landuse_cemetery") or theme.get("landuse_farmland"):
            safe_print("  [10/11] Downloading cemetery/farmland areas...")
            landuse_misc = fetch_features(
                point, compensated_dist,
                tags={"landuse": ["cemetery", "farmland", "farmyard", "allotments",
                                   "vineyard", "orchard", "military"]},
                name="landuse_misc",
            )
        else:
            safe_print("  [10/11] Skipping cemetery/farmland (no theme colors)")

        safe_print("  [11/11] Downloading harbor/port structures...")
        harbor_structures = fetch_features(
            point, compensated_dist,
            tags={
                "man_made": ["pier", "breakwater", "groyne", "quay", "jetty", "wharf"],
                "amenity": ["ferry_terminal"],
            },
            name="harbor_structures",
        )
    else:
        safe_print("  [4-11/11] Skipping detail layers (detail_layers=False)")

    safe_print("[OK] All data retrieved successfully!")

    return {
        "graph": g,
        "water": water,
        "parks": parks,
        "buildings": buildings,
        "landuse": landuse,
        "waterway_lines": waterway_lines,
        "natural_areas": natural_areas,
        "wetlands": wetlands,
        "railways": railways,
        "landuse_misc": landuse_misc,
        "harbor_structures": harbor_structures,
        "compensated_dist": compensated_dist,
    }


# ---------------------------------------------------------------------------
# Coordinate Projection
# ---------------------------------------------------------------------------
def get_crop_limits(g_proj, center_lat_lon: tuple[float, float],
                    axes_w_inches: float, axes_h_inches: float,
                    dist: int) -> tuple[tuple[float, float], tuple[float, float]]:
    """Compute xlim/ylim that fill the axes with equal meter scaling."""
    lat, lon = center_lat_lon
    center = ox.projection.project_geometry(
        Point(lon, lat), crs="EPSG:4326", to_crs=g_proj.graph["crs"]
    )[0]
    center_x, center_y = center.x, center.y

    aspect = axes_w_inches / axes_h_inches
    if aspect >= 1:
        half_x = dist
        half_y = dist / aspect
    else:
        half_y = dist
        half_x = dist * aspect

    return (
        (center_x - half_x, center_x + half_x),
        (center_y - half_y, center_y + half_y),
    )


# ---------------------------------------------------------------------------
# Layer Rendering Helpers
# ---------------------------------------------------------------------------
def _poly_to_path(poly):
    """Convert a shapely Polygon (with holes) to a matplotlib Path."""
    all_verts = []
    all_codes = []
    coords = list(poly.exterior.coords)
    all_verts.extend(coords)
    all_codes.extend(
        [MplPath.MOVETO] + [MplPath.LINETO] * (len(coords) - 2) + [MplPath.CLOSEPOLY]
    )
    for interior in poly.interiors:
        coords = list(interior.coords)
        all_verts.extend(coords)
        all_codes.extend(
            [MplPath.MOVETO] + [MplPath.LINETO] * (len(coords) - 2) + [MplPath.CLOSEPOLY]
        )
    return MplPath(all_verts, all_codes)


def render_ocean(ax, ocean_polys: list, theme: dict, zoom_scale: float) -> None:
    """Render ocean fill and coastline stroke."""
    if not ocean_polys:
        return

    patches = []
    hole_count = 0
    for poly in ocean_polys:
        if hasattr(poly, 'exterior'):
            hole_count += len(list(poly.interiors))
            patches.append(MplPathPatch(_poly_to_path(poly)))
        elif hasattr(poly, 'geoms'):
            for p in poly.geoms:
                if hasattr(p, 'exterior'):
                    hole_count += len(list(p.interiors))
                    patches.append(MplPathPatch(_poly_to_path(p)))
    if patches:
        pc = PatchCollection(
            patches, facecolor=theme['water'], edgecolor='none', zorder=0.3
        )
        ax.add_collection(pc)
        safe_print(f"  Ocean fill: {len(patches)} patches ({hole_count} holes)")

    # Coastline stroke
    coastline_color = theme.get("coastline_stroke")
    if coastline_color:
        stroke_patches = []
        for poly in ocean_polys:
            if hasattr(poly, 'exterior'):
                stroke_patches.append(MplPolygon(list(poly.exterior.coords), closed=True))
            elif hasattr(poly, 'geoms'):
                for p in poly.geoms:
                    if hasattr(p, 'exterior'):
                        stroke_patches.append(MplPolygon(list(p.exterior.coords), closed=True))
        if stroke_patches:
            pc_stroke = PatchCollection(
                stroke_patches, facecolor='none',
                edgecolor=coastline_color,
                linewidth=0.4 * zoom_scale, zorder=0.35,
            )
            ax.add_collection(pc_stroke)
            safe_print(f"  Coastline stroke: {len(stroke_patches)} edges")


def render_natural_areas(ax, natural_areas, target_crs, theme: dict,
                         zoom_scale: float, ocean_union=None) -> None:
    """Render natural areas (wood, scrub, heath)."""
    if natural_areas is None or natural_areas.empty:
        return
    nat_polys = natural_areas[
        natural_areas.geometry.type.isin(["Polygon", "MultiPolygon"])
    ]
    if nat_polys.empty:
        return
    nat_polys = project_cached(nat_polys, target_crs, "natural_areas")
    nat_fill = theme.get("natural_fill", "#D8E8D0")
    nat_polys.plot(
        ax=ax, facecolor=nat_fill, edgecolor='#BBBBBB',
        linewidth=0.3 * zoom_scale, alpha=0.35, zorder=0.4,
    )
    safe_print(f"  Natural areas: {len(nat_polys)} polygons")


def render_wetlands(ax, wetlands, target_crs, theme: dict) -> None:
    """Render wetlands with stippled pattern."""
    if wetlands is None or wetlands.empty:
        return
    wetland_fill = theme.get("wetland_fill")
    if not wetland_fill:
        return
    wl_polys = wetlands[wetlands.geometry.type.isin(["Polygon", "MultiPolygon"])]
    if wl_polys.empty:
        return
    wl_polys = project_cached(wl_polys, target_crs, "wetlands")
    wl_polys.plot(
        ax=ax, facecolor=wetland_fill, edgecolor='none',
        alpha=0.5, zorder=0.45,
    )
    wetland_dots = theme.get("wetland_dots")
    if wetland_dots:
        rng = np.random.RandomState(99)
        for _, row in wl_polys.iterrows():
            geom = row.geometry
            if geom.is_empty:
                continue
            minx, miny, maxx, maxy = geom.bounds
            area = geom.area
            n_dots = max(10, min(3000, int(area / 2000)))
            xs = rng.uniform(minx, maxx, n_dots * 3)
            ys = rng.uniform(miny, maxy, n_dots * 3)
            inside_x, inside_y = [], []
            for x, y in zip(xs, ys):
                if geom.contains(Point(x, y)):
                    inside_x.append(x)
                    inside_y.append(y)
                    if len(inside_x) >= n_dots:
                        break
            if inside_x:
                ax.scatter(
                    inside_x, inside_y,
                    s=0.3, c=wetland_dots, marker='.',
                    alpha=0.6, zorder=0.46, linewidths=0,
                )
    safe_print(f"  Wetlands: {len(wl_polys)} polygons")


def render_landuse_misc(ax, landuse_misc, target_crs, theme: dict,
                        ocean_union=None) -> None:
    """Render cemetery/farmland areas."""
    if landuse_misc is None or landuse_misc.empty:
        return
    lm_polys = landuse_misc[landuse_misc.geometry.type.isin(["Polygon", "MultiPolygon"])]
    if lm_polys.empty:
        return
    lm_polys = project_cached(lm_polys, target_crs, "landuse_misc")
    if ocean_union is not None:
        try:
            lm_polys = lm_polys.copy()
            lm_polys["geometry"] = lm_polys.geometry.difference(ocean_union)
            lm_polys = lm_polys[~lm_polys.geometry.is_empty]
        except Exception:
            pass
    cem_color = theme.get("landuse_cemetery", "#E0DCCC")
    farm_color = theme.get("landuse_farmland", "#EDE8DC")
    mil_color = theme.get("landuse_industrial", cem_color)

    # Group patches by color for batched PatchCollection rendering
    color_patches: dict[str, list] = {}
    for _, row in lm_polys.iterrows():
        lu_type = row.get("landuse", "")
        if isinstance(lu_type, list):
            lu_type = lu_type[0]
        color = cem_color if lu_type == "cemetery" else (mil_color if lu_type == "military" else farm_color)
        geom = row.geometry
        if not geom or geom.is_empty:
            continue
        polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        bucket = color_patches.setdefault(color, [])
        for p in polys:
            bucket.append(MplPolygon(list(p.exterior.coords), closed=True))

    for color, patches in color_patches.items():
        if patches:
            pc = PatchCollection(
                patches, facecolor=color, edgecolor='none',
                alpha=0.45, zorder=0.48,
            )
            ax.add_collection(pc)
    safe_print(f"  Cemetery/farmland: {len(lm_polys)} polygons")


def render_water(ax, water, target_crs, theme: dict,
                 ocean_union=None) -> None:
    """Render inland water polygons."""
    if water is None or water.empty:
        return
    water_polys = water[water.geometry.type.isin(["Polygon", "MultiPolygon"])]
    if water_polys.empty:
        return
    water_polys = project_cached(water_polys, target_crs, "water")
    water_polys.plot(
        ax=ax, facecolor=theme['water'], edgecolor='none', zorder=0.5,
    )
    safe_print(f"  Water: {len(water_polys)} polygons")


def render_waterway_lines(ax, waterway_lines, target_crs, theme: dict,
                          zoom_scale: float, ocean_union=None,
                          water=None) -> None:
    """Render waterway lines (rivers, canals, streams)."""
    waterway_color = theme.get("waterway_line")
    if waterway_lines is None or waterway_lines.empty or not waterway_color:
        return
    ww_lines = waterway_lines[
        waterway_lines.geometry.type.isin(["LineString", "MultiLineString"])
    ]
    if ww_lines.empty:
        return
    ww_lines = project_cached(ww_lines, target_crs, "waterway_lines")

    # Clip waterway lines against open water
    clip_parts = []
    if ocean_union is not None:
        clip_parts.append(ocean_union)
    if water is not None and not water.empty:
        wp = water[water.geometry.type.isin(["Polygon", "MultiPolygon"])]
        if not wp.empty:
            wp_crs = project_cached(wp, target_crs, "water_clip")
            try:
                clip_parts.append(unary_union(wp_crs.geometry.values))
            except Exception:
                pass
    if clip_parts:
        try:
            all_water = unary_union(clip_parts)
            ww_lines = ww_lines.copy()
            ww_lines["geometry"] = ww_lines.geometry.difference(all_water)
            ww_lines = ww_lines[~ww_lines.geometry.is_empty]
        except Exception:
            pass

    # Vary width by waterway type — vectorized
    ww_type_col = ww_lines["waterway"] if "waterway" in ww_lines.columns else None
    if ww_type_col is not None:
        ww_types = ww_type_col.apply(
            lambda v: v[0] if isinstance(v, list) and v else (v if isinstance(v, str) else "stream")
        )
    else:
        ww_types = "stream"
    width_map = {"river": 1.2, "canal": 0.8}
    if isinstance(ww_types, str):
        ww_widths = [width_map.get(ww_types, 0.4) * zoom_scale] * len(ww_lines)
    else:
        ww_widths = [width_map.get(t, 0.4) * zoom_scale for t in ww_types]

    ww_outline_color = theme.get("waterway_outline")
    if ww_outline_color:
        ww_casing = [w + 0.6 * zoom_scale for w in ww_widths]
        ww_lines.plot(ax=ax, color=ww_outline_color, linewidth=ww_casing, zorder=0.54)
    ww_lines.plot(ax=ax, color=waterway_color, linewidth=ww_widths, zorder=0.55)
    safe_print(f"  Waterway lines: {len(ww_lines)} features")


def render_landuse(ax, landuse, target_crs, theme: dict,
                   ocean_union=None) -> None:
    """Render landuse areas (industrial/commercial)."""
    if landuse is None or landuse.empty:
        return
    lu_polys = landuse[landuse.geometry.type.isin(["Polygon", "MultiPolygon"])]
    if lu_polys.empty:
        return
    lu_polys = project_cached(lu_polys, target_crs, "landuse")
    if ocean_union is not None:
        try:
            lu_polys = lu_polys.copy()
            lu_polys["geometry"] = lu_polys.geometry.difference(ocean_union)
            lu_polys = lu_polys[~lu_polys.geometry.is_empty]
        except Exception:
            pass
    ind_color = theme.get("landuse_industrial", "#E0D5CE")
    com_color = theme.get("landuse_commercial", "#E3DDD6")

    color_patches: dict[str, list] = {}
    for _, row in lu_polys.iterrows():
        lu_type = row.get("landuse", "")
        if isinstance(lu_type, list):
            lu_type = lu_type[0]
        color = ind_color if lu_type in ("industrial", "railway") else com_color
        geom = row.geometry
        if not geom or geom.is_empty:
            continue
        polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        bucket = color_patches.setdefault(color, [])
        for p in polys:
            bucket.append(MplPolygon(list(p.exterior.coords), closed=True))

    for color, patches in color_patches.items():
        if patches:
            pc = PatchCollection(
                patches, facecolor=color, edgecolor='none',
                alpha=0.55, zorder=0.6,
            )
            ax.add_collection(pc)
    safe_print(f"  Landuse: {len(lu_polys)} polygons")


def render_parks(ax, parks, target_crs, theme: dict) -> None:
    """Render parks/green spaces."""
    if parks is None or parks.empty:
        return
    park_polys = parks[parks.geometry.type.isin(["Polygon", "MultiPolygon"])]
    if park_polys.empty:
        return
    park_polys = project_cached(park_polys, target_crs, "parks")
    park_polys.plot(
        ax=ax, facecolor=theme['parks'], edgecolor='none', zorder=0.8,
    )
    safe_print(f"  Parks: {len(park_polys)} polygons")


def render_buildings(ax, buildings, target_crs, theme: dict) -> None:
    """Render building footprints."""
    if buildings is None or buildings.empty or not theme.get("buildings"):
        return
    bldg_polys = buildings[buildings.geometry.type.isin(["Polygon", "MultiPolygon"])]
    if bldg_polys.empty:
        return
    bldg_polys = project_cached(bldg_polys, target_crs, "buildings")
    bldg_polys.plot(
        ax=ax, facecolor=theme["buildings"], edgecolor="none",
        alpha=0.6, zorder=0.9,
    )
    safe_print(f"  Buildings: {len(bldg_polys)} polygons")


def render_railways(ax, railways, target_crs, theme: dict,
                    zoom_scale: float, ocean_union=None) -> None:
    """Render railway lines as thin dashed lines."""
    railway_color = theme.get("railway_line")
    if railways is None or railways.empty or not railway_color:
        return
    rl_lines = railways[
        railways.geometry.type.isin(["LineString", "MultiLineString"])
    ]
    if rl_lines.empty:
        return
    rl_lines = project_cached(rl_lines, target_crs, "railways")
    if ocean_union is not None:
        try:
            rl_lines = rl_lines.copy()
            rl_lines["geometry"] = rl_lines.geometry.difference(ocean_union)
            rl_lines = rl_lines[~rl_lines.geometry.is_empty]
        except Exception:
            pass
    rl_lines.plot(
        ax=ax, color=railway_color, linewidth=0.3 * zoom_scale,
        linestyle=(0, (3, 3)), alpha=0.4, zorder=1.7,
    )
    safe_print(f"  Railways: {len(rl_lines)} lines")


def render_paper_texture(ax, theme: dict) -> None:
    """Add subtle paper texture for light themes."""
    import matplotlib.colors as mcolors
    from scipy.ndimage import gaussian_filter

    bg_rgb = mcolors.to_rgb(theme["bg"])
    bg_lum = 0.299 * bg_rgb[0] + 0.587 * bg_rgb[1] + 0.114 * bg_rgb[2]
    if bg_lum <= 0.4:
        return

    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    data_w = xlim[1] - xlim[0]
    data_h = ylim[1] - ylim[0]
    tex_scale = 0.05
    tex_w_px = max(200, min(800, int(data_w * tex_scale)))
    tex_h_px = max(200, min(800, int(data_h * tex_scale)))
    rng = np.random.RandomState(42)
    noise = rng.randn(tex_h_px, tex_w_px)
    noise_smooth = gaussian_filter(noise, sigma=8) * 0.4 + gaussian_filter(noise, sigma=2) * 0.3
    noise_smooth = noise_smooth / max(np.max(np.abs(noise_smooth)), 1e-10)
    texture_intensity = 0.025
    tex_rgba = np.ones((tex_h_px, tex_w_px, 4))
    for c in range(3):
        tex_rgba[:, :, c] = bg_rgb[c] + noise_smooth * texture_intensity
    tex_rgba[:, :, :3] = np.clip(tex_rgba[:, :, :3], 0, 1)
    ax.imshow(tex_rgba, extent=[xlim[0], xlim[1], ylim[0], ylim[1]],
              origin="upper", zorder=0, interpolation="bilinear")
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    safe_print("  Paper texture applied")
