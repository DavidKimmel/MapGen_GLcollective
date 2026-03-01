"""Quick test: render Washington DC with residential + construction + leisure layers."""

import os
import sys
import time

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import osmnx as ox
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon as MplPolygon
from shapely.ops import unary_union

from engine.map_engine import (
    REFERENCE_DIST,
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
from engine.ocean import build_ocean_polygons, refine_ocean_with_harbors
from engine.roads import render_roads
from engine.text_layout import get_zone_positions, render_bottom_text
from engine.renderer import load_theme
from export.output_sizes import get_size_config
from utils.logging import safe_print


def render_extra_landuse(ax, gdf, target_crs, theme, ocean_union=None):
    """Render residential/construction/recreation landuse."""
    if gdf is None or gdf.empty:
        return
    polys = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
    if polys.empty:
        return
    polys = project_cached(polys, target_crs, "residential_ext")
    if ocean_union is not None:
        try:
            polys = polys.copy()
            polys["geometry"] = polys.geometry.difference(ocean_union)
            polys = polys[~polys.geometry.is_empty]
        except Exception:
            pass
    patches = []
    for _, row in polys.iterrows():
        geom = row.geometry
        if not geom or geom.is_empty:
            continue
        sub = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        for p in sub:
            patches.append(MplPolygon(list(p.exterior.coords), closed=True))
    if patches:
        pc = PatchCollection(
            patches, facecolor="#E4DDD0", edgecolor='none',
            alpha=0.7, zorder=0.35,
        )
        ax.add_collection(pc)
    safe_print(f"  Residential/construction/recreation: {len(patches)} polygons")


def render_aeroway(ax, gdf, target_crs, theme, zoom_scale, ocean_union=None):
    """Render airport runways, taxiways, aprons, and terminals."""
    if gdf is None or gdf.empty:
        safe_print("  Aeroway: no data")
        return
    gdf_proj = project_cached(gdf, target_crs, "aeroway")
    if ocean_union is not None:
        try:
            gdf_proj = gdf_proj.copy()
            gdf_proj["geometry"] = gdf_proj.geometry.difference(ocean_union)
            gdf_proj = gdf_proj[~gdf_proj.geometry.is_empty]
        except Exception:
            pass

    aero_col = gdf_proj["aeroway"] if "aeroway" in gdf_proj.columns else None

    # Aprons (polygon tarmac areas) — light gray fill
    apron_types = {"apron", "helipad"}
    apron_polys = gdf_proj[
        gdf_proj.geometry.type.isin(["Polygon", "MultiPolygon"])
    ]
    if aero_col is not None:
        apron_mask = apron_polys.index.isin(
            gdf_proj[gdf_proj["aeroway"].isin(apron_types)].index
        )
        aprons = apron_polys[apron_mask]
    else:
        aprons = apron_polys
    if not aprons.empty:
        patches = []
        for _, row in aprons.iterrows():
            geom = row.geometry
            if not geom or geom.is_empty:
                continue
            sub = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
            for p in sub:
                patches.append(MplPolygon(list(p.exterior.coords), closed=True))
        if patches:
            pc = PatchCollection(
                patches, facecolor="#D9D5CF", edgecolor='none',
                alpha=0.8, zorder=0.85,
            )
            ax.add_collection(pc)
        safe_print(f"  Aeroway aprons: {len(patches)} polygons")

    # Terminals — render like buildings
    terminal_types = {"terminal", "hangar"}
    if aero_col is not None:
        terminals = gdf_proj[
            gdf_proj["aeroway"].isin(terminal_types) &
            gdf_proj.geometry.type.isin(["Polygon", "MultiPolygon"])
        ]
        if not terminals.empty:
            patches = []
            for _, row in terminals.iterrows():
                geom = row.geometry
                if not geom or geom.is_empty:
                    continue
                sub = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
                for p in sub:
                    patches.append(MplPolygon(list(p.exterior.coords), closed=True))
            if patches:
                bldg_color = theme.get("buildings", "#E8E8E0")
                pc = PatchCollection(
                    patches, facecolor=bldg_color, edgecolor='#BBBBBB',
                    linewidth=0.3 * zoom_scale, alpha=0.8, zorder=0.92,
                )
                ax.add_collection(pc)
            safe_print(f"  Aeroway terminals: {len(patches)} polygons")

    # Runways (lines) — thick dark gray
    lines = gdf_proj[gdf_proj.geometry.type.isin(["LineString", "MultiLineString"])]
    if aero_col is not None and not lines.empty:
        runways = lines[lines["aeroway"] == "runway"]
        if not runways.empty:
            runways.plot(
                ax=ax, color="#C8C4BC", linewidth=3.0 * zoom_scale,
                alpha=0.9, zorder=1.5,
            )
            safe_print(f"  Aeroway runways: {len(runways)} lines")

        taxiways = lines[lines["aeroway"].isin(["taxiway", "taxilane"])]
        if not taxiways.empty:
            taxiways.plot(
                ax=ax, color="#D0CCC4", linewidth=1.2 * zoom_scale,
                alpha=0.8, zorder=1.45,
            )
            safe_print(f"  Aeroway taxiways: {len(taxiways)} lines")


def render_leisure_extra(ax, gdf, target_crs, theme, ocean_union=None):
    """Render pitch/garden/playground as light green."""
    if gdf is None or gdf.empty:
        return
    polys = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
    if polys.empty:
        return
    polys = project_cached(polys, target_crs, "leisure_extra")
    if ocean_union is not None:
        try:
            polys = polys.copy()
            polys["geometry"] = polys.geometry.difference(ocean_union)
            polys = polys[~polys.geometry.is_empty]
        except Exception:
            pass
    patches = []
    for _, row in polys.iterrows():
        geom = row.geometry
        if not geom or geom.is_empty:
            continue
        sub = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        for p in sub:
            patches.append(MplPolygon(list(p.exterior.coords), closed=True))
    if patches:
        pc = PatchCollection(
            patches, facecolor=theme.get("parks", "#B8D4AC"), edgecolor='none',
            alpha=0.6, zorder=0.75,
        )
        ax.add_collection(pc)
    safe_print(f"  Leisure extra: {len(patches)} polygons")


def main():
    t_start = time.time()
    lat, lon = 38.9072, -77.0369
    point = (lat, lon)
    city_name = "Washington DC"
    state_name = "United States"
    distance = 8000
    theme_name = "37th_parallel"
    size = "16x20"
    dpi = 300

    theme_data = load_theme(theme_name)
    size_config = get_size_config(size)
    width_in = size_config["width_in"]
    height_in = size_config["height_in"]

    safe_print(f"Rendering {city_name} with extra layers")

    osm_data = fetch_all_osm_data(point, distance, theme_data, detail_layers=True)
    compensated_dist = osm_data["compensated_dist"]

    residential = fetch_features(
        point, compensated_dist,
        tags={"landuse": ["residential", "construction", "recreation_ground"]},
        name="residential_ext",
    )
    leisure_extra = fetch_features(
        point, compensated_dist,
        tags={"leisure": ["pitch", "garden", "playground", "sports_centre"]},
        name="leisure_extra",
    )
    aeroway = fetch_features(
        point, compensated_dist,
        tags={"aeroway": True},
        name="aeroway",
    )

    zones = get_zone_positions(has_top_label=False)
    fig = plt.figure(figsize=(width_in, height_in), facecolor="#FFFFFF")
    ax = fig.add_axes(zones["map"])
    ax.set_facecolor(theme_data["bg"])

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

    zoom_scale = min(1.5, max(0.3, REFERENCE_DIST / distance))

    # Ocean
    ocean_polys = build_ocean_polygons(
        point, compensated_dist, target_crs, crop_xlim, crop_ylim
    )
    ocean_polys = refine_ocean_with_harbors(
        ocean_polys, osm_data["harbor_structures"], target_crs,
        crop_xlim, crop_ylim,
    )
    render_ocean(ax, ocean_polys, theme_data, zoom_scale)
    ocean_union = unary_union(ocean_polys) if ocean_polys else None

    render_natural_areas(ax, osm_data["natural_areas"], target_crs,
                         theme_data, zoom_scale, ocean_union)
    render_wetlands(ax, osm_data["wetlands"], target_crs, theme_data)
    render_landuse_misc(ax, osm_data["landuse_misc"], target_crs,
                        theme_data, ocean_union)
    render_extra_landuse(ax, residential, target_crs, theme_data, ocean_union)
    render_leisure_extra(ax, leisure_extra, target_crs, theme_data, ocean_union)
    render_water(ax, osm_data["water"], target_crs, theme_data, ocean_union)
    render_waterway_lines(ax, osm_data["waterway_lines"], target_crs,
                          theme_data, zoom_scale, ocean_union, osm_data["water"])
    render_landuse(ax, osm_data["landuse"], target_crs, theme_data, ocean_union)
    render_parks(ax, osm_data["parks"], target_crs, theme_data)
    render_buildings(ax, osm_data["buildings"], target_crs, theme_data)
    gdf_edges_full = ox.graph_to_gdfs(g_proj, nodes=False)
    render_roads(ax, gdf_edges_full, theme_data, distance)
    render_railways(ax, osm_data["railways"], target_crs, theme_data,
                    zoom_scale, ocean_union)
    render_aeroway(ax, aeroway, target_crs, theme_data, zoom_scale, ocean_union)
    render_paper_texture(ax, theme_data)

    scale_factor = min(height_in, width_in) / 12.0
    render_bottom_text(
        fig, city_name, state_name, True, point,
        None, None, theme_name,
        scale_factor=scale_factor, font_preset=1,
        text_line_1=city_name, text_line_2=state_name, text_line_3=None,
    )
    ax.set_position(zones["map"])

    output_path = "etsy/renders/washington_dc/dc_residential_test2.png"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

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
    safe_print(f"\n[OK] Done! ({elapsed:.1f}s)")
    safe_print(f"     Output: {output_path}")


if __name__ == "__main__":
    main()
