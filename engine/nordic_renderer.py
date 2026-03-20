"""Nordic-style monochromatic street network map renderer.

Steel blue background, white streets and water, blue-green parks.
Simple, clean, Scandinavian aesthetic.
"""

import gc
import io
import os
import time

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import osmnx as ox
from PIL import Image
from shapely.geometry import Point, box

from engine.text_layout import get_zone_positions, render_bottom_text
from export.output_sizes import get_size_config
from utils.geocoding import extract_city_state, parse_location
from utils.logging import safe_print

_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_ENGINE_DIR)
POSTERS_DIR = os.path.join(_PROJECT_DIR, "posters")

# ─── FEATURE TAGS ────────────────────────────────────────────────────────────

WATER_TAGS: dict = {
    "natural": ["water", "bay"],
    "waterway": ["riverbank"],
    "water": True,
}

PARK_TAGS: dict = {
    "leisure": ["park", "garden", "nature_reserve"],
    "landuse": ["forest", "meadow", "grass"],
    "natural": ["wood", "grassland", "scrub"],
}

# ─── DEFAULT STREET WIDTHS ───────────────────────────────────────────────────

DEFAULT_STREET_WIDTHS: dict[str, float] = {
    "motorway": 3.0, "trunk": 3.0, "primary": 2.5, "primary_link": 2.5,
    "motorway_link": 2.0, "secondary": 2.0, "secondary_link": 2.0,
    "tertiary": 1.5, "tertiary_link": 1.0, "cycleway": 0,
    "residential": 0.5, "service": 0, "unclassified": 0,
    "pedestrian": 0, "footway": 0,
}


def _road_width(row, street_widths: dict[str, float]) -> float:
    """Get line width for a road based on highway type."""
    hw = str(row.get("highway", "")).lower() if "highway" in row.index else ""
    for key, width in street_widths.items():
        if key in hw:
            return width
    return 0.0


def render_nordic_map(
    lat: float,
    lon: float,
    radius: int = 5000,
    bg_color: str = "#3A5A78",
    street_color: str = "#FFFFFF",
    water_color: str = "#FFFFFF",
    parks_color: str = "#4A7A6A",
    street_widths: dict[str, float] | None = None,
    dpi: int = 200,
    fig_width: float = 16,
    fig_height: float = 20,
    output_path: str = "",
) -> str:
    """Render a Nordic-style monochrome street map. Returns path as str."""
    if street_widths is None:
        street_widths = DEFAULT_STREET_WIDTHS

    # 1. Compute AOI
    safe_print(f"  Computing AOI for: ({lat:.4f}, {lon:.4f}) r={radius}m...")
    center_pt = Point(lon, lat)
    center_gdf = gpd.GeoDataFrame(geometry=[center_pt], crs="EPSG:4326")
    utm_crs = center_gdf.estimate_utm_crs()
    center_proj = center_gdf.to_crs(utm_crs).geometry[0]
    aoi_box = box(
        center_proj.x - radius, center_proj.y - radius,
        center_proj.x + radius, center_proj.y + radius,
    )

    # 2. Fetch street network
    safe_print("  Fetching street network...")
    G = ox.graph_from_point((lat, lon), dist=radius, network_type="all")
    edges = ox.graph_to_gdfs(G, nodes=False).to_crs(utm_crs)
    edges = gpd.clip(edges, aoi_box)
    edges["lw"] = edges.apply(lambda row: _road_width(row, street_widths), axis=1)
    # Filter out zero-width streets
    edges = edges[edges["lw"] > 0]

    # 3. Fetch water
    safe_print("  Fetching water...")
    try:
        water = ox.features_from_point((lat, lon), WATER_TAGS, dist=radius)
        water = water[water.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
        water = water.to_crs(utm_crs)
        water = gpd.clip(water, aoi_box)
        has_water = len(water) > 0
        safe_print(f"  {len(water)} water features")
    except Exception:
        has_water = False
        safe_print("  No water found")

    # 4. Fetch parks/woodland
    safe_print("  Fetching parks...")
    try:
        parks = ox.features_from_point((lat, lon), PARK_TAGS, dist=radius)
        parks = parks[parks.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
        parks = parks.to_crs(utm_crs)
        parks = gpd.clip(parks, aoi_box)
        has_parks = len(parks) > 0
        safe_print(f"  {len(parks)} park features")
    except Exception:
        has_parks = False
        safe_print("  No parks found")

    # 5. Render
    safe_print("  Rendering Nordic map...")
    fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height))
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    ax.set_aspect("equal")
    ax.axis("off")

    # Parks (zorder 2)
    if has_parks:
        parks.plot(ax=ax, color=parks_color, edgecolor="none", linewidth=0, zorder=2)

    # Water (zorder 2)
    if has_water:
        water.plot(ax=ax, color=water_color, edgecolor="none", linewidth=0, zorder=2)

    # Streets (zorder 5)
    for lw_val, group in edges.groupby("lw"):
        group.plot(ax=ax, color=street_color, linewidth=lw_val, zorder=5)

    bounds = [
        center_proj.x - radius, center_proj.y - radius,
        center_proj.x + radius, center_proj.y + radius,
    ]
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])

    # Save
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight", pad_inches=0, facecolor=bg_color)
    plt.close(fig)
    gc.collect()

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    safe_print(f"  Map saved: {output_path} ({size_mb:.1f} MB)")
    return output_path


def render_nordic_poster(
    location: str,
    theme_data: dict,
    size: str = "16x20",
    dpi: int = 300,
    output_path: str | None = None,
    distance: int | None = None,
    map_only: bool = False,
) -> str:
    """Main entry point for Nordic renderer — called by dispatcher.

    Handles geocoding, renders map, composes poster with text, returns str path.
    """
    t_start = time.time()

    safe_print(f"\n{'='*60}")
    safe_print("MapGen — Nordic Renderer")
    safe_print(f"{'='*60}")

    # Parse location
    lat, lon, geocode_result = parse_location(location)
    city_name, state_name = extract_city_state(geocode_result)
    if city_name is None:
        city_name = location.split(",")[0].strip()

    # Size config
    size_config = get_size_config(size)
    width_in = size_config["width_in"]
    height_in = size_config["height_in"]
    if distance is None:
        distance = size_config["distance_m"]

    safe_print(f"  Location: {city_name} ({lat:.4f}, {lon:.4f})")
    safe_print(f"  Size: {size} ({width_in}x{height_in} in)")
    safe_print(f"  Distance: {distance}m | DPI: {dpi}")

    # Build output path
    if output_path is None:
        os.makedirs(POSTERS_DIR, exist_ok=True)
        city_slug = city_name.lower().replace(" ", "_") if city_name else "map"
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(POSTERS_DIR, f"{city_slug}_nordic_{size}_{timestamp}.png")

    # Colors from theme
    bg_color = theme_data.get("bg_color", "#3A5A78")
    street_color = theme_data.get("street_color", "#FFFFFF")
    water_color = theme_data.get("water_color", "#FFFFFF")
    parks_color = theme_data.get("parks_color", "#4A7A6A")
    poster_bg = theme_data.get("poster_bg", "#FFFFFF")
    text_color = theme_data.get("text_color", "#1A1A1A")
    street_widths = theme_data.get("street_widths", DEFAULT_STREET_WIDTHS)

    if map_only:
        # Return raw map directly
        map_path = render_nordic_map(
            lat=lat, lon=lon, radius=distance,
            bg_color=bg_color, street_color=street_color,
            water_color=water_color, parks_color=parks_color,
            street_widths=street_widths,
            dpi=dpi, fig_width=width_in, fig_height=height_in,
            output_path=output_path,
        )
        elapsed = time.time() - t_start
        safe_print(f"\n[OK] Nordic map-only done! ({elapsed:.1f}s)")
        return map_path

    # Render map to temp file, then compose poster with text
    tmp_map = output_path + ".tmp_map.png"
    render_nordic_map(
        lat=lat, lon=lon, radius=distance,
        bg_color=bg_color, street_color=street_color,
        water_color=water_color, parks_color=parks_color,
        street_widths=street_widths,
        dpi=dpi, fig_width=width_in, fig_height=height_in,
        output_path=tmp_map,
    )

    # Compose poster: white bg, map in map zone, text at bottom
    safe_print("  Composing Nordic poster...")
    zones = get_zone_positions(has_top_label=False, layout="default")

    fig = plt.figure(figsize=(width_in, height_in), facecolor=poster_bg)
    ax = fig.add_axes(zones["map"])
    ax.axis("off")

    # Load rendered map as image and display in axes
    map_img = plt.imread(tmp_map)
    ax.imshow(map_img, aspect="auto", extent=[0, 1, 0, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # Render text
    safe_print("  Rendering text...")
    scale_factor = min(height_in, width_in) / 12.0
    render_bottom_text(
        fig, city_name, state_name, False, (lat, lon),
        None, None, "nordic",
        scale_factor=scale_factor, font_preset=1,
        text_line_1=city_name, text_line_2=state_name,
    )

    ax.set_position(zones["map"])

    # Save as RGB PNG
    safe_print(f"\n  Saving to {output_path}...")
    os.makedirs(os.path.dirname(output_path) or POSTERS_DIR, exist_ok=True)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, facecolor=poster_bg)
    plt.close(fig)
    buf.seek(0)

    img = Image.open(buf)
    if img.mode == "RGBA":
        bg_img = Image.new("RGB", img.size, (255, 255, 255))
        bg_img.paste(img, mask=img.split()[3])
        img = bg_img
    elif img.mode != "RGB":
        img = img.convert("RGB")
    img.save(output_path, "PNG", dpi=(dpi, dpi))
    buf.close()

    # Clean up temp
    if os.path.exists(tmp_map):
        os.remove(tmp_map)
    gc.collect()

    elapsed = time.time() - t_start
    file_size_mb = os.path.getsize(output_path) / 1e6
    safe_print(f"\n[OK] Nordic poster done! ({elapsed:.1f}s, {file_size_mb:.1f} MB)")
    safe_print(f"     Output: {output_path}")
    return output_path
