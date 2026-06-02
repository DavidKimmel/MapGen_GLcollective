"""Blueprint renderer — shaded monochrome mosaic with detailed road overlay.

Style: 8 shades of one hue for city blocks, white roads overlay, white water.
Layout (top to bottom):
- Top margin
- City name (right-aligned, Montserrat Bold, lowercase)
- State/country (right-aligned, Montserrat Bold smaller, lowercase)
- Blocky swatch bar (palette segments, exact map width, coords in left block)
- Map (solid, same width as swatch bar)
- Bottom margin

Fonts: Montserrat Bold (city + state), Roboto Regular (coords in swatch bar).
Established from layoutv3c iteration (2026-03-25).
"""

import gc
import os
import random
import sys
from typing import Optional

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import osmnx as ox
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Point, box, LineString
from shapely.ops import polygonize, unary_union

_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_ENGINE_DIR)
FONTS_DIR = os.path.join(_PROJECT_DIR, "fonts")

sys.path.insert(0, _PROJECT_DIR) if _PROJECT_DIR not in sys.path else None

from engine.florence_renderer import DROP_HIGHWAY, WATER_TAGS, _road_weight
from export.output_sizes import get_size_config
from utils.logging import safe_print

# ─── COLOR PALETTES ──────────────────────────────────────────────────────────

PALETTES: dict[str, dict] = {
    "navy": {
        "shades": [
            "#0A1628", "#132744", "#1C3D6E", "#2B5EA2",
            "#3A7BD5", "#5B9BD5", "#8BB8E8", "#B5D4F0",
        ],
        "text_color": "#0A1628",
    },
    "forest": {
        "shades": [
            "#0B1F0B", "#1A3A1A", "#2A5A2A", "#3B7A3B",
            "#4E944E", "#6BAF6B", "#8FCA8F", "#B5DEB5",
        ],
        "text_color": "#0B1F0B",
    },
    "terracotta": {
        "shades": [
            "#4A1A0A", "#6B2E14", "#8C4422", "#A85A35",
            "#C4734D", "#D4906B", "#E4AD8E", "#F0CAB5",
        ],
        "text_color": "#4A1A0A",
    },
    "charcoal": {
        "shades": [
            "#1A1A1A", "#2D2D2D", "#404040", "#555555",
            "#6E6E6E", "#8A8A8A", "#A3A3A3", "#BFBFBF",
        ],
        "text_color": "#1A1A1A",
    },
}

# Font paths
CITY_FONT = os.path.join(FONTS_DIR, "Montserrat-Bold.ttf")
COORD_FONT = os.path.join(FONTS_DIR, "Roboto-Regular.ttf")


# ─── MAP RENDERING ───────────────────────────────────────────────────────────

def detect_extent(lat: float, lon: float, probe_radius: int = 3000) -> int:
    """Probe city density via OSM edge count to determine extent radius.

    Dense cities (Paris, Rome) get wider extent, sparse cities stay tight.
    """
    try:
        G = ox.graph_from_point((lat, lon), dist=probe_radius, network_type="drive")
        edge_count = len(G.edges)
    except Exception:
        return 3000

    if edge_count > 12000:
        radius = 4000  # mega-dense (Paris, Manhattan, Rome)
    elif edge_count > 8000:
        radius = 3500  # dense (Berlin, Amsterdam)
    elif edge_count > 5000:
        radius = 3000  # medium (Chicago, Prague)
    else:
        radius = 2500  # smaller/sparser (Nashville)

    safe_print(f"  Probe: {edge_count} drive edges at {probe_radius}m → extent {radius}m")
    return radius


def render_shaded_map(
    lat: float,
    lon: float,
    radius: int,
    palette: list[str],
    dpi: int = 200,
    fig_width: float = 16,
    fig_height: float = 20,
    output_path: str = "",
) -> str:
    """Render shaded polygon map with detailed road overlay.

    Produces a raw map image (no text/layout) suitable for composition.
    """
    random.seed(42)

    aspect = fig_height / fig_width
    radius_x = radius
    radius_y = int(radius * aspect)
    center_pt = Point(lon, lat)
    center_gdf = gpd.GeoDataFrame(geometry=[center_pt], crs="EPSG:4326")
    utm_crs = center_gdf.estimate_utm_crs()
    center_proj = center_gdf.to_crs(utm_crs).geometry[0]
    aoi_box = box(
        center_proj.x - radius_x, center_proj.y - radius_y,
        center_proj.x + radius_x, center_proj.y + radius_y,
    )

    fetch_radius = int(max(radius_x, radius_y) * 1.25)
    safe_print("  Fetching streets...")
    G = ox.graph_from_point((lat, lon), dist=fetch_radius, network_type="all")
    all_edges = ox.graph_to_gdfs(G, nodes=False).to_crs(utm_crs)
    all_edges = gpd.clip(all_edges, aoi_box)

    # Filtered edges for polygonize (skip minor paths)
    edges = all_edges.copy()
    if "highway" in edges.columns:
        edges = edges[~edges["highway"].apply(
            lambda h: str(h).lower() in DROP_HIGHWAY if h is not None else False
        )].copy()

    # All edges for road overlay
    all_edges["lw"] = all_edges.apply(_road_weight, axis=1)
    if "highway" in all_edges.columns:
        extra_mask = all_edges["highway"].apply(
            lambda h: str(h).lower() in DROP_HIGHWAY if h is not None else False
        )
        all_edges.loc[extra_mask, "lw"] = 0.15

    aoi_boundary = LineString(aoi_box.exterior.coords)
    safe_print("  Polygonizing...")
    all_lines = unary_union(list(edges.geometry) + [aoi_boundary])
    block_polys = list(polygonize(all_lines))
    blocks = gpd.GeoDataFrame(geometry=block_polys, crs=utm_crs)
    blocks = gpd.clip(blocks, aoi_box)
    blocks = blocks[blocks.geometry.area >= 500].copy()
    blocks["color"] = [random.choice(palette) for _ in range(len(blocks))]
    safe_print(f"  {len(blocks)} blocks")

    # Water
    safe_print("  Fetching water...")
    try:
        water = ox.features_from_point((lat, lon), WATER_TAGS, dist=fetch_radius)
        water = water[water.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
        water = water.to_crs(utm_crs)
        water = gpd.clip(water, aoi_box)
        has_water = len(water) > 0
    except Exception:
        has_water = False

    # Ocean
    try:
        from engine.ocean import build_ocean_polygons
        crop_xlim = (center_proj.x - radius_x, center_proj.x + radius_x)
        crop_ylim = (center_proj.y - radius_y, center_proj.y + radius_y)
        ocean_polys = build_ocean_polygons(
            (lat, lon), max(radius_x, radius_y), utm_crs, crop_xlim, crop_ylim
        )
    except Exception:
        ocean_polys = []

    # Render
    safe_print("  Rendering...")
    fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height))
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    ax.set_aspect("equal")
    ax.axis("off")

    base_gdf = gpd.GeoDataFrame(geometry=[aoi_box], crs=utm_crs)
    base_gdf.plot(ax=ax, color=random.choice(palette), edgecolor="none", zorder=0)

    if ocean_polys:
        gpd.GeoDataFrame(geometry=ocean_polys, crs=utm_crs).plot(
            ax=ax, color="#FFFFFF", edgecolor="none", zorder=0.5
        )

    blocks.plot(ax=ax, color=blocks["color"], edgecolor="none", zorder=1)

    if has_water:
        water.plot(ax=ax, color="#FFFFFF", edgecolor="none", zorder=3)

    for lw_val, group in all_edges.groupby("lw"):
        group.plot(ax=ax, color="#FFFFFF", linewidth=lw_val, alpha=1.0, zorder=4)

    ax.set_xlim(center_proj.x - radius_x, center_proj.x + radius_x)
    ax.set_ylim(center_proj.y - radius_y, center_proj.y + radius_y)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight", pad_inches=0, facecolor="#FFFFFF")
    plt.close(fig)
    gc.collect()
    return output_path


# ─── LAYOUT COMPOSITION (v3c — blocky swatch bar) ────────────────────────────

def compose_blueprint_poster(
    map_image_path: str,
    city_name: str,
    state_or_region: str,
    lat: float,
    lon: float,
    palette: list[str],
    text_color: str,
    size_name: str = "16x20",
    dpi: int = 200,
    output_path: Optional[str] = None,
    strip_header: bool = False,
) -> str:
    """Compose a Blueprint poster with blocky swatch bar layout.

    Layout: city name top-right → state below → blocky swatch bar with coords
    in leftmost block → map flush below.
    """
    ps = get_size_config(size_name)
    total_w = int(ps["width_in"] * dpi)
    total_h = int(ps["height_in"] * dpi)
    margin_x = int(total_w * 0.05)

    # Layout proportions
    top_margin = int(total_h * 0.06)
    city_font_size = int(total_h * 0.065)
    state_font_size = int(total_h * 0.022)
    swatch_height = int(total_h * 0.022)
    swatch_gap = int(total_w * 0.004)
    coord_font_size = int(swatch_height * 0.55)

    # Fonts
    city_font = ImageFont.truetype(CITY_FONT, city_font_size)
    state_font = ImageFont.truetype(CITY_FONT, state_font_size)
    coord_font = ImageFont.truetype(COORD_FONT, coord_font_size)

    canvas = Image.new("RGB", (total_w, total_h), "#FFFFFF")
    draw = ImageDraw.Draw(canvas)
    right_edge = total_w - margin_x
    map_w = total_w - (2 * margin_x)

    # City name (right-aligned, lowercase)
    city_text = city_name.lower()
    bbox = draw.textbbox((0, 0), city_text, font=city_font)
    city_text_w = bbox[2] - bbox[0]
    city_text_h = bbox[3] - bbox[1]
    city_y = top_margin
    draw.text((right_edge - city_text_w, city_y), city_text, fill=text_color, font=city_font)

    # State/country (right-aligned, lowercase)
    gap_city_state = int(total_h * 0.02)
    state_text = state_or_region.lower()
    bbox = draw.textbbox((0, 0), state_text, font=state_font)
    state_text_w = bbox[2] - bbox[0]
    state_text_h = bbox[3] - bbox[1]
    state_y = city_y + city_text_h + gap_city_state
    draw.text((right_edge - state_text_w, state_y), state_text, fill=text_color, font=state_font)

    # Blocky swatch bar — exact map width, coords in leftmost block
    gap_state_bar = int(total_h * 0.015)
    swatch_y = state_y + state_text_h + gap_state_bar

    coord_text = f"{abs(lat):.4f}\u00b0{'N' if lat >= 0 else 'S'}  {abs(lon):.4f}\u00b0{'E' if lon >= 0 else 'W'}"
    coord_bbox = draw.textbbox((0, 0), coord_text, font=coord_font)
    coord_text_w = coord_bbox[2] - coord_bbox[0]
    coord_text_h = coord_bbox[3] - coord_bbox[1]
    coord_ascent = coord_bbox[1]
    coord_block_w = coord_text_w + int(map_w * 0.04)

    # Draw coord block (leftmost, darkest shade)
    x_cursor = margin_x
    draw.rectangle(
        [x_cursor, swatch_y, x_cursor + coord_block_w, swatch_y + swatch_height],
        fill=palette[0],
    )
    cx = x_cursor + int(map_w * 0.02)
    cy = swatch_y + (swatch_height - coord_text_h) // 2 - coord_ascent
    draw.text((cx, cy), coord_text, fill="#FFFFFF", font=coord_font)
    x_cursor += coord_block_w + swatch_gap

    # Remaining palette blocks — fit exactly to map right edge
    max_right = margin_x + map_w
    remaining_for_blocks = max_right - x_cursor
    num_blocks = len(palette)
    block_gaps = swatch_gap * (num_blocks - 1)
    block_total = remaining_for_blocks - block_gaps

    random.seed(len(city_name) + 7)
    raw_w = [random.uniform(0.5, 2.0) for _ in palette]
    total_r = sum(raw_w)
    widths = [int((w / total_r) * block_total) for w in raw_w]
    used = sum(widths) + block_gaps
    widths[-1] += (remaining_for_blocks - used)

    for i, color in enumerate(palette):
        x0 = x_cursor
        x1 = x_cursor + widths[i]
        draw.rectangle([x0, swatch_y, x1, swatch_y + swatch_height], fill=color)
        x_cursor = x1 + swatch_gap

    # Map — crop content bounds from raw matplotlib output then paste
    gap_bar_map = int(total_h * 0.012)
    map_top = swatch_y + swatch_height + gap_bar_map
    map_h = total_h - map_top - margin_x

    existing = Image.open(map_image_path).convert("RGB")

    # If input is an already-composited poster (has header/bar), crop it out
    if strip_header:
        ex_w, ex_h = existing.size
        crop_top = int(ex_h * 0.22)
        existing = existing.crop((0, crop_top, ex_w, ex_h))

    # Resize map to fill the poster map area — same width as swatch bar
    map_region = existing.resize((map_w, map_h), Image.LANCZOS)
    canvas.paste(map_region, (margin_x, map_top))

    if output_path is None:
        output_path = map_image_path.replace(".png", "_poster.png")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    canvas.save(output_path, dpi=(dpi, dpi))
    size_mb = os.path.getsize(output_path) / 1e6
    safe_print(f"  Poster: {output_path} ({size_mb:.1f} MB)")
    return output_path


# ─── FULL PIPELINE ────────────────────────────────────────────────────────────

def render_blueprint(
    city_name: str,
    state_or_region: str,
    lat: float,
    lon: float,
    color_name: str,
    size_name: str = "16x20",
    dpi: int = 200,
    output_path: Optional[str] = None,
    radius: Optional[int] = None,
) -> str:
    """Full pipeline: render raw map → compose poster layout.

    Args:
        city_name: Display name (e.g. "Amsterdam")
        state_or_region: State or country (e.g. "Netherlands")
        lat, lon: Center coordinates
        color_name: Palette key ("navy", "forest", "terracotta", "charcoal")
        size_name: Print size (default "16x20")
        dpi: Output DPI (default 200)
        output_path: Final output path (auto-generated if None)
        radius: Override extent radius (auto-detected if None)

    Returns:
        Path to the final poster image.
    """
    palette_data = PALETTES[color_name]
    slug = city_name.lower().replace(" ", "_")

    if output_path is None:
        output_path = os.path.join(
            "etsy", "renders", "GradientMap",
            f"{slug}_{color_name}_{size_name}.png",
        )

    if radius is None:
        radius = detect_extent(lat, lon)

    ps = get_size_config(size_name)
    fig_w = ps["width_in"]
    fig_h = ps["height_in"]

    # Render raw map to temp file
    tmp_map = output_path.replace(".png", "_raw.png")
    render_shaded_map(
        lat=lat, lon=lon, radius=radius,
        palette=palette_data["shades"],
        dpi=dpi, fig_width=fig_w, fig_height=fig_h,
        output_path=tmp_map,
    )

    # Compose poster layout
    compose_blueprint_poster(
        map_image_path=tmp_map,
        city_name=city_name,
        state_or_region=state_or_region,
        lat=lat, lon=lon,
        palette=palette_data["shades"],
        text_color=palette_data["text_color"],
        size_name=size_name, dpi=dpi,
        output_path=output_path,
    )

    # Clean up temp
    if os.path.exists(tmp_map):
        os.remove(tmp_map)

    return output_path
