"""Florence-style city block mosaic map renderer.

Uses polygonize() on the street network to create individual city block polygons,
then colors each block randomly from a palette. Landuse/park/forest polygons
rendered on top. Water as neutral. Streets as thin cream lines on top.
"""

import gc
import os
import random
import time

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import osmnx as ox
from shapely.geometry import Point, box
from shapely.ops import polygonize, unary_union

from export.output_sizes import get_size_config
from utils.geocoding import extract_city_state, parse_location
from utils.logging import safe_print

_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_ENGINE_DIR)
FONTS_DIR = os.path.join(_PROJECT_DIR, "fonts")
POSTERS_DIR = os.path.join(_PROJECT_DIR, "posters")

# ─── PALETTES ────────────────────────────────────────────────────────────────

PALETTES: dict[str, list[str]] = {
    "florence": [
        "#E8760A", "#F5A623", "#F4A68C", "#4ECDC4", "#2C3E50",
        "#BDC3C7", "#7A9E6B", "#C0392B", "#D4752A", "#4A6A5A",
    ],
}

# ─── FEATURE TAGS — landuse + natural + leisure (NO water) ────────────────────

FEATURE_TAGS: dict = {
    "landuse": True,
    "natural": ["wood", "scrub", "heath", "grassland", "beach", "sand", "bare_rock"],
    "leisure": ["park", "garden", "golf_course", "nature_reserve",
                "recreation_ground", "pitch"],
    "amenity": ["university", "hospital", "school"],
    "aeroway": ["aerodrome"],
}

WATER_TAGS: dict = {
    "natural": ["water", "bay"],
    "waterway": ["riverbank"],
    "water": True,
}

# ─── STREET WIDTHS ───────────────────────────────────────────────────────────

STREET_WEIGHTS: dict[str, float] = {
    "motorway": 1.2, "motorway_link": 0.8,
    "trunk": 1.0, "trunk_link": 0.7,
    "primary": 0.8, "primary_link": 0.6,
    "secondary": 0.6, "secondary_link": 0.5,
    "tertiary": 0.4, "tertiary_link": 0.3,
    "residential": 0.25, "unclassified": 0.25,
    "service": 0.15, "living_street": 0.2,
}


def _road_weight(row) -> float:
    """Get line width for a road based on highway type."""
    hw = str(row.get("highway", "")).lower() if "highway" in row.index else ""
    for key, weight in STREET_WEIGHTS.items():
        if key in hw:
            return weight
    return 0.15


def render_florence_map(
    lat: float,
    lon: float,
    radius: int = 5000,
    palette: list[str] | None = None,
    bg_color: str = "#E8760A",
    water_color: str = "#F0EBE1",
    street_color: str = "#F0EBE1",
    dpi: int = 200,
    fig_width: float = 16,
    fig_height: float = 20,
    output_path: str = "",
    seed: int = 42,
) -> str:
    """Render a Florence-style city block mosaic map.

    Returns path to saved PNG as str.
    """
    random.seed(seed)
    if palette is None:
        palette = PALETTES["florence"]

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

    # 2. Fetch street network and polygonize into city blocks
    safe_print("  Fetching street network...")
    G = ox.graph_from_point((lat, lon), dist=radius, network_type="all")
    edges = ox.graph_to_gdfs(G, nodes=False).to_crs(utm_crs)
    edges = gpd.clip(edges, aoi_box)
    edges["lw"] = edges.apply(_road_weight, axis=1)

    safe_print("  Polygonizing street network into city blocks...")
    all_lines = unary_union(edges.geometry)
    block_polys = list(polygonize(all_lines))
    blocks = gpd.GeoDataFrame(geometry=block_polys, crs=utm_crs)
    blocks = gpd.clip(blocks, aoi_box)
    blocks["color"] = [random.choice(palette) for _ in range(len(blocks))]
    safe_print(f"  {len(blocks)} city blocks generated")

    # 3. Fetch landuse/natural/leisure features (NO water)
    safe_print("  Fetching landuse features...")
    try:
        features = ox.features_from_point((lat, lon), FEATURE_TAGS, dist=radius)
        features = features[
            features.geometry.type.isin(["Polygon", "MultiPolygon"])
        ].copy()
        features = features.to_crs(utm_crs)
        features = gpd.clip(features, aoi_box)
        features["color"] = [random.choice(palette) for _ in range(len(features))]
        safe_print(f"  {len(features)} landuse features")
    except Exception as e:
        safe_print(f"  Warning: could not fetch landuse: {e}")
        features = gpd.GeoDataFrame(columns=["geometry", "color"], crs=utm_crs)

    # 4. Fetch water separately
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

    # 5. Render — layer order is critical
    safe_print("  Rendering Florence mosaic...")
    fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height))
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    ax.set_aspect("equal")
    ax.axis("off")

    # Layer 1 (bottom): City block mosaic
    blocks.plot(ax=ax, color=blocks["color"], edgecolor="none", linewidth=0, zorder=1)

    # Layer 2 (middle): Landuse/parks/forests override blocks
    if not features.empty:
        features.plot(ax=ax, color=features["color"], edgecolor="none", linewidth=0, zorder=2)

    # Layer 3: Water — neutral/cream
    if has_water:
        water.plot(ax=ax, color=water_color, edgecolor="none", linewidth=0, zorder=3)

    # Layer 4 (top): Streets as thin cream lines
    for lw_val, group in edges.groupby("lw"):
        group.plot(ax=ax, color=street_color, linewidth=lw_val, alpha=0.9, zorder=4)

    bounds = [
        center_proj.x - radius, center_proj.y - radius,
        center_proj.x + radius, center_proj.y + radius,
    ]
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])

    # 6. Save
    out_path = output_path
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", pad_inches=0, facecolor=bg_color)
    plt.close(fig)
    gc.collect()

    size_mb = os.path.getsize(out_path) / 1024 / 1024
    safe_print(f"  Map saved: {out_path} ({size_mb:.1f} MB)")
    return out_path


def render_florence_poster(
    location: str,
    theme_data: dict,
    size: str = "16x20",
    dpi: int = 300,
    output_path: str | None = None,
    distance: int | None = None,
    map_only: bool = False,
) -> str:
    """Main entry point for Florence renderer — called by dispatcher.

    Handles geocoding, renders map, composes poster, returns str path.
    """
    t_start = time.time()

    safe_print(f"\n{'='*60}")
    safe_print("MapGen — Florence Renderer")
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
        output_path = os.path.join(POSTERS_DIR, f"{city_slug}_florence_{size}_{timestamp}.png")

    # Render raw map
    palette = theme_data.get("palette", PALETTES["florence"])
    bg_color = theme_data.get("bg_color", "#E8760A")
    water_color = theme_data.get("water_color", "#F0EBE1")
    street_color = theme_data.get("street_color", "#F0EBE1")

    if map_only:
        # Return raw map directly
        map_path = render_florence_map(
            lat=lat, lon=lon, radius=distance,
            palette=palette, bg_color=bg_color,
            water_color=water_color, street_color=street_color,
            dpi=dpi, fig_width=width_in, fig_height=height_in,
            output_path=output_path,
        )
        elapsed = time.time() - t_start
        safe_print(f"\n[OK] Florence map-only done! ({elapsed:.1f}s)")
        return map_path

    # Render map to temp, then compose poster
    tmp_map = output_path + ".tmp_map.png"
    render_florence_map(
        lat=lat, lon=lon, radius=distance,
        palette=palette, bg_color=bg_color,
        water_color=water_color, street_color=street_color,
        dpi=dpi, fig_width=width_in, fig_height=height_in,
        output_path=tmp_map,
    )

    # Compose poster
    from engine.florence_text_layout import compose_florence_poster as compose

    font_name = theme_data.get("font", "Switzer-Bold.ttf")
    font_path = os.path.join(FONTS_DIR, font_name)

    result = compose(
        map_image_path=tmp_map,
        city_name=city_name or "city",
        state_or_region=state_name or "",
        lat=lat, lon=lon,
        palette=palette,
        size_name=size,
        dpi=dpi,
        bg_color=theme_data.get("poster_bg", "#F0EBE1"),
        text_color=theme_data.get("text_color", "#2C3E50"),
        font_path=font_path,
        output_path=output_path,
    )

    # Clean up temp
    if os.path.exists(tmp_map):
        os.remove(tmp_map)

    elapsed = time.time() - t_start
    file_size_mb = os.path.getsize(result) / 1e6
    safe_print(f"\n[OK] Florence poster done! ({elapsed:.1f}s, {file_size_mb:.1f} MB)")
    safe_print(f"     Output: {result}")
    return result
