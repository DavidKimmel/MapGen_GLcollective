# Design: Florence + Nordic Renderer Integration

## Summary

Add two new map rendering styles (Florence and Nordic) to MapGen as isolated renderers that share the CLI entry point and city list but do not modify the existing rendering pipeline.

## Context

Two styles were prototyped in `C:\prettymapp\glcollective\` and are approved for production:

- **Florence** — city block mosaic via `polygonize()` on street network. Random palette colors per block, landuse overlay, cream water/streets. PIL-based poster composer with swatch bar and right-aligned typography.
- **Nordic** — monochromatic street network art. Steel blue background, white streets and water, blue-green parks. Simple and clean.

Both need to be integrated into MapGen to leverage the existing city list, batch rendering, Etsy/Gelato fulfillment, and mockup pipeline.

## Design Decision: Separate Renderers

Each style gets its own renderer module. The existing `render_poster()` pipeline is untouched — a dispatch check at the top routes to the new renderers based on a `"renderer"` key in the theme JSON.

**Rationale:** Zero risk to the existing 57 live Etsy listings. Florence uses fundamentally different rendering (polygonize + PIL composition). Nordic uses different data fetching and layer logic. Coupling either to the existing pipeline would create fragile dependencies.

## Architecture

### New Files

| File | Purpose |
|---|---|
| `engine/florence_renderer.py` | Polygonize renderer — fetches street network via osmnx, creates city block polygons, random palette colors, landuse overlay, water + streets on top |
| `engine/nordic_renderer.py` | Monochrome renderer — fetches street network + water + parks via osmnx, renders white-on-blue |
| `engine/florence_text_layout.py` | PIL-based poster composer — cream background, color swatch bar, right-aligned city name in Switzer Bold |
| `themes/florence.json` | Palette colors, water/street/bg colors, `"renderer": "florence"` |
| `themes/nordic.json` | Background/street/park colors, street widths, `"renderer": "nordic"` |
| `fonts/Switzer-Bold.ttf` | Font for Florence poster typography |

### Modified Files

| File | Change |
|---|---|
| `engine/renderer.py` | Move `load_theme()` call above geocoding. Add dispatch: if `theme.renderer` is `"florence"` or `"nordic"`, call dedicated renderer and return early. All existing code below dispatch is unchanged. |

### Dispatch Logic

The `load_theme()` call must be moved above the geocoding block (currently line 183, needs to move before line 167). This is safe — `load_theme()` has no dependencies on parsed location. The dispatch intercepts before any existing pipeline code runs.

```python
# Move load_theme() to top of render_poster(), before geocoding:
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
# ... existing pipeline continues unchanged (geocoding, OSM fetch, etc.)
```

### Return Type Contract

Both new renderer functions must return `str` (file path), matching `render_poster()`'s contract. The source prototypes return `Path` — these must be converted via `str()` before returning.

### Parameter Handling

The new renderers accept a subset of `render_poster()`'s 18 parameters. Parameters not supported by these renderers:

| Parameter | Florence | Nordic | Behavior |
|---|---|---|---|
| `crop` | Not supported | Not supported (v1) | Ignored — these styles are full-bleed only for initial release |
| `pin_*` | Not supported | Not supported (v1) | Ignored — no pin rendering |
| `font_preset` | N/A (uses Switzer Bold) | N/A (uses preset 1 style) | Ignored |
| `text_line_*` | N/A (uses city/state from geocoding) | N/A (uses city/state from geocoding) | Ignored |
| `layout` | N/A (own PIL layout) | N/A (default only) | Ignored |
| `border` | Not supported | Not supported | Ignored |
| `detail_layers` | N/A (own layer logic) | N/A (own layer logic) | Ignored |
| `map_only` | Supported — skip poster composition, return raw map | Supported — skip text, return raw map | Used by mockup pipeline |

Unsupported parameters are silently ignored (not errors). These are new art styles with their own aesthetic — pins and crop masks don't apply to the Florence mosaic look or the Nordic monochrome look.

### Shared Modules (Read-Only)

- `utils/geocoding.py` — `parse_location()`, `extract_city_state()`
- `export/output_sizes.py` — `get_size_config()` for print dimensions
- `etsy/city_list.py` — city data for batch rendering
- `fonts/` directory — font files

### Import Remapping from Source

| Source import | MapGen import |
|---|---|
| `from glcollective.print_sizes import PRINT_SIZES` | `from export.output_sizes import get_size_config` |
| `from glcollective.florence_style import PALETTES` | `from engine.florence_renderer import PALETTES` |
| `from glcollective.florence_style import render_florence` | `from engine.florence_renderer import render_florence_map` |

### Font Path Resolution

The theme JSON `font` field stores a filename only (e.g., `"Switzer-Bold.ttf"`), not an absolute path. Renderers resolve fonts via `os.path.join(FONTS_DIR, theme_data["font"])`. The hardcoded path in the prettymapp prototype is not carried over.

### Theme JSON Structure

**`themes/florence.json`:**
```json
{
    "name": "Florence",
    "renderer": "florence",
    "palette": ["#E8760A", "#F5A623", "#F4A68C", "#4ECDC4", "#2C3E50", "#BDC3C7", "#7A9E6B", "#C0392B", "#D4752A", "#4A6A5A"],
    "bg_color": "#E8760A",
    "water_color": "#F0EBE1",
    "street_color": "#F0EBE1",
    "poster_bg": "#F0EBE1",
    "text_color": "#2C3E50",
    "font": "Switzer-Bold.ttf"
}
```

**`themes/nordic.json`:**
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
        "motorway": 3, "trunk": 3, "primary": 2.5, "primary_link": 2.5,
        "motorway_link": 2, "secondary": 2, "secondary_link": 2,
        "tertiary": 1.5, "tertiary_link": 1.0, "cycleway": 0,
        "residential": 0.5, "service": 0, "unclassified": 0,
        "pedestrian": 0, "footway": 0
    }
}
```

### Web Frontend Consideration

The new themes will appear in `get_available_themes()` and the frontend theme picker. Since these renderers produce fundamentally different output (no pin support, different text layout), this is a known limitation for v1. The web app is not the primary sales channel — CLI and batch scripts are. Future work could filter themes by renderer type in the API response.

## Florence Renderer Details

### Rendering Pipeline (`florence_renderer.py`)

1. Parse location via `utils/geocoding.py` — returns `lat, lon, city_name, state_name`
2. Get size config via `export/output_sizes.py`
3. Compute AOI bounding box in UTM projection
4. Fetch street network via `ox.graph_from_address()` — uses osmnx's own cache (separate from MapGen's `utils/cache.py`)
5. `polygonize()` street geometries into city block polygons
6. Assign random palette color per block (seeded for reproducibility)
7. Fetch landuse/natural/leisure features — random palette colors, rendered on top of blocks
8. Fetch water — rendered as cream (`#F0EBE1`)
9. Render streets as thin cream lines on top
10. If `map_only`: save and return raw map path as `str`
11. Otherwise: save raw map to temp file, pass to `florence_text_layout.py` for poster composition
12. Delete temp file, `gc.collect()`, return final poster path as `str`

### Poster Composition (`florence_text_layout.py`)

- PIL-based (not matplotlib)
- Cream background (`#F0EBE1`), 5% margins
- Map fills top ~83%
- Bottom block: color swatch bar (varied widths), city name large lowercase right-aligned, state/country smaller underneath
- Font: Switzer Bold resolved from `fonts/Switzer-Bold.ttf`
- Text color: `#2C3E50`

### Known Constraints

- Dense European cities (Paris) can look monotone due to large landuse polygons dominating
- `polygonize()` can be slow at large extents (DC at 8000m = 86k blocks)
- Memory management: explicit `gc.collect()` after each render

## Nordic Renderer Details

### Rendering Pipeline (`nordic_renderer.py`)

1. Parse location via `utils/geocoding.py` — returns `lat, lon, city_name, state_name`
2. Get size config via `export/output_sizes.py`
3. Fetch street network via `ox.graph_from_address()`
4. Fetch water features via `ox.features_from_address()`
5. Fetch parks/woodland via `ox.features_from_address()`
6. Render on steel blue background (`#3A5A78`):
   - Parks/woodland as `#4A7A6A` (zorder 2)
   - Water as white (zorder 2)
   - Streets as white lines with reduced widths (zorder 5)
   - No buildings, no railways, no other layers
7. If `map_only`: save and return raw map path as `str`
8. Otherwise: save raw map to temp file, compose poster with white background + city/state text using MapGen's existing `text_layout.py` (font preset 1, right-aligned), `gc.collect()`, return final poster path as `str`

### Nordic Text Layout

Nordic uses MapGen's existing `text_layout.py` module with `render_bottom_text()` for the poster composition. This keeps the text style consistent with the existing product line while the map itself is rendered differently. The poster background is white (`#FFFFFF`), text color is dark (`#1A1A1A`).

## CLI Usage

No CLI changes needed — existing `--theme` flag works:

```bash
python cli.py --location "New York" --theme florence --size 16x20
python cli.py --location "New York" --theme nordic --size 16x20

# map_only mode for mockup templates
python cli.py --location "New York" --theme florence --size 16x20 --map-only
```

## Testing

1. Render Florence for Pittsburgh at 72 DPI — verify mosaic + poster layout
2. Render Nordic for Pittsburgh at 72 DPI — verify monochrome + poster layout
3. Render existing theme (37th_parallel) for Pittsburgh — verify no regression (dispatch skips new code)
4. Test `--map-only` flag with both new themes — verify raw map output without text
5. Test at 300 DPI / 16x20 for production quality
6. Verify return type is `str` (not `Path`)
7. Test font loading fallback (missing Switzer-Bold.ttf should fall back to system serif)
8. Verify output file naming matches existing pattern (`{city}_{theme}_{size}_{timestamp}.png`)
