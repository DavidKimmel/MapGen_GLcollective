"""
MapGen — Unified Poster Renderer.

Main orchestrator combining MapToPoster's detailed layer rendering with
GeoLineCollective's crop masks, pin placement, and text layout.

This is the single entry point for generating map posters.
"""

import json
import os
import time

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import osmnx as ox
from shapely.ops import unary_union

from engine.crop_masks import apply_circle_crop, apply_house_crop, apply_heart_crop
from engine.map_engine import (
    REFERENCE_DIST,
    fetch_all_osm_data,
    get_crop_limits,
    render_aeroway,
    render_buildings,
    render_landuse,
    render_landuse_misc,
    render_leisure_extra,
    render_natural_areas,
    render_ocean,
    render_paper_texture,
    render_parks,
    render_railways,
    render_residential,
    render_water,
    render_waterway_lines,
    render_wetlands,
)
from engine.ocean import build_ocean_polygons, refine_ocean_with_harbors
from engine.pin_renderer import render_pin
from engine.roads import render_roads
from engine.text_layout import get_zone_positions, render_bottom_text, render_date_night_text, render_top_label
from export.output_sizes import get_size_config
from utils.geocoding import extract_city_state, parse_location
from utils.logging import safe_print

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEMES_DIR = os.path.join(PROJECT_DIR, "themes")
FONTS_DIR = os.path.join(PROJECT_DIR, "fonts")
POSTERS_DIR = os.path.join(PROJECT_DIR, "posters")
GELATO_DIR = os.path.join(PROJECT_DIR, "gelato_ready")
FILE_ENCODING = "utf-8"


def load_theme(theme_name: str = "37th_parallel") -> dict:
    """Load a theme from JSON file. Falls back to terracotta if not found."""
    theme_path = os.path.join(THEMES_DIR, f"{theme_name}.json")
    if os.path.exists(theme_path):
        with open(theme_path, "r", encoding=FILE_ENCODING) as f:
            theme = json.load(f)
        theme.setdefault("id", theme_name)
        return theme

    # Fallback to terracotta
    fallback = os.path.join(THEMES_DIR, "terracotta.json")
    if os.path.exists(fallback):
        safe_print(f"[!] Theme '{theme_name}' not found, using terracotta")
        with open(fallback, "r", encoding=FILE_ENCODING) as f:
            theme = json.load(f)
        theme.setdefault("id", "terracotta")
        return theme

    # Hard-coded minimal fallback
    safe_print(f"[!] No theme files found, using built-in defaults")
    return {
        "id": "default",
        "name": "Default",
        "bg": "#F5EDE4",
        "text": "#8B4513",
        "gradient_color": "#F5EDE4",
        "water": "#A8C4C4",
        "parks": "#E8E0D0",
        "road_motorway": "#A0522D",
        "road_primary": "#B8653A",
        "road_secondary": "#C9846A",
        "road_tertiary": "#D9A08A",
        "road_residential": "#E5C4B0",
        "road_default": "#D9A08A",
    }


def get_available_themes() -> list[dict]:
    """List all available themes with their color data."""
    themes = []
    if not os.path.exists(THEMES_DIR):
        return themes
    for fname in sorted(os.listdir(THEMES_DIR)):
        if not fname.endswith(".json"):
            continue
        theme_id = fname[:-5]
        fpath = os.path.join(THEMES_DIR, fname)
        try:
            with open(fpath, "r", encoding=FILE_ENCODING) as f:
                data = json.load(f)
            data["id"] = theme_id
            themes.append(data)
        except (OSError, json.JSONDecodeError):
            continue
    return themes


def render_poster(
    location: str,
    theme: str = "37th_parallel",
    size: str = "16x20",
    crop: str = "full",
    detail_layers: bool = True,
    distance: int | None = None,
    pin_lat: float | None = None,
    pin_lon: float | None = None,
    pin_style: int = 1,
    pin_color: str | None = None,
    font_preset: int = 1,
    text_line_1: str | None = None,
    text_line_2: str | None = None,
    text_line_3: str | None = None,
    dpi: int = 300,
    output_path: str | None = None,
    border: bool = False,
    map_only: bool = False,
    layout: str = "default",
    text_line_4: str | None = None,
) -> str:
    """Generate a complete map poster.

    Args:
        location: City name ("New York") or lat/lon ("40.7128,-74.0060")
        theme: Theme name (filename without .json)
        size: Print size ("8x10", "11x14", "16x20", "18x24", "24x36")
        crop: Crop shape ("full", "circle", "heart", "house")
        detail_layers: If True, render all 11 layers; if False, minimal (roads+water+parks)
        distance: Map radius in meters (auto from size if None)
        pin_lat: Latitude of pin marker (from frontend geocoding)
        pin_lon: Longitude of pin marker (from frontend geocoding)
        pin_style: 1=heart, 2=heart-pin, 3=classic, 4=house, 5=grad cap
        pin_color: Custom hex color for pin
        font_preset: Font preset (1-5)
        text_line_1: Large title text
        text_line_2: Medium subtitle text
        text_line_3: Small detail text
        dpi: Resolution (300 for print, 72 for preview)
        output_path: Output file path (auto-generated if None)
        border: Add double-line border

    Returns:
        Path to the saved poster file.
    """
    t_start = time.time()

    # 1. Parse location, geocode
    safe_print(f"\n{'='*60}")
    safe_print("MapGen — Poster Renderer")
    safe_print(f"{'='*60}")

    # Renderer dispatch — route to dedicated renderers before existing pipeline
    theme_data = load_theme(theme)
    renderer_type = theme_data.get("renderer")
    if renderer_type == "florence":
        from engine.florence_renderer import render_florence_poster
        return render_florence_poster(
            location=location, theme_data=theme_data, size=size,
            dpi=dpi, output_path=output_path, distance=distance,
            map_only=map_only,
        )
    elif renderer_type == "nordic":
        from engine.nordic_renderer import render_nordic_poster
        return render_nordic_poster(
            location=location, theme_data=theme_data, size=size,
            dpi=dpi, output_path=output_path, distance=distance,
            map_only=map_only,
        )
    elif renderer_type is not None:
        raise ValueError(f"Unknown renderer type: {renderer_type}")

    # 1. Parse location, geocode
    lat, lon, geocode_result = parse_location(location)
    point = (lat, lon)

    city_name, state_name = extract_city_state(geocode_result)
    if city_name is None:
        city_name = location.split(",")[0].strip()

    safe_print(f"  Location: {city_name} ({lat:.4f}, {lon:.4f})")

    # 2. Get size config, set up figure with zones
    size_config = get_size_config(size)
    width_in = size_config["width_in"]
    height_in = size_config["height_in"]
    if distance is None:
        distance = size_config["distance_m"]

    safe_print(f"  Size: {size} ({width_in}x{height_in} in)")
    safe_print(f"  Distance: {distance}m")
    safe_print(f"  Theme: {theme}")
    safe_print(f"  Crop: {crop}")
    safe_print(f"  Detail layers: {detail_layers}")
    safe_print(f"  DPI: {dpi}")

    # Determine if any text lines are provided
    has_text = any([text_line_1, text_line_2, text_line_3])
    # Default text: use city name and state if no custom text
    if not has_text and not map_only:
        text_line_1 = city_name
        if state_name:
            text_line_2 = state_name

    zones = get_zone_positions(has_top_label=False, layout=layout)

    fig = plt.figure(figsize=(width_in, height_in), facecolor="#FFFFFF")
    if map_only:
        # Map fills entire canvas — no margins, no text zone
        ax = fig.add_axes([0, 0, 1, 1])
    else:
        ax = fig.add_axes(zones["map"])
    ax.set_facecolor(theme_data["bg"])

    # 3. Fetch OSM data
    safe_print("\nFetching OSM data...")
    osm_data = fetch_all_osm_data(point, distance, theme_data,
                                   detail_layers=detail_layers)

    # 4. Project to CRS, compute crop limits, lock axes
    safe_print("Projecting graph...")
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

    # 5. Render layers (z-order)
    safe_print("\nRendering map layers...")
    # Scale linewidths relative to the reference 16x20 figure size so all
    # layers look consistent across print sizes (8x10 through 24x36).
    ref_diag = (16**2 + 20**2) ** 0.5
    cur_diag = (width_in**2 + height_in**2) ** 0.5
    fig_scale = cur_diag / ref_diag
    zoom_scale = min(1.5, max(0.3, REFERENCE_DIST / distance)) * fig_scale
    compensated_dist = osm_data["compensated_dist"]

    # Ocean (only when theme opts in via "ocean": true)
    if theme_data.get("ocean", False):
        ocean_polys = build_ocean_polygons(
            point, compensated_dist, target_crs, crop_xlim, crop_ylim
        )
        ocean_polys = refine_ocean_with_harbors(
            ocean_polys, osm_data["harbor_structures"], target_crs,
            crop_xlim, crop_ylim,
        )
        render_ocean(ax, ocean_polys, theme_data, zoom_scale)
    else:
        ocean_polys = []

    ocean_union = None
    if ocean_polys:
        try:
            ocean_union = unary_union(ocean_polys)
        except Exception:
            pass

    # Residential landuse (z=0.35, below natural areas)
    if detail_layers:
        render_residential(ax, osm_data["residential"], target_crs,
                           theme_data, ocean_union)

    # Natural areas
    if detail_layers:
        render_natural_areas(ax, osm_data["natural_areas"], target_crs,
                             theme_data, zoom_scale, ocean_union)
        render_wetlands(ax, osm_data["wetlands"], target_crs, theme_data)
        render_landuse_misc(ax, osm_data["landuse_misc"], target_crs,
                            theme_data, ocean_union)

    # Water (always)
    render_water(ax, osm_data["water"], target_crs, theme_data, ocean_union)

    # Waterway lines (detail only)
    if detail_layers:
        render_waterway_lines(ax, osm_data["waterway_lines"], target_crs,
                              theme_data, zoom_scale, ocean_union,
                              osm_data["water"])
        render_landuse(ax, osm_data["landuse"], target_crs, theme_data, ocean_union)

    # Leisure extras — pitch, garden, playground (z=0.75, between landuse and parks)
    if detail_layers:
        render_leisure_extra(ax, osm_data["leisure_extra"], target_crs,
                             theme_data, ocean_union)

    # Parks (always)
    render_parks(ax, osm_data["parks"], target_crs, theme_data)

    # Buildings (detail only)
    if detail_layers:
        render_buildings(ax, osm_data["buildings"], target_crs, theme_data)

    # Roads (always)
    gdf_edges_full = ox.graph_to_gdfs(g_proj, nodes=False)
    render_roads(ax, gdf_edges_full, theme_data, distance, fig_scale=fig_scale)

    # Railways (detail only)
    if detail_layers:
        render_railways(ax, osm_data["railways"], target_crs, theme_data,
                        zoom_scale, ocean_union)

    # Aeroway features — runways, taxiways, aprons, terminals
    if detail_layers:
        render_aeroway(ax, osm_data["aeroway"], target_crs, theme_data,
                       zoom_scale, ocean_union)

    # Paper texture (skip for low-res previews — invisible at 72 DPI)
    if dpi > 72:
        render_paper_texture(ax, theme_data)

    # 6. Apply crop mask
    if crop == "circle":
        safe_print("\nApplying circle crop...")
        apply_circle_crop(ax, fig, bg_color="#FFFFFF")
    elif crop == "heart":
        safe_print("\nApplying heart crop...")
        h_scale = 0.98 if layout == "date_night" else 1.0
        apply_heart_crop(ax, fig, bg_color="#FFFFFF", heart_scale=h_scale)
    elif crop == "house":
        safe_print("\nApplying house crop...")
        apply_house_crop(ax, fig, bg_color="#FFFFFF")

    # 7. Place pin
    if pin_lat is not None and pin_lon is not None:
        safe_print("\nPlacing pin marker...")
        try:
            render_pin(ax, pin_lat, pin_lon, target_crs,
                       pin_style=pin_style, pin_color=pin_color)
        except Exception as e:
            safe_print(f"  [!] Pin rendering failed: {e}")

    # 8. Render text zones (skip in map_only mode)
    if not map_only:
        safe_print("\nRendering text...")
        scale_factor = min(height_in, width_in) / 12.0

        if layout == "date_night":
            render_date_night_text(
                fig, scale_factor=scale_factor, font_preset=font_preset,
                text_line_1=text_line_1, text_line_2=text_line_2,
                text_line_3=text_line_3, text_line_4=text_line_4,
            )
        else:
            render_bottom_text(
                fig, city_name, state_name, True, point,
                None, None, theme,
                scale_factor=scale_factor, font_preset=font_preset,
                text_line_1=text_line_1, text_line_2=text_line_2, text_line_3=text_line_3,
            )
    else:
        safe_print("\nMap-only mode — skipping text")

    # Optional border
    if border:
        border_color = theme_data.get("text", "#000000")
        rect_outer = plt.Rectangle(
            (0.02, 0.02), 0.96, 0.96,
            transform=ax.transAxes, linewidth=2.5,
            edgecolor=border_color, facecolor='none', zorder=12,
        )
        ax.add_patch(rect_outer)
        rect_inner = plt.Rectangle(
            (0.025, 0.025), 0.95, 0.95,
            transform=ax.transAxes, linewidth=0.8,
            edgecolor=border_color, facecolor='none', zorder=12,
        )
        ax.add_patch(rect_inner)

    # Re-apply axes position
    if map_only:
        ax.set_position([0, 0, 1, 1])
    else:
        ax.set_position(zones["map"])

    safe_print(f"  Layout: {layout}")

    # 9. Save as RGB PNG at target DPI
    if output_path is None:
        os.makedirs(POSTERS_DIR, exist_ok=True)
        city_slug = city_name.lower().replace(" ", "_") if city_name else "map"
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(POSTERS_DIR, f"{city_slug}_{theme}_{size}_{timestamp}.png")

    os.makedirs(os.path.dirname(output_path) or POSTERS_DIR, exist_ok=True)
    safe_print(f"\nSaving to {output_path}...")

    # Render to in-memory buffer, convert RGBA->RGB once, save
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

    return output_path
