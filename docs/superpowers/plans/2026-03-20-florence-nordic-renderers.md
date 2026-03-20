# Florence + Nordic Renderer Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two new isolated map renderers (Florence mosaic + Nordic monochrome) to MapGen, dispatched via theme JSON, with zero changes to the existing rendering pipeline.

**Architecture:** Theme JSONs include a `"renderer"` key. A dispatch block at the top of `render_poster()` routes to dedicated renderer modules before any existing code runs. Each renderer handles its own OSM data fetching, matplotlib rendering, poster composition, and file saving.

**Tech Stack:** Python 3.13, osmnx, matplotlib, PIL/Pillow, geopandas, shapely

**Spec:** `docs/superpowers/specs/2026-03-20-florence-nordic-renderers-design.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `fonts/Switzer-Bold.ttf` | Create (copy) | Font for Florence poster typography |
| `themes/florence.json` | Create | Florence theme config with `"renderer": "florence"` |
| `themes/nordic.json` | Create | Nordic theme config with `"renderer": "nordic"` |
| `engine/florence_renderer.py` | Create | Polygonize map renderer — fetches OSM, renders mosaic, saves map |
| `engine/florence_text_layout.py` | Create | PIL poster composer — swatch bar, city name, state |
| `engine/nordic_renderer.py` | Create | Monochrome street renderer — fetches OSM, renders white-on-blue, composes poster |
| `engine/renderer.py` | Modify (lines 160-183) | Add dispatch block before geocoding |

---

### Task 1: Copy Switzer Bold font

**Files:**
- Create: `fonts/Switzer-Bold.ttf`

- [ ] **Step 1: Copy font file**

```bash
cp "C:/Users/kimme/Downloads/Switzer_Complete/Switzer_Complete/Fonts/WEB/fonts/Switzer-Bold.ttf" fonts/Switzer-Bold.ttf
```

- [ ] **Step 2: Verify font file exists and has reasonable size**

```bash
ls -la fonts/Switzer-Bold.ttf
```
Expected: File exists, ~50-200 KB

- [ ] **Step 3: Commit**

```bash
git add fonts/Switzer-Bold.ttf
git commit -m "chore: add Switzer Bold font for Florence renderer"
```

---

### Task 2: Create theme JSON files

**Files:**
- Create: `themes/florence.json`
- Create: `themes/nordic.json`

- [ ] **Step 1: Create `themes/florence.json`**

```json
{
    "name": "Florence",
    "renderer": "florence",
    "palette": [
        "#E8760A", "#F5A623", "#F4A68C", "#4ECDC4", "#2C3E50",
        "#BDC3C7", "#7A9E6B", "#C0392B", "#D4752A", "#4A6A5A"
    ],
    "bg_color": "#E8760A",
    "water_color": "#F0EBE1",
    "street_color": "#F0EBE1",
    "poster_bg": "#F0EBE1",
    "text_color": "#2C3E50",
    "font": "Switzer-Bold.ttf"
}
```

- [ ] **Step 2: Create `themes/nordic.json`**

```json
{
    "name": "Simple Nordic",
    "renderer": "nordic",
    "bg_color": "#3A5A78",
    "parks_color": "#4A7A6A",
    "street_color": "#FFFFFF",
    "water_color": "#FFFFFF",
    "text_color": "#1A1A1A",
    "poster_bg": "#FFFFFF",
    "street_widths": {
        "motorway": 3.0, "trunk": 3.0, "primary": 2.5, "primary_link": 2.5,
        "motorway_link": 2.0, "secondary": 2.0, "secondary_link": 2.0,
        "tertiary": 1.5, "tertiary_link": 1.0, "cycleway": 0,
        "residential": 0.5, "service": 0, "unclassified": 0,
        "pedestrian": 0, "footway": 0
    }
}
```

- [ ] **Step 3: Verify both themes load**

```bash
python -c "from engine.renderer import load_theme; t = load_theme('florence'); print(t['name'], t['renderer'])"
python -c "from engine.renderer import load_theme; t = load_theme('nordic'); print(t['name'], t['renderer'])"
```
Expected: `Florence florence` and `Simple Nordic nordic`

- [ ] **Step 4: Commit**

```bash
git add themes/florence.json themes/nordic.json
git commit -m "feat: add Florence and Nordic theme JSON files"
```

---

### Task 3: Create Florence map renderer

**Files:**
- Create: `engine/florence_renderer.py`

Port from `C:\prettymapp\glcollective\florence_style.py`. Key changes from source:
- Remove prettymapp imports (source has none — just osmnx/shapely/geopandas)
- Keep the core `render_florence_map()` function and all constants (PALETTES, FEATURE_TAGS, WATER_TAGS, STREET_WEIGHTS, TYPE_SEED)
- Change function name from `render_florence` to `render_florence_map` to distinguish from the poster entry point
- Add `render_florence_poster()` as the main entry point called by dispatcher — handles geocoding, size config, calls `render_florence_map()`, then calls `florence_text_layout.compose_florence_poster()`, returns `str`
- Use `utils/geocoding.py` for location parsing
- Use `export/output_sizes.py` for size dimensions
- Font path resolved via `FONTS_DIR`
- Return `str` (not `Path`)
- Support `map_only` parameter — skip poster composition

- [ ] **Step 1: Create `engine/florence_renderer.py`**

```python
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

    address = f"{lat}, {lon}"

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
```

- [ ] **Step 2: Verify module imports without errors**

```bash
python -c "from engine.florence_renderer import PALETTES, STREET_WEIGHTS; print('OK', len(PALETTES['florence']), 'colors')"
```
Expected: `OK 10 colors`

- [ ] **Step 3: Commit**

```bash
git add engine/florence_renderer.py
git commit -m "feat: add Florence mosaic map renderer"
```

---

### Task 4: Create Florence poster composer

**Files:**
- Create: `engine/florence_text_layout.py`

Port from `C:\prettymapp\glcollective\compose_florence.py`. Key changes:
- Remove `from glcollective.print_sizes import PRINT_SIZES` — use `export.output_sizes.get_size_config`
- Remove `from glcollective.florence_style import PALETTES` — accept palette as parameter
- Accept `palette` list directly instead of `palette_name`
- Return `str` (not `Path`)

- [ ] **Step 1: Create `engine/florence_text_layout.py`**

```python
"""Florence-style poster composer — swatch bar + typography.

Layout (top to bottom):
- Top margin (5% of width, matches sides)
- Map image (fills top ~83%)
- Color swatch bar (horizontal strip showing palette)
- City name (large lowercase, right-aligned)
- State/country (smaller, right-aligned)
- Bottom margin
"""

import os
import random
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from export.output_sizes import get_size_config

_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_ENGINE_DIR)
FONTS_DIR = os.path.join(_PROJECT_DIR, "fonts")


def compose_florence_poster(
    map_image_path: str,
    city_name: str,
    state_or_region: str,
    lat: float,
    lon: float,
    palette: list[str],
    size_name: str = "16x20",
    dpi: int = 200,
    bg_color: str = "#F0EBE1",
    text_color: str = "#2C3E50",
    font_path: Optional[str] = None,
    output_path: Optional[str] = None,
) -> str:
    """Compose a Florence-style poster. Returns output path as str."""
    ps = get_size_config(size_name)
    total_w = int(ps["width_in"] * dpi)
    total_h = int(ps["height_in"] * dpi)

    # ─── Layout proportions ──────────────────────────────────────────────
    margin_x = int(total_w * 0.05)
    top_margin = margin_x
    bottom_block_height = int(total_h * 0.17)

    # Text sizing
    city_font_size = int(total_h * 0.075)
    region_font_size = int(total_h * 0.018)

    # Swatch bar
    swatch_height = int(total_h * 0.012)

    # Map fills top area
    map_x = margin_x
    map_y = top_margin
    map_w = total_w - (2 * margin_x)
    map_h = total_h - top_margin - bottom_block_height

    # ─── Load fonts ──────────────────────────────────────────────────────
    city_font = _load_font(font_path, city_font_size, prefer_serif=True)
    region_font = _load_font(font_path, region_font_size, prefer_serif=False)

    # ─── Create canvas ───────────────────────────────────────────────────
    canvas = Image.new("RGB", (total_w, total_h), bg_color)
    draw = ImageDraw.Draw(canvas)

    # ─── Bottom text block ──────────────────────────────────────────────
    right_edge = total_w - margin_x
    text_block_top = map_y + map_h + int(total_h * 0.015)

    # Color swatch bar (full width, above title)
    swatch_y = text_block_top
    swatch_total_w = total_w - (2 * margin_x)
    swatch_gap = int(total_w * 0.003)

    # Vary widths — some blocks wider than others for organic feel
    random.seed(len(city_name))  # deterministic per city
    raw_widths = [random.uniform(0.6, 1.8) for _ in palette]
    total_raw = sum(raw_widths)
    usable_w = swatch_total_w - (swatch_gap * (len(palette) - 1))
    widths = [int((w / total_raw) * usable_w) for w in raw_widths]

    x_cursor = margin_x
    for i, color in enumerate(palette):
        x0 = x_cursor
        x1 = x_cursor + widths[i]
        draw.rectangle([x0, swatch_y, x1, swatch_y + swatch_height], fill=color)
        x_cursor = x1 + swatch_gap

    # City name (large lowercase, right-aligned, below swatch)
    city_text = city_name.lower()
    city_y = swatch_y + swatch_height + int(total_h * 0.012)
    bbox = draw.textbbox((0, 0), city_text, font=city_font)
    city_text_w = bbox[2] - bbox[0]
    draw.text((right_edge - city_text_w, city_y), city_text, fill=text_color, font=city_font)

    # State/country (smaller, right-aligned, below city name)
    if state_or_region:
        state_text = state_or_region.lower()
        state_y = city_y + city_font_size + int(total_h * 0.012)
        bbox = draw.textbbox((0, 0), state_text, font=region_font)
        state_text_w = bbox[2] - bbox[0]
        draw.text((right_edge - state_text_w, state_y), state_text, fill=text_color, font=region_font)

    # ─── Map image ───────────────────────────────────────────────────────
    map_img = Image.open(map_image_path).convert("RGB")
    map_img = map_img.resize((map_w, map_h), Image.LANCZOS)
    canvas.paste(map_img, (map_x, map_y))

    # ─── Save ────────────────────────────────────────────────────────────
    if output_path is None:
        slug = city_name.lower().replace(" ", "_")
        output_path = f"posters/{slug}_florence_poster.png"

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    canvas.save(output_path, dpi=(dpi, dpi))
    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"  Poster saved: {output_path} ({size_mb:.1f} MB)")
    return output_path


def _load_font(
    font_path: Optional[str], size: int, prefer_serif: bool = True,
) -> ImageFont.FreeTypeFont:
    """Try to load a font, falling back through options."""
    if font_path:
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            pass

    if prefer_serif:
        candidates = [
            "georgia.ttf", "georgiab.ttf", "CENTURY.TTF",
            "times.ttf", "timesbd.ttf", "cambriab.ttf",
        ]
    else:
        candidates = [
            "calibri.ttf", "arial.ttf", "CenturyGothic.ttf",
            "segoeui.ttf", "verdana.ttf",
        ]

    for fname in candidates:
        try:
            return ImageFont.truetype(fname, size)
        except OSError:
            continue

    return ImageFont.load_default()
```

- [ ] **Step 2: Verify module imports**

```bash
python -c "from engine.florence_text_layout import compose_florence_poster; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add engine/florence_text_layout.py
git commit -m "feat: add Florence poster composer (swatch bar + typography)"
```

---

### Task 5: Create Nordic renderer

**Files:**
- Create: `engine/nordic_renderer.py`

New file — renders monochrome street network art. Uses osmnx for data, matplotlib for rendering, and MapGen's existing `text_layout.py` for poster text.

- [ ] **Step 1: Create `engine/nordic_renderer.py`**

```python
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
```

- [ ] **Step 2: Verify module imports**

```bash
python -c "from engine.nordic_renderer import render_nordic_poster; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add engine/nordic_renderer.py
git commit -m "feat: add Nordic monochrome street map renderer"
```

---

### Task 6: Add dispatch to `renderer.py`

**Files:**
- Modify: `engine/renderer.py:160-183`

Move `load_theme()` above geocoding and add dispatch block. No other changes to existing code.

- [ ] **Step 1: Modify `engine/renderer.py` — two edits**

**Edit A:** Insert dispatch block after the banner (after line 165, before line 167). This adds `load_theme()` + dispatch logic.

Replace lines 166-167 (the blank line + `lat, lon` geocode line):

```
    # renderer dispatch — route to dedicated renderers before existing pipeline
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
```

**Edit B:** Remove the duplicate `load_theme()` on line 183.

Replace this exact line:
```
    theme_data = load_theme(theme)
```
with nothing (delete it). The variable is already set by the dispatch block above.

**Net result:** `load_theme()` runs once at line ~167. Existing themes (no `"renderer"` key) fall through to the existing pipeline unchanged. New themes dispatch to their dedicated renderer and return early. Unknown renderer values raise a clear error.

- [ ] **Step 2: Verify existing theme still works (no regression)**

```bash
python -c "from engine.renderer import load_theme; t = load_theme('37th_parallel'); assert 'renderer' not in t; print('OK — existing theme has no renderer key')"
```
Expected: `OK — existing theme has no renderer key`

- [ ] **Step 3: Verify dispatch routes correctly**

```bash
python -c "from engine.renderer import load_theme; t = load_theme('florence'); assert t.get('renderer') == 'florence'; print('OK — florence routes to florence renderer')"
python -c "from engine.renderer import load_theme; t = load_theme('nordic'); assert t.get('renderer') == 'nordic'; print('OK — nordic routes to nordic renderer')"
```
Expected: Both print OK

- [ ] **Step 4: Commit**

```bash
git add engine/renderer.py
git commit -m "feat: add renderer dispatch for florence and nordic themes"
```

---

### Task 7: Test Florence end-to-end

**Files:** None (testing only)

- [ ] **Step 1: Render Florence poster at 72 DPI (fast test)**

```bash
python cli.py --location "Pittsburgh" --theme florence --size 16x20 --dpi 72 --output posters/test_florence_pgh.png
```
Expected: Poster saved to `posters/test_florence_pgh.png`. Visually verify: cream background, colorful mosaic map, swatch bar at bottom, "pittsburgh" text right-aligned.

- [ ] **Step 2: Render Florence map-only at 72 DPI**

```bash
python cli.py --location "Pittsburgh" --theme florence --size 16x20 --dpi 72 --map-only --output posters/test_florence_pgh_maponly.png
```
Expected: Raw mosaic map, no swatch bar, no text.

- [ ] **Step 3: Verify return type is str**

```bash
python -c "
from engine.renderer import render_poster
result = render_poster(location='Pittsburgh', theme='florence', size='16x20', dpi=72, output_path='posters/test_florence_type.png')
print(type(result).__name__, ':', result)
assert isinstance(result, str)
print('OK — returns str')
"
```
Expected: `str : posters/test_florence_type.png` then `OK — returns str`

---

### Task 8: Test Nordic end-to-end

**Files:** None (testing only)

- [ ] **Step 1: Render Nordic poster at 72 DPI (fast test)**

```bash
python cli.py --location "Pittsburgh" --theme nordic --size 16x20 --dpi 72 --output posters/test_nordic_pgh.png
```
Expected: Poster saved. Visually verify: white background, steel blue map with white streets and water, city name text at bottom.

- [ ] **Step 2: Render Nordic map-only at 72 DPI**

```bash
python cli.py --location "Pittsburgh" --theme nordic --size 16x20 --dpi 72 --map-only --output posters/test_nordic_pgh_maponly.png
```
Expected: Raw blue map, no text, no white margins.

---

### Task 9: Regression test existing pipeline

**Files:** None (testing only)

- [ ] **Step 1: Render with default theme**

```bash
python cli.py --location "Pittsburgh" --theme 37th_parallel --size 16x20 --dpi 72 --output posters/test_regression_pgh.png
```
Expected: Identical behavior to before — standard black roads on white with blue water, green parks, text at bottom.

- [ ] **Step 2: Clean up test files**

```bash
rm -f posters/test_florence_*.png posters/test_nordic_*.png posters/test_regression_*.png
```

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: Florence + Nordic renderer integration complete"
```
