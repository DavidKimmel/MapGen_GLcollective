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
        "#E8760A",  # burnt orange
        "#F5A623",  # amber/gold
        "#F5D89A",  # light yellow/cream (lightens the map)
        "#D4752A",  # copper/brown-orange
        "#C4943C",  # golden ochre
        "#F4A68C",  # salmon/peach
        "#E8C4A0",  # warm tan/sand
        "#B8956A",  # warm brown
        "#2C3E50",  # dark charcoal
        "#6B6B60",  # warm dark gray
        "#9A9A8A",  # warm medium gray
        "#BDC3C7",  # silver/light gray
        "#7A9E6B",  # olive green (muted)
        "#4A6A5A",  # dark sage
        "#4ECDC4",  # teal (rare accent)
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

# ─── LANDUSE TYPE → PALETTE INDEX (semantic coloring) ─────────────────────────
# Ensures different landuse types get different colors, reducing monotone blocks.

TYPE_SEED: dict[str, int] = {
    "farmland": 0, "farmyard": 0, "orchard": 0, "vineyard": 0,
    "forest": 6, "wood": 6,
    "scrub": 2, "heath": 2,
    "grassland": 1, "meadow": 3, "grass": 3,
    "park": 3, "garden": 3, "nature_reserve": 6,
    "residential": 0, "commercial": 4, "retail": 4,
    "industrial": 5, "construction": 5, "military": 6,
    "cemetery": 7, "allotments": 1,
    "beach": 7, "sand": 7, "bare_rock": 5,
    "aerodrome": 8, "quarry": 5,
    "recreation_ground": 3, "pitch": 3, "golf_course": 3,
    "university": 5, "hospital": 4, "school": 7,
}


def _get_type_color(
    val: str, palette: list[str], used_map: dict[str, str],
) -> str:
    """Return a consistent color for a landuse/natural type value."""
    val = str(val).lower().strip() if val else "unknown"
    if val not in used_map:
        idx = TYPE_SEED.get(val, hash(val) % len(palette))
        used_map[val] = palette[idx % len(palette)]
    return used_map[val]


def _assign_color(row, palette: list[str], used_map: dict[str, str]) -> str:
    """Assign color based on landuse > natural > leisure > amenity type."""
    for col in ["landuse", "natural", "leisure", "amenity"]:
        if col in row.index and row[col] not in [None, "nan", ""]:
            val = row[col]
            if val is not None and str(val) != "nan":
                return _get_type_color(str(val), palette, used_map)
    return random.choice(palette)


# ─── STREET WIDTHS ───────────────────────────────────────────────────────────

STREET_WEIGHTS: dict[str, float] = {
    "motorway": 3.0, "motorway_link": 2.0,
    "trunk": 2.5, "trunk_link": 1.8,
    "primary": 2.0, "primary_link": 1.5,
    "secondary": 1.5, "secondary_link": 1.2,
    "tertiary": 1.0, "tertiary_link": 0.8,
    "residential": 0.5, "unclassified": 0.5,
    "service": 0.3, "living_street": 0.4,
}

# Highway types to filter out — creates noise in parks/hills without adding structure
DROP_HIGHWAY: set[str] = {"footway", "path", "track", "cycleway", "steps", "pedestrian", "corridor"}


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
    bg_color: str = "#F0EBE1",
    water_color: str = "#F0EBE1",
    street_color: str = "#F0EBE1",
    dpi: int = 200,
    fig_width: float = 16,
    fig_height: float = 20,
    output_path: str = "",
    seed: int = 42,
) -> str:
    """Render a Florence-style city block mosaic map.

    Approach: streets + water only. Polygonize street network into blocks,
    color each block randomly. AOI base fill ensures zero gaps. Water on top.
    Streets as cream lines on top of everything.

    Returns path to saved PNG as str.
    """
    random.seed(seed)
    if palette is None:
        palette = PALETTES["florence"]

    # 1. Compute AOI — rectangular to match poster aspect ratio
    aspect = fig_height / fig_width  # e.g. 20/16 = 1.25, 36/24 = 1.5
    radius_x = radius
    radius_y = int(radius * aspect)
    safe_print(f"  Computing AOI for: ({lat:.4f}, {lon:.4f}) r={radius}m, aspect={aspect:.2f}...")
    center_pt = Point(lon, lat)
    center_gdf = gpd.GeoDataFrame(geometry=[center_pt], crs="EPSG:4326")
    utm_crs = center_gdf.estimate_utm_crs()
    center_proj = center_gdf.to_crs(utm_crs).geometry[0]
    aoi_box = box(
        center_proj.x - radius_x, center_proj.y - radius_y,
        center_proj.x + radius_x, center_proj.y + radius_y,
    )

    # 2. Fetch street network — overfetch 25% beyond AOI so edge blocks are complete
    fetch_radius = int(max(radius_x, radius_y) * 1.25)
    safe_print("  Fetching street network...")
    G = ox.graph_from_point((lat, lon), dist=fetch_radius, network_type="all")
    edges = ox.graph_to_gdfs(G, nodes=False).to_crs(utm_crs)
    edges = gpd.clip(edges, aoi_box)
    # Filter out footpaths/trails/cycleways — they fragment parks/hills into noise
    before = len(edges)
    if "highway" in edges.columns:
        edges = edges[~edges["highway"].apply(
            lambda h: str(h).lower() in DROP_HIGHWAY if h is not None else False
        )].copy()
    safe_print(f"  {before} edges → {len(edges)} after filtering paths")
    edges["lw"] = edges.apply(_road_weight, axis=1)

    # 3. Polygonize street network into city blocks
    # Add AOI boundary as lines — closes all open polygons at edges
    from shapely.geometry import LineString
    aoi_boundary = LineString(aoi_box.exterior.coords)
    safe_print("  Polygonizing street network into city blocks...")
    all_lines = unary_union(list(edges.geometry) + [aoi_boundary])
    block_polys = list(polygonize(all_lines))
    blocks = gpd.GeoDataFrame(geometry=block_polys, crs=utm_crs)
    blocks = gpd.clip(blocks, aoi_box)
    # Filter out tiny fragments — trail intersections create noise polygons
    # Threshold: ~500 sq meters (a small city lot). Tiny fragments merge into base fill.
    min_area = 500
    before = len(blocks)
    blocks = blocks[blocks.geometry.area >= min_area].copy()
    safe_print(f"  {before} raw blocks → {len(blocks)} after filtering (<{min_area}m² removed)")
    blocks["color"] = [random.choice(palette) for _ in range(len(blocks))]

    # 4. Fetch water separately
    safe_print("  Fetching water...")
    try:
        water = ox.features_from_point((lat, lon), WATER_TAGS, dist=int(max(radius_x, radius_y) * 1.25))
        water = water[water.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
        water = water.to_crs(utm_crs)
        water = gpd.clip(water, aoi_box)
        has_water = len(water) > 0
        safe_print(f"  {len(water)} water features")
    except Exception:
        has_water = False
        safe_print("  No water found")

    # 5. Build ocean polygons for coastal cities (land subtraction)
    crop_xlim = (center_proj.x - radius_x, center_proj.x + radius_x)
    crop_ylim = (center_proj.y - radius_y, center_proj.y + radius_y)
    try:
        from engine.ocean import build_ocean_polygons
        ocean_polys = build_ocean_polygons(
            (lat, lon), max(radius_x, radius_y), utm_crs, crop_xlim, crop_ylim
        )
    except Exception as e:
        safe_print(f"  Ocean build skipped: {e}")
        ocean_polys = []

    # 6. Render — layer order: base fill → ocean → blocks → water → streets
    safe_print("  Rendering Florence mosaic...")
    fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height))
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    ax.set_aspect("equal")
    ax.axis("off")

    # Layer 0: AOI base fill — solid palette color covers entire extent
    base_color = random.choice(palette)
    base_gdf = gpd.GeoDataFrame(geometry=[aoi_box], crs=utm_crs)
    base_gdf.plot(ax=ax, color=base_color, edgecolor="none", linewidth=0, zorder=0)

    # Layer 0.5: Ocean — water color underneath blocks (coastal cities)
    if ocean_polys:
        ocean_gdf = gpd.GeoDataFrame(geometry=ocean_polys, crs=utm_crs)
        ocean_gdf.plot(ax=ax, color=water_color, edgecolor="none", linewidth=0, zorder=0.5)

    # Layer 1: City block mosaic — every polygonized block gets a random color
    blocks.plot(ax=ax, color=blocks["color"], edgecolor="none", linewidth=0, zorder=1)

    # Layer 2: Water (rivers/lakes/bays) on top of blocks
    if has_water:
        water.plot(ax=ax, color=water_color, edgecolor="none", linewidth=0, zorder=3)

    # Layer 3: Streets as cream lines on top of everything
    for lw_val, group in edges.groupby("lw"):
        group.plot(ax=ax, color=street_color, linewidth=lw_val, alpha=1.0, zorder=4)

    bounds = [
        center_proj.x - radius_x, center_proj.y - radius_y,
        center_proj.x + radius_x, center_proj.y + radius_y,
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
    city_name: str | None = None,
    state_name: str | None = None,
) -> str:
    """Main entry point for Florence renderer — called by dispatcher.

    Handles geocoding, renders map, composes poster, returns str path.
    city_name/state_name overrides allow batch scripts to set display text.
    """
    t_start = time.time()

    safe_print(f"\n{'='*60}")
    safe_print("MapGen — Florence Renderer")
    safe_print(f"{'='*60}")

    # Parse location
    lat, lon, geocode_result = parse_location(location)
    if city_name is None:
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


def render_florence_all_sizes(
    location: str,
    theme_data: dict,
    sizes: list[str] | None = None,
    dpi: int = 300,
    output_dir: str = "",
    distance: int | None = None,
    city_name: str | None = None,
    state_name: str | None = None,
    city_slug: str | None = None,
    force: bool = False,
) -> list[str]:
    """Render all sizes from a single master map — consistent colors across sizes.

    Renders one master at 24x36 aspect (tallest), then crops to each size's
    aspect ratio via PIL. One render, 5 posters, identical coloring.

    Returns list of output paths.
    """
    from PIL import Image as PILImage
    from engine.florence_text_layout import compose_florence_poster as compose

    if sizes is None:
        sizes = ["8x10", "11x14", "16x20", "18x24", "24x36"]

    t_start = time.time()

    safe_print(f"\n{'='*60}")
    safe_print("MapGen — Florence Renderer (all sizes from master)")
    safe_print(f"{'='*60}")

    # Parse location
    lat, lon, geocode_result = parse_location(location)
    if city_name is None:
        city_name, state_name = extract_city_state(geocode_result)
        if city_name is None:
            city_name = location.split(",")[0].strip()

    if city_slug is None:
        city_slug = city_name.lower().replace(" ", "_") if city_name else "map"

    # Use 24x36 as the master — tallest aspect ratio (1.5)
    master_w, master_h = 24, 36
    if distance is None:
        distance = get_size_config("24x36")["distance_m"]

    safe_print(f"  Location: {city_name} ({lat:.4f}, {lon:.4f})")
    safe_print(f"  Master: {master_w}x{master_h} | Distance: {distance}m | DPI: {dpi}")
    safe_print(f"  Sizes: {', '.join(sizes)}")

    os.makedirs(output_dir or POSTERS_DIR, exist_ok=True)

    # Check if all sizes already exist
    if not force:
        all_exist = True
        for s in sizes:
            out = os.path.join(output_dir, f"{city_slug}_{s}.png")
            if not os.path.exists(out):
                all_exist = False
                break
        if all_exist:
            safe_print("  All sizes already exist — skipping")
            return [os.path.join(output_dir, f"{city_slug}_{s}.png") for s in sizes]

    # Render master map at 24x36 aspect
    palette = theme_data.get("palette", PALETTES["florence"])
    bg_color = theme_data.get("bg_color", "#F0EBE1")
    water_color = theme_data.get("water_color", "#F0EBE1")
    street_color = theme_data.get("street_color", "#F0EBE1")

    master_path = os.path.join(output_dir, f"_master_{city_slug}.png")
    render_florence_map(
        lat=lat, lon=lon, radius=distance,
        palette=palette, bg_color=bg_color,
        water_color=water_color, street_color=street_color,
        dpi=dpi, fig_width=master_w, fig_height=master_h,
        output_path=master_path,
    )

    # Load master image
    master_img = PILImage.open(master_path).convert("RGB")
    master_px_w, master_px_h = master_img.size
    safe_print(f"  Master image: {master_px_w}x{master_px_h} px")

    # For each size, crop the master to that aspect ratio (center crop)
    font_name = theme_data.get("font", "Switzer-Bold.ttf")
    font_path = os.path.join(FONTS_DIR, font_name)
    results = []

    for size_name in sizes:
        out_path = os.path.join(output_dir, f"{city_slug}_{size_name}.png")
        if os.path.exists(out_path) and not force:
            safe_print(f"  {size_name} — exists, skipping")
            results.append(out_path)
            continue

        sc = get_size_config(size_name)
        target_aspect = sc["height_in"] / sc["width_in"]
        master_aspect = master_h / master_w  # 1.5

        # Crop master to target aspect — always crop height (master is tallest)
        if target_aspect < master_aspect:
            # Target is squarer — crop top and bottom
            crop_h = int(master_px_w * target_aspect)
            y_offset = (master_px_h - crop_h) // 2
            cropped = master_img.crop((0, y_offset, master_px_w, y_offset + crop_h))
        else:
            # Target is same or taller — use full master
            cropped = master_img

        # Save cropped map to temp
        tmp_crop = os.path.join(output_dir, f"_crop_{city_slug}_{size_name}.png")
        cropped.save(tmp_crop)

        # Compose poster
        result = compose(
            map_image_path=tmp_crop,
            city_name=city_name or "city",
            state_or_region=state_name or "",
            lat=lat, lon=lon,
            palette=palette,
            size_name=size_name,
            dpi=dpi,
            bg_color=theme_data.get("poster_bg", "#F0EBE1"),
            text_color=theme_data.get("text_color", "#2C3E50"),
            font_path=font_path,
            output_path=out_path,
        )
        results.append(result)
        os.remove(tmp_crop)

        size_mb = os.path.getsize(result) / 1e6
        safe_print(f"  {size_name} — OK ({size_mb:.1f} MB)")

    # Clean up master
    if os.path.exists(master_path):
        os.remove(master_path)

    elapsed = time.time() - t_start
    safe_print(f"\n[OK] All {len(sizes)} sizes done! ({elapsed:.1f}s)")
    return results
