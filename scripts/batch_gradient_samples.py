"""Render gradient/shaded mosaic samples — auto-sized extents per city.

Detects city density via OSM edge count at a probe radius to determine
tight vs wide extent. Dense cities (Paris, Rome) get wider, smaller
cities (Nashville, Dublin) get tighter.

Output: etsy/renders/GradientMap/{slug}_{color}_16x20.png
"""

import gc
import os
import random
import sys

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import osmnx as ox
from shapely.geometry import Point, box, LineString
from shapely.ops import polygonize, unary_union

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from engine.florence_renderer import DROP_HIGHWAY, WATER_TAGS, _road_weight
from engine.florence_text_layout import _load_font
from export.output_sizes import get_size_config
from utils.logging import safe_print

from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = os.path.join(PROJECT_ROOT, "fonts")
OUT_DIR = os.path.join("etsy", "renders", "GradientMap")
DPI = 200
SIZE = "16x20"

# ─── COLOR PALETTES (shades of one hue) ──────────────────────────────────────

PALETTES: dict[str, dict] = {
    "navy": {
        "shades": [
            "#0A1628", "#132744", "#1C3D6E", "#2B5EA2",
            "#3A7BD5", "#5B9BD5", "#8BB8E8", "#B5D4F0",
        ],
        "text_color": "#0A1628",
        "bar_color": "#0A1628",
    },
    "forest": {
        "shades": [
            "#0B1F0B", "#1A3A1A", "#2A5A2A", "#3B7A3B",
            "#4E944E", "#6BAF6B", "#8FCA8F", "#B5DEB5",
        ],
        "text_color": "#0B1F0B",
        "bar_color": "#0B1F0B",
    },
    "terracotta": {
        "shades": [
            "#4A1A0A", "#6B2E14", "#8C4422", "#A85A35",
            "#C4734D", "#D4906B", "#E4AD8E", "#F0CAB5",
        ],
        "text_color": "#4A1A0A",
        "bar_color": "#4A1A0A",
    },
    "charcoal": {
        "shades": [
            "#1A1A1A", "#2D2D2D", "#404040", "#555555",
            "#6E6E6E", "#8A8A8A", "#A3A3A3", "#BFBFBF",
        ],
        "text_color": "#1A1A1A",
        "bar_color": "#1A1A1A",
    },
}

# ─── CITIES ───────────────────────────────────────────────────────────────────

CITIES: list[dict] = [
    {"name": "Paris", "state": "France", "lat": 48.8566, "lon": 2.3522, "slug": "paris"},
    {"name": "Nashville", "state": "Tennessee", "lat": 36.1627, "lon": -86.7816, "slug": "nashville"},
    {"name": "Berlin", "state": "Germany", "lat": 52.5163, "lon": 13.3777, "slug": "berlin"},
    {"name": "Rome", "state": "Italy", "lat": 41.8992, "lon": 12.4731, "slug": "rome"},
    {"name": "Chicago", "state": "Illinois", "lat": 41.8827, "lon": -87.6233, "slug": "chicago"},
    {"name": "Amsterdam", "state": "Netherlands", "lat": 52.3676, "lon": 4.9041, "slug": "amsterdam"},
    {"name": "Manhattan", "state": "New York", "lat": 40.7580, "lon": -73.9770, "slug": "manhattan"},
    {"name": "Prague", "state": "Czech Republic", "lat": 50.0755, "lon": 14.4378, "slug": "prague"},
]


def detect_extent(lat: float, lon: float, probe_radius: int = 3000) -> int:
    """Probe city density and return appropriate extent radius.

    Counts edges in a small probe area. Dense cities get wider extent
    so more of the city is visible. Sparse cities stay tight.
    """
    try:
        G = ox.graph_from_point((lat, lon), dist=probe_radius, network_type="drive")
        edge_count = len(G.edges)
    except Exception:
        return 3000  # fallback

    # Thresholds based on testing:
    # Paris/Rome ~15k+ edges at 3km → very dense, need 3500-4000m
    # Berlin/Amsterdam ~8-12k → medium, 3000-3500m
    # Nashville ~4-6k → smaller, 2500-3000m
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
    lat: float, lon: float, radius: int,
    palette: list[str],
    dpi: int = 200,
    fig_width: float = 16, fig_height: float = 20,
    output_path: str = "",
) -> str:
    """Render shaded polygon map with detailed road overlay."""
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

    # Filtered for polygonize
    edges = all_edges.copy()
    if "highway" in edges.columns:
        edges = edges[~edges["highway"].apply(
            lambda h: str(h).lower() in DROP_HIGHWAY if h is not None else False
        )].copy()

    # All edges for overlay
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

    safe_print("  Fetching water...")
    try:
        water = ox.features_from_point((lat, lon), WATER_TAGS, dist=fetch_radius)
        water = water[water.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
        water = water.to_crs(utm_crs)
        water = gpd.clip(water, aoi_box)
        has_water = len(water) > 0
    except Exception:
        has_water = False

    try:
        from engine.ocean import build_ocean_polygons
        crop_xlim = (center_proj.x - radius_x, center_proj.x + radius_x)
        crop_ylim = (center_proj.y - radius_y, center_proj.y + radius_y)
        ocean_polys = build_ocean_polygons(
            (lat, lon), max(radius_x, radius_y), utm_crs, crop_xlim, crop_ylim
        )
    except Exception:
        ocean_polys = []

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


def compose_poster(
    map_image_path: str,
    city_name: str, state_or_region: str,
    lat: float, lon: float,
    text_color: str, bar_color: str,
    size_name: str = "16x20", dpi: int = 200,
    output_path: str = "",
) -> str:
    """Compose poster: title top-right, fading bar with coords, solid map."""
    ps = get_size_config(size_name)
    total_w = int(ps["width_in"] * dpi)
    total_h = int(ps["height_in"] * dpi)
    margin_x = int(total_w * 0.05)

    top_margin = int(total_h * 0.05)
    city_font_size = int(total_h * 0.065)
    region_font_size = int(total_h * 0.018)
    bar_height = int(total_h * 0.025)
    coord_font_size = int(bar_height * 0.7)

    font_path = os.path.join(FONTS_DIR, "Switzer-Bold.ttf")
    coord_font_path = os.path.join(FONTS_DIR, "Roboto-Light.ttf")
    try:
        city_font = ImageFont.truetype(font_path, city_font_size)
    except OSError:
        city_font = ImageFont.load_default()
    try:
        region_font = ImageFont.truetype(font_path, region_font_size)
    except OSError:
        region_font = ImageFont.load_default()
    try:
        coord_font = ImageFont.truetype(coord_font_path, coord_font_size)
    except OSError:
        coord_font = ImageFont.load_default()

    canvas = Image.new("RGB", (total_w, total_h), "#FFFFFF")
    draw = ImageDraw.Draw(canvas)
    right_edge = total_w - margin_x

    # City name
    city_text = city_name.lower()
    bbox = draw.textbbox((0, 0), city_text, font=city_font)
    city_text_w = bbox[2] - bbox[0]
    city_text_h = bbox[3] - bbox[1]
    city_y = top_margin
    draw.text((right_edge - city_text_w, city_y), city_text, fill=text_color, font=city_font)

    # State/country
    state_y = city_y + city_text_h + int(total_h * 0.015)
    if state_or_region:
        state_text = state_or_region.lower()
        bbox = draw.textbbox((0, 0), state_text, font=region_font)
        state_text_w = bbox[2] - bbox[0]
        state_text_h = bbox[3] - bbox[1]
        draw.text((right_edge - state_text_w, state_y), state_text, fill=text_color, font=region_font)
        bar_y = state_y + state_text_h + int(total_h * 0.012)
    else:
        bar_y = state_y + int(total_h * 0.012)

    # Fading bar (solid left → transparent right) with coordinates
    bar_width = total_w - (2 * margin_x)
    bar_img = Image.new("RGBA", (bar_width, bar_height), (0, 0, 0, 0))
    bar_draw = ImageDraw.Draw(bar_img)

    tc = bar_color.lstrip("#")
    r, g, b = int(tc[0:2], 16), int(tc[2:4], 16), int(tc[4:6], 16)

    for x in range(bar_width):
        alpha = int(255 * (1.0 - x / bar_width))
        bar_draw.line([(x, 0), (x, bar_height - 1)], fill=(r, g, b, alpha))

    coord_text = f"{abs(lat):.4f}\u00b0{'N' if lat >= 0 else 'S'}  {abs(lon):.4f}\u00b0{'E' if lon >= 0 else 'W'}"
    coord_bbox = bar_draw.textbbox((0, 0), coord_text, font=coord_font)
    coord_w = coord_bbox[2] - coord_bbox[0]
    coord_h = coord_bbox[3] - coord_bbox[1]
    coord_ascent = coord_bbox[1]
    coord_x = int(bar_width * 0.02)
    coord_y = (bar_height - coord_h) // 2 - coord_ascent
    bar_draw.text((coord_x, coord_y), coord_text, fill=(255, 255, 255, 255), font=coord_font)

    canvas.paste(bar_img, (margin_x, bar_y), bar_img)

    # Map
    map_top = bar_y + bar_height + int(total_h * 0.015)
    map_x = margin_x
    map_w = total_w - (2 * margin_x)
    map_h = total_h - map_top - margin_x

    map_img = Image.open(map_image_path).convert("RGB")
    map_img = map_img.resize((map_w, map_h), Image.LANCZOS)
    canvas.paste(map_img, (map_x, map_top))

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    canvas.save(output_path, dpi=(dpi, dpi))
    size_mb = os.path.getsize(output_path) / 1e6
    safe_print(f"  Poster: {output_path} ({size_mb:.1f} MB)")
    return output_path


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # First pass: detect extents for all cities
    print(f"\nDetecting city extents...\n")
    extents: dict[str, int] = {}
    for city in CITIES:
        print(f"  {city['name']}:")
        extents[city["slug"]] = detect_extent(city["lat"], city["lon"])

    total = len(CITIES) * len(PALETTES)
    count = 0

    print(f"\nRendering {len(CITIES)} cities x {len(PALETTES)} colors = {total} posters")
    print(f"Output: {OUT_DIR}/\n")

    for city in CITIES:
        radius = extents[city["slug"]]
        for color_name, pal in PALETTES.items():
            count += 1
            print(f"\n[{count}/{total}] {city['name']} — {color_name} ({radius}m)")

            tmp_map = os.path.join(OUT_DIR, f"_tmp_{city['slug']}_{color_name}.png")
            out_path = os.path.join(OUT_DIR, f"{city['slug']}_{color_name}_{SIZE}.png")

            if os.path.exists(out_path):
                print(f"  Exists — skipping")
                continue

            render_shaded_map(
                lat=city["lat"], lon=city["lon"], radius=radius,
                palette=pal["shades"],
                dpi=DPI, fig_width=16, fig_height=20,
                output_path=tmp_map,
            )

            compose_poster(
                map_image_path=tmp_map,
                city_name=city["name"],
                state_or_region=city["state"],
                lat=city["lat"], lon=city["lon"],
                text_color=pal["text_color"],
                bar_color=pal["bar_color"],
                size_name=SIZE, dpi=DPI,
                output_path=out_path,
            )

            if os.path.exists(tmp_map):
                os.remove(tmp_map)

    file_count = len([f for f in os.listdir(OUT_DIR) if f.endswith(".png") and not f.startswith("_")])
    print(f"\nDone! {file_count} files in {OUT_DIR}/")


if __name__ == "__main__":
    main()
