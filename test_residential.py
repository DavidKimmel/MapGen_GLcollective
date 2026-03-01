"""Quick test: render San Francisco with residential + land base fill."""

import os
import time

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import osmnx as ox
import pyproj
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon as MplPolygon
from shapely.geometry import box as shapely_box
from shapely.ops import unary_union

from engine.map_engine import (
    REFERENCE_DIST,
    _poly_to_path,
    fetch_all_osm_data,
    fetch_features,
    get_crop_limits,
    project_cached,
    render_buildings,
    render_landuse,
    render_landuse_misc,
    render_natural_areas,
    render_ocean,
    render_paper_texture,
    render_parks,
    render_railways,
    render_water,
    render_waterway_lines,
    render_wetlands,
)
from matplotlib.patches import PathPatch as MplPathPatch
from engine.ocean import build_ocean_polygons, refine_ocean_with_harbors, _load_land_polygons
from engine.roads import render_roads
from engine.text_layout import get_zone_positions, render_bottom_text
from engine.renderer import load_theme
from export.output_sizes import get_size_config
from utils.logging import safe_print


def render_land_base_fill(
    ax, target_crs, crop_xlim, crop_ylim, theme: dict,
) -> None:
    """Render land polygons as a subtle base fill.

    This fills ALL land areas with a very light warm tone, eliminating
    the pure white gaps on islands and undeveloped areas. Similar to how
    the OSM web map renders a base land color.
    """
    # Build bbox in EPSG:3857 to load land polygons
    pad = 100
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
    if land_gdf is None or land_gdf.empty:
        safe_print("  Land base fill: no data")
        return

    clipped = land_gdf.clip(vp_3857)
    if clipped.empty:
        safe_print("  Land base fill: no land in viewport")
        return

    land_union = unary_union(clipped.geometry)

    # Reproject to target CRS
    from shapely.ops import transform as shapely_transform
    land_target = shapely_transform(transformer_from_3857.transform, land_union)

    # Render as very subtle warm fill — below everything else
    land_color = "#F0EBE1"  # Slightly warmer than background #FCFCFA
    patches = []
    if land_target.geom_type == "Polygon":
        patches.append(MplPathPatch(_poly_to_path(land_target)))
    elif land_target.geom_type == "MultiPolygon":
        for p in land_target.geoms:
            if p.geom_type == "Polygon":
                patches.append(MplPathPatch(_poly_to_path(p)))

    if patches:
        pc = PatchCollection(
            patches, facecolor=land_color, edgecolor='none',
            alpha=1.0, zorder=0.15,
        )
        ax.add_collection(pc)
    safe_print(f"  Land base fill: {len(patches)} polygons (color: {land_color})")


def render_residential(
    ax, residential_gdf, target_crs, theme: dict, ocean_union=None,
) -> None:
    """Render residential landuse as a light fill."""
    if residential_gdf is None or residential_gdf.empty:
        safe_print("  Residential: no data")
        return
    polys = residential_gdf[
        residential_gdf.geometry.type.isin(["Polygon", "MultiPolygon"])
    ]
    if polys.empty:
        safe_print("  Residential: no polygons")
        return
    polys = project_cached(polys, target_crs, "residential")
    if ocean_union is not None:
        try:
            polys = polys.copy()
            polys["geometry"] = polys.geometry.difference(ocean_union)
            polys = polys[~polys.geometry.is_empty]
        except Exception:
            pass

    # Warm fill — visible but not competing with parks/roads
    res_color = "#E4DDD0"
    patches = []
    for _, row in polys.iterrows():
        geom = row.geometry
        if not geom or geom.is_empty:
            continue
        sub_polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        for p in sub_polys:
            patches.append(MplPolygon(list(p.exterior.coords), closed=True))

    if patches:
        pc = PatchCollection(
            patches, facecolor=res_color, edgecolor='none',
            alpha=0.7, zorder=0.35,
        )
        ax.add_collection(pc)
    safe_print(f"  Residential/construction/recreation: {len(patches)} polygons")


def render_leisure_extra(
    ax, leisure_gdf, target_crs, theme: dict, ocean_union=None,
) -> None:
    """Render extra leisure areas (pitch, garden, playground) as light green."""
    if leisure_gdf is None or leisure_gdf.empty:
        safe_print("  Leisure extra: no data")
        return
    polys = leisure_gdf[
        leisure_gdf.geometry.type.isin(["Polygon", "MultiPolygon"])
    ]
    if polys.empty:
        safe_print("  Leisure extra: no polygons")
        return
    polys = project_cached(polys, target_crs, "leisure_extra")
    if ocean_union is not None:
        try:
            polys = polys.copy()
            polys["geometry"] = polys.geometry.difference(ocean_union)
            polys = polys[~polys.geometry.is_empty]
        except Exception:
            pass

    # Light green — similar to parks but slightly different
    leisure_color = theme.get("parks", "#B8D4AC")
    patches = []
    for _, row in polys.iterrows():
        geom = row.geometry
        if not geom or geom.is_empty:
            continue
        sub_polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        for p in sub_polys:
            patches.append(MplPolygon(list(p.exterior.coords), closed=True))

    if patches:
        pc = PatchCollection(
            patches, facecolor=leisure_color, edgecolor='none',
            alpha=0.6, zorder=0.75,
        )
        ax.add_collection(pc)
    safe_print(f"  Leisure extra: {len(patches)} polygons")


def main() -> None:
    t_start = time.time()

    # San Francisco
    lat, lon = 37.7749, -122.4194
    point = (lat, lon)
    city_name = "San Francisco"
    state_name = "California"
    theme_name = "37th_parallel"
    size = "16x20"
    dpi = 300

    theme_data = load_theme(theme_name)
    size_config = get_size_config(size)
    width_in = size_config["width_in"]
    height_in = size_config["height_in"]
    distance = 8000  # Match city_list.py for SF (default 5000 too tight)

    safe_print(f"Rendering {city_name} with residential layer test")
    safe_print(f"  Size: {size}, Distance: {distance}m, DPI: {dpi}")

    # Fetch standard OSM data
    safe_print("\nFetching standard OSM data...")
    osm_data = fetch_all_osm_data(point, distance, theme_data, detail_layers=True)

    # Fetch extra landuse layers we've been missing
    compensated_dist = osm_data["compensated_dist"]

    safe_print("\n  [EXTRA] Fetching residential + construction + recreation landuse...")
    residential = fetch_features(
        point, compensated_dist,
        tags={"landuse": ["residential", "construction", "recreation_ground"]},
        name="residential_ext",
    )
    if residential is not None:
        safe_print(f"  [EXTRA] Got {len(residential)} residential/construction/recreation features")

    safe_print("  [EXTRA] Fetching leisure areas (pitch, garden, playground)...")
    leisure_extra = fetch_features(
        point, compensated_dist,
        tags={"leisure": ["pitch", "garden", "playground", "sports_centre"]},
        name="leisure_extra",
    )
    if leisure_extra is not None:
        safe_print(f"  [EXTRA] Got {len(leisure_extra)} leisure features")

    # Set up figure
    zones = get_zone_positions(has_top_label=False)
    fig = plt.figure(figsize=(width_in, height_in), facecolor="#FFFFFF")
    ax = fig.add_axes(zones["map"])
    ax.set_facecolor(theme_data["bg"])

    # Project
    safe_print("\nProjecting...")
    g_proj = ox.project_graph(osm_data["graph"])
    target_crs = g_proj.graph['crs']

    ax_pos = ax.get_position()
    axes_w = ax_pos.width * fig.get_figwidth()
    axes_h = ax_pos.height * fig.get_figheight()
    crop_xlim, crop_ylim = get_crop_limits(g_proj, point, axes_w, axes_h, distance)
    ax.set_xlim(crop_xlim)
    ax.set_ylim(crop_ylim)
    ax.set_aspect("auto")
    ax.set_autoscale_on(False)
    ax.margins(0)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Render layers
    safe_print("\nRendering layers...")
    zoom_scale = min(1.5, max(0.3, REFERENCE_DIST / distance))

    # >>> NEW: Land base fill — subtle warm tone on all land areas <<<
    render_land_base_fill(ax, target_crs, crop_xlim, crop_ylim, theme_data)

    # Ocean
    ocean_polys = build_ocean_polygons(
        point, compensated_dist, target_crs, crop_xlim, crop_ylim
    )
    ocean_polys = refine_ocean_with_harbors(
        ocean_polys, osm_data["harbor_structures"], target_crs,
        crop_xlim, crop_ylim,
    )
    render_ocean(ax, ocean_polys, theme_data, zoom_scale)
    ocean_union = None
    if ocean_polys:
        try:
            ocean_union = unary_union(ocean_polys)
        except Exception:
            pass

    # Natural areas
    render_natural_areas(ax, osm_data["natural_areas"], target_crs,
                         theme_data, zoom_scale, ocean_union)
    render_wetlands(ax, osm_data["wetlands"], target_crs, theme_data)
    render_landuse_misc(ax, osm_data["landuse_misc"], target_crs,
                        theme_data, ocean_union)

    # >>> NEW: Residential + construction + recreation landuse <<<
    render_residential(ax, residential, target_crs, theme_data, ocean_union)

    # >>> NEW: Leisure areas (pitch, garden, playground) <<<
    render_leisure_extra(ax, leisure_extra, target_crs, theme_data, ocean_union)

    # Water
    render_water(ax, osm_data["water"], target_crs, theme_data, ocean_union)
    render_waterway_lines(ax, osm_data["waterway_lines"], target_crs,
                          theme_data, zoom_scale, ocean_union, osm_data["water"])
    render_landuse(ax, osm_data["landuse"], target_crs, theme_data, ocean_union)

    # Parks
    render_parks(ax, osm_data["parks"], target_crs, theme_data)

    # Buildings
    render_buildings(ax, osm_data["buildings"], target_crs, theme_data)

    # Roads
    gdf_edges_full = ox.graph_to_gdfs(g_proj, nodes=False)
    render_roads(ax, gdf_edges_full, theme_data, distance)

    # Railways
    render_railways(ax, osm_data["railways"], target_crs, theme_data,
                    zoom_scale, ocean_union)

    # Paper texture
    render_paper_texture(ax, theme_data)

    # Text
    scale_factor = min(height_in, width_in) / 12.0
    render_bottom_text(
        fig, city_name, state_name, True, point,
        None, None, theme_name,
        scale_factor=scale_factor, font_preset=1,
        text_line_1=city_name, text_line_2=state_name, text_line_3=None,
    )

    ax.set_position(zones["map"])

    # Save
    output_path = "etsy/renders/san_francisco/sf_residential_test3.png"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    safe_print(f"\nSaving to {output_path}...")

    import io
    from PIL import Image

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, facecolor="#FFFFFF")
    plt.close(fig)
    buf.seek(0)

    img = Image.open(buf)
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    img.save(output_path, "PNG", dpi=(dpi, dpi))
    buf.close()

    elapsed = time.time() - t_start
    file_size_mb = os.path.getsize(output_path) / 1e6
    safe_print(f"\n[OK] Done! ({elapsed:.1f}s, {file_size_mb:.1f} MB)")
    safe_print(f"     Output: {output_path}")


if __name__ == "__main__":
    main()
