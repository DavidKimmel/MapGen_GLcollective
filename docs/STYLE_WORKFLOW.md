# GeoLine Collective — Style Workflow Guide

Complete reference for producing a batch of city map listings in any style. Follow this guide step-by-step when creating a new batch or adding a new style.

---

## Table of Contents

1. [Overview — The Pipeline](#overview)
2. [Style Definitions](#style-definitions)
3. [City Extents](#city-extents)
4. [Rendering Rules](#rendering-rules)
5. [Mockup Rules](#mockup-rules)
6. [Detail Crop Rules](#detail-crop-rules)
7. [Listing Text Rules](#listing-text-rules)
8. [Image Upload Order](#image-upload-order)
9. [Color Variant Styles](#color-variant-styles)
10. [Etsy API Push](#etsy-api-push)
11. [Gelato Connection](#gelato-connection)
12. [Custom Map vs Pre-Made](#custom-map-vs-pre-made)
13. [Known Issues](#known-issues)
14. [Commands Quick Reference](#commands-quick-reference)

---

## 1. Overview — The Pipeline <a name="overview"></a>

Every listing follows this pipeline:

```
1. RENDER      → 5 sizes per city (8x10, 11x14, 16x20, 18x24, 24x36)
2. MOCKUPS     → 7-10 images per city (flat + lifestyle + PSD4 labeled if color style)
3. DETAIL CROP → 1 close-up with "EVERY STREET. EVERY DETAIL." badge
4. LISTING TXT → Style-specific title, tags, description, SKUs, pricing
5. GELATO CSV  → 15 physical variants (5 unframed + 5 framed black + 5 framed white)
6. ETSY PUSH   → Create draft via API, upload images, set variants, enable personalization
7. GELATO SYNC → Sync in Gelato dashboard, then connect variants via API
```

**Main script:** `python scripts/batch_universal.py --style <name> --skip-etsy`

---

## 2. Style Definitions <a name="style-definitions"></a>

| Style | Renderer | Default Extent | DPI | Default Color | Filler Source |
|-------|----------|---------------|-----|---------------|---------------|
| **Classic** (37th_parallel) | `engine/renderer.py` | city_list distance | 300 | N/A (single look) | `DefaultMap_Posted/` |
| **Florence** | `engine/florence_renderer.py` | city_list × 0.65 | 300 | N/A (single palette) | `FlorenceMap_Posted/` |
| **Blueprint** | `engine/blueprint_renderer.py` | 5000m (fixed) | 200 | terracotta | `BlueprintV3/` |
| **MonoMap** | Florence renderer + single-color palette | 5000m (fixed) | 300 | navy | `MonoMap/{color}/` |

### Style configs: `etsy/style_config.py`
- `StyleConfig` dataclass with pricing, SKU prefix, tags, render params
- `CITY_EXTENT_OVERRIDES` — per-city radius overrides (mega cities get 6000-8000m)
- `get_city_extent(slug, style)` — returns the correct radius for any city

### Style-specific listing text:
- Classic/Florence: `etsy/listing_generator.py` (pass `style=` parameter)
- Blueprint: `etsy/blueprint_listing.py`
- MonoMap: TODO — needs its own listing module (currently uses listing_generator)

---

## 3. City Extents <a name="city-extents"></a>

**Default:** 5000m for Blueprint/MonoMap, city_list distance for Classic/Florence

**Overrides in `etsy/style_config.py` → `CITY_EXTENT_OVERRIDES`:**

| Extent | Cities |
|--------|--------|
| 8000m | London, Tokyo, Los Angeles, Istanbul |
| 7000m | Mexico City |
| 6000m | Chicago, NYC, Houston, Dallas, Phoenix, Miami, Atlanta, Philadelphia, + more |
| 5000m | Default (31 mid-size cities) |
| 4000m | Florence, Savannah, Charleston, Asheville |

**Rule:** Always render ONE test city and review before running a full batch.

---

## 4. Rendering Rules <a name="rendering-rules"></a>

### Master Crop Approach (Blueprint, Florence, MonoMap)
1. Render ONE master at 24x36 aspect ratio (tallest)
2. Crop to each size's aspect ratio from center
3. Compose poster layout per size

This ensures consistent colors across all sizes (one render pass).

### Per-Size Rendering (Classic)
Each size rendered independently via `render_poster()`.

### Key Rules:
- **Subprocess isolation** — each city runs in its own Python subprocess to prevent memory leaks
- **`bbox_inches="tight"`** in matplotlib — strips padding
- **No content-bounds detection** in Blueprint compositor — just resize to fill (removed after it caused squishing/zooming issues)
- **Blueprint:** `render_shaded_map()` → crop → `compose_blueprint_poster()`
- **Florence:** `render_florence_all_sizes()` handles master crop internally

### Output Location:
```
etsy/renders/{slug}_{style}/         # e.g., chicago_blueprint/
etsy/renders/{slug}_{style}/{slug}_{size}.png  # e.g., chicago_16x20.png
```

Classic uses `{slug}/` (no style suffix) for backward compatibility.

---

## 5. Mockup Rules <a name="mockup-rules"></a>

### Template Sources:
| Template | File | Slots | Render Size | Notes |
|----------|------|-------|-------------|-------|
| Main | `TUR2/Best/Flat/Main.psd` | 1 | 24x36 | Primary thumbnail for non-color styles |
| Mockup4 | `TUR2/Best/Flat/Mockup4.psd` | 1 | 24x36 | |
| ONCE | `TUR2/Best/Flat/ONCE 1_PSD_Post.psd` | 1 | 18x24 | |
| VV1 | `TUR2/Best/Flat/VV1_PSD_Post.psd` | 1 | 18x24 | |
| 2Frames | `TUR2/Best/Flat/2 Frames - StudioBlank.psd` | 2 | 24x36 | Featured = slot 1 (right) |
| CLS-4 | `TUR2/Best/Flat/CLS-4_PSD_Post.psd` | 3 | 24x36 | Featured = slot 1 (middle) |
| FramePSD | `TUR2/Best/Flat/FramePSD.psd` | 2 | 24x36 | Featured = slot 1 (right) |
| Frame 15 | `TUR2/40Vintage.../Frame 15.psd` | 1 | 24x36 | Lifestyle: green velvet couch |
| Frame 32 | `TUR2/40Vintage.../Frame 32.psd` | 1 | 24x36 | Lifestyle: minimalist shelf |

### CRITICAL RULES:

1. **Multi-frame mockups MUST use same-style filler cities** — never mix Classic renders in a Blueprint mockup. Each frame should show a different city from the same theme.

2. **Filler cities MUST use the same render size as the featured city** — if featured uses 24x36, fillers must also be 24x36. Mismatched sizes cause different aspect ratios in the same frame.

3. **For color-variant styles, fillers should use DIFFERENT colors** — e.g., Blueprint CLS-4: Chicago (navy) + Featured (terracotta) + Berlin (forest). Shows the color variety.

### Filler Cities:

| Style | Filler Cities | Source |
|-------|---------------|--------|
| Classic | Pittsburgh, New Orleans, Washington DC, Amsterdam | `DefaultMap_Posted/` |
| Florence | Pittsburgh, New Orleans, Washington DC, Amsterdam | `FlorenceMap_Posted/` |
| Blueprint | Chicago (navy), Berlin (forest), Paris (charcoal) | `BlueprintV3/` |
| MonoMap | Chicago (forest), Berlin (terracotta), Paris (dusty_rose), Rome (charcoal) | `MonoMap/{color}/` |

**Filler renders MUST exist at 24x36 and 18x24 before running batch.** The batch pipeline falls through size preferences: 24x36 → 18x24 → 16x20.

### PSD4 (Unlabeled) — REMOVED
Do NOT generate the plain PSD4 mockup. It was replaced by the labeled PSD4 for color styles.

### Layer-Aware + Blend-Mode Compositing (REQUIRED for any new mockup)

**THE RULE:** Before adding a new PSD mockup template, inspect its layer stack and smart-object blend mode with `psd_tools`. If **either** of these is true, you MUST use the layer-aware compositor — a plain `psd.composite()` + `base.paste(art, ...)` will produce a broken mockup:

1. **Any visible layer sits above the smart object** in the top-level stack (e.g. a hand, a mask, a rolled paper tube, a frame foreground, a plant). A flat paste covers those foreground layers.
2. **The smart object's `blend_mode` is not `NORMAL`** (commonly `MULTIPLY` for frame/lifestyle photography). A flat paste erases shadows that should darken the artwork.

**Reference implementation:** `scripts/compose_new_mockups_atlanta.py` — function `compose_layer_aware(psd_path, art)`. Copy this pattern for any new smart-object-based mockup. It uses three stages:

1. **Below stack** — `psd.composite(layer_filter=...)` where the filter keeps only layers at indices < the smart object's index. This gives the "scene with placeholder poster + baked-in shadows".
2. **Blend the art** — crop the below at the smart-object slot, apply the smart object's blend mode against the fitted art:
   - `BlendMode.NORMAL` → `canvas.alpha_composite(fitted, ...)`
   - `BlendMode.MULTIPLY` → `ImageChops.multiply(below_crop_rgb, fitted_rgb)` then paste
   - Also honor smart-object `opacity` via `Image.blend(below_crop, blended, opacity/255)` if < 255
   - Any blend mode not yet wired up should raise, not silently fall through
3. **Above stack** — iterate layers at indices > the smart-object index, call `layer.composite()` on each (returns RGBA at layer bounds), and `canvas.alpha_composite(layer_img, (layer.left, layer.top))`. This re-overlays hands, masks, tubes, and any other foreground element in the correct order.

**PSD inspection command** — run this first for every new template:
```bash
/c/Users/kimme/miniconda3/envs/py313/python.exe -c "
from psd_tools import PSDImage
psd = PSDImage.open(r'path\to\mockup.psd')
print(f'Canvas: {psd.size}')
for i, l in enumerate(psd):
    print(f'[{i}] {l.kind:12s} {l.name!r:30s} blend={l.blend_mode} opacity={l.opacity} visible={l.visible}')
    if l.kind == 'smartobject':
        print(f'    slot: L={l.left} T={l.top} R={l.right} B={l.bottom}')
        w = getattr(l.smart_object, 'warp', None)
        if w:
            print(f'    warpValue={w.get(b\"warpValue\")} warpPerspective={w.get(b\"warpPerspective\")}')"
```
- If `warpValue` or `warpPerspective` is non-zero, the smart object has a perspective warp and you need an additional `cv2.warpPerspective` step (not yet implemented — document the TODO on the template).
- If the smart-object slot aspect ratio differs from 2:3 (0.6667), `fit_to_slot()` will pad with white. Acceptable for frames with inset mats; check visually.

**Never** fall back to Photopea/Photoshop for batch work — the layer-aware compositor reproduces what Photopea does when you replace a smart object, and it runs programmatically over any number of cities.

---

## 6. Detail Crop Rules <a name="detail-crop-rules"></a>

Every listing gets a detail crop with the "EVERY STREET. EVERY DETAIL." badge.

- **Source:** 16x20 render
- **Crop:** Center 40% of map area (avoid text/header regions)
- **Blueprint:** Map area starts at 22% from top (header is at top)
- **Classic/Florence:** Map area is top 76% (text at bottom)
- **Output:** 2000×2000 JPEG, quality 92, 300 DPI
- **Badge:** Dark semi-transparent rounded rectangle, top-left at 4% margin, bold white text
- **Function:** `_draw_detail_badge()` from `etsy/image_composer.py`

---

## 7. Listing Text Rules <a name="listing-text-rules"></a>

### Format (matches Florence production listings):
```
======================================================================
ETSY LISTING — {City}, {State/Country} ({Style Name})
======================================================================

TITLE
----------------------------------------
{SEO-optimized title, max 140 chars}

TAGS
----------------------------------------
{13 comma-separated tags, max 20 chars each, must include "custom-map" for color variants}

DESCRIPTION
----------------------------------------
{Full description with emoji headers, diamond bullets, sections for:
 - Product intro
 - How to Order (numbered steps)
 - Color options (if applicable)
 - Product options (unframed, framed)
 - Available sizes (metric + imperial)
 - About this design
 - Shipping & delivery
 - Gift occasions
 - Questions CTA}

VARIATIONS (SKU / Size / Format / Price)
----------------------------------------
{SKU table}
```

### Emoji Style (from best-seller research):
- `📍` Product intro
- `🔸` Section dividers (HOW TO ORDER, etc.)
- `🎨` Color options
- `🖼️` Product options
- `📐` Available sizes
- `🚚` Shipping
- `💛` Gift occasions
- `❓` Questions
- `◈` Diamond bullets for list items

### Tags MUST include:
- 4 city-specific tags: `{city} map print`, `{city} wall art`, `{city} poster`, `{city} gift`
- `custom-map` (with dash!) for color-variant styles (triggers Gelato custom workflow)
- 9 style-specific tags

### SKU Format:
`GLC-{STYLE}-{FORMAT}-{SIZE}`
- Styles: `BLUE` (Blueprint), `MONO` (MonoMap), `FLOR` (Florence), no prefix (Classic = `GLC-{CITY}`)
- Formats: `DIG`, `UNF`, `FBK`, `FWH`
- Sizes: `8X10`, `11X14`, `16X20`, `18X24`, `24X36`

### NEVER use internal theme names in customer-facing text:
- "Blueprint" → use "Detailed Mosaic", "Shaded Mosaic"
- Internal names are for code only

---

## 8. Image Upload Order <a name="image-upload-order"></a>

### Color-Variant Styles (Blueprint, MonoMap) — 10 images:
| Rank | Image | Purpose |
|------|-------|---------|
| 1 | `{slug}_main.jpg` | Primary thumbnail (city in frame) |
| 2 | `{slug}_psd4_labeled.jpg` | Color options showcase with labels |
| 3 | Single-frame lifestyle mockups | Room scenes |
| 4-8 | More mockups (flat + lifestyle) | Variety of settings |
| 9 | Multi-frame mockup | Shows we offer other cities |
| 10 | `{slug}_detail_crop.jpg` | "EVERY STREET. EVERY DETAIL." close-up |

### Single-Style (Classic, Florence) — 10 images:
| Rank | Image | Purpose |
|------|-------|---------|
| 1 | `{slug}_main.jpg` | Primary thumbnail |
| 2-8 | Mockups (flat + lifestyle) | Various room settings |
| 9 | Size comparison or multi-frame | |
| 10 | `{slug}_detail_crop.jpg` | Detail close-up with badge |

---

## 9. Color Variant Styles <a name="color-variant-styles"></a>

### Blueprint (4 colors):
- Navy, Forest, Terracotta (default), Charcoal
- Each city rendered in ONE default color (terracotta)
- Color showcase via labeled PSD4 mockup and color swatch image
- Orders are made-to-order: customer picks color in personalization
- `custom-map` tag required

### MonoMap (6 colors):
- Charcoal, Navy (default), Forest, Terracotta, Dusty Rose, Black
- Same approach: render one color, showcase all via PSD4 + swatch
- `custom-map` tag required

### Labeled PSD4:
- **Title:** "Choose Your Color Style" across top
- **4 frames:** Each shows a different color (same city if all colors rendered, or shared showcase of 4 cities)
- **Labels:** Below each frame (top row labels at y=frame.bottom+55, bottom row at y=frame.bottom+80)
- **Font:** Montserrat Bold, 72pt labels, 90pt title
- **City-specific** for cities with all 4 colors rendered (filler cities: Nashville, Chicago, Berlin, Paris)
- **Shared showcase** for all other cities (copies `BlueprintV3/shared_psd4_labeled.jpg`)

### Shared Showcase PSD4:
Must be regenerated when filler cities change. Location:
- `etsy/renders/BlueprintV3/shared_psd4_labeled.jpg`
- `etsy/renders/MonoMap/shared_psd4_labeled.jpg`

---

## 10. Etsy API Push <a name="etsy-api-push"></a>

### Pre-requisites:
- Auth token refreshed: `python -m etsy.auth --refresh`
- Token expires every ~1 hour during batch pushes

### Create Draft Listing:
```python
client.create_draft_listing(
    shop_id=64614087,
    title=title,                         # Max 140 chars
    description=description,
    price=4.20,                          # Base price (smallest variant)
    quantity=999,
    tags=tags,                           # Max 13 tags, 20 chars each, NO periods
    who_made="i_did",
    when_made="made_to_order",
    taxonomy_id=1029,                    # Art > Prints
    listing_type="physical",
    shipping_profile_id=299396504426,    # Gelato: Free shipping
    return_policy_id=1470278944285,
    shop_section_id=57587152,            # City Maps (or 57768965 for Custom Maps)
    readiness_state_id=1470278628937,
)
```

### Upload Images:
- Max 10 images per listing
- `client.upload_listing_image(shop_id, listing_id, path, rank=N)`
- Rate limit: 0.3s between uploads

### Set Variants (20 per listing):
- 5 Digital + 5 Unframed + 5 Framed Black + 5 Framed White
- Property IDs: 513 (Format), 514 (Size)
- Each offering needs `readiness_state_id`

### Enable Personalization:
```python
client.update_listing(shop_id, listing_id,
    is_personalizable=True,
    personalization_is_required=True,
    personalization_instructions="...",
    personalization_char_count_max=256,
)
```

### Tags Warning:
- Etsy rejects tags with periods (e.g., "st. louis" fails)
- Strip periods before pushing: `tag.replace(".", "")`
- Max 20 chars per tag

---

## 11. Gelato Connection <a name="gelato-connection"></a>

### Gelato Store ID: `3e2b887f-ccb6-465d-9000-adfc312b0b1f`

### Process:
1. **Sync in Gelato dashboard** — pulls new Etsy listings into Gelato
2. **Run connect script** — 3 API calls per variant:
   - PATCH variant with `productUid`
   - POST print-file with file URL
   - PATCH variant with `connectionStatus: "connected"`

### Product UIDs:
```
Unframed 8x10:   flat_8x10-inch-200x250-mm_170-gsm-65lb-uncoated_4-0_ver
Unframed 11x14:  flat_11x14-inch-270x350-mm_170-gsm-65lb-uncoated_4-0_ver
Unframed 16x20:  flat_16x20-inch-400x500-mm_170-gsm-65lb-uncoated_4-0_ver
Unframed 18x24:  flat_18x24-inch-450x600-mm_170-gsm-65lb-uncoated_4-0_ver
Unframed 24x36:  flat_24x36-inch-600x900-mm_170-gsm-65lb-uncoated_4-0_ver

Framed Black:    framed-poster_{size}-inch-{mm}_black_170-gsm-65lb-uncoated_4-0_ver
Framed White:    framed-poster_{size}-inch-{mm}_white_170-gsm-65lb-uncoated_4-0_ver
```

### For custom-map listings (color variants):
- Use placeholder image: `https://www.dropbox.com/scl/fi/nz3sdcm86f3imk7g4h8rc/placeholder.png?rlkey=mmls03ibtqooz4fw944hm90yj&dl=1`
- Gelato sees `custom-map` tag and holds order for manual fulfillment
- When order comes in: render specific city+color → upload to Dropbox → update Gelato via `custom_fulfill.py`

### For pre-made city listings (single color):
- Upload actual render to Dropbox first
- Gelato CSV file URL points to Dropbox shared link
- `batch_dropbox_upload.py` or style-specific upload script

### Connect Script:
- Blueprint: `python scripts/gelato_connect_blueprint.py`
- General: `python -m etsy.gelato_connect --city "City Name"`

---

## 12. Custom Map vs Pre-Made <a name="custom-map-vs-pre-made"></a>

| | Pre-Made | Custom (color variant) |
|---|---|---|
| **Render timing** | Pre-rendered, uploaded to Dropbox | Rendered on-demand after order |
| **Gelato file** | Actual render Dropbox link | Placeholder image |
| **Etsy tag** | Normal tags | Must include `custom-map` |
| **Personalization** | Optional (for text customization) | Required (city + color choice) |
| **Dropbox upload** | Yes, before listing | No (placeholder only) |
| **Fulfillment** | Automatic via Gelato | Manual via `custom_fulfill.py` |

**Blueprint and MonoMap are custom-map** because customers choose a color.
**Classic and Florence are pre-made** because there's one fixed look per city.

---

## 13. Known Issues <a name="known-issues"></a>

### Coastal City Water Rendering
Blueprint/MonoMap polygonize water areas into colored blocks for coastal cities. The water overlay doesn't always fully cover polygonized coastline blocks.

**Affected cities (removed from Blueprint batch):** San Francisco, Seattle, Lisbon, Copenhagen, Honolulu

**Fix needed:** Clip blocks to land area before coloring, or render ocean at higher z-order. See `memory/feedback_coastal_water_rendering.md`.

### Etsy Tag Periods
Tags containing periods (e.g., "st. louis map") are rejected by Etsy API. Strip periods before pushing.

### Gelato Connect Retries
Sometimes Step 1 (set UID) succeeds but Step 2 (upload file) fails. Retrying usually works because the UID is already set. If all 3 steps fail, re-sync in Gelato dashboard first.

### Blueprint Content Detection (FIXED)
The old Blueprint compositor used content-bounds detection that stripped white space (including lakes/ocean), making maps appear zoomed in. **Fixed by removing content detection** — maps now resize directly to fill the poster area.

---

## 14. Commands Quick Reference <a name="commands-quick-reference"></a>

### Full Batch (render + mockups + text, no Etsy push):
```bash
python scripts/batch_universal.py --style blueprint --skip-etsy --resume
```

### Single City Test:
```bash
python scripts/batch_universal.py --city "Chicago" --style blueprint --skip-etsy
```

### Dry Run (see what would happen):
```bash
python scripts/batch_universal.py --style blueprint --dry-run
```

### Push to Etsy as Drafts:
```bash
# Refresh token first!
python -m etsy.auth --refresh
python scripts/batch_universal.py --style blueprint --resume
```

### Gelato Connect (after syncing in dashboard):
```bash
python scripts/gelato_connect_blueprint.py
python scripts/gelato_connect_blueprint.py --city chicago --dry-run
```

### Regenerate Listing Text Only:
```python
from etsy.blueprint_listing import generate_blueprint_listing_text
generate_blueprint_listing_text("chicago", output_dir="etsy/renders/chicago_blueprint")
```

### Regenerate PSD4 Labels Only:
```python
from scripts.batch_universal import create_labeled_psd4
create_labeled_psd4(city, style, out_dir)
```

### Regenerate Detail Crop Only:
```python
from scripts.batch_universal import generate_detail_crop
generate_detail_crop(city, style, out_dir)
```

### Upload to Dropbox (pre-made styles only):
```bash
python scripts/batch_dropbox_upload_blueprint.py --token TOKEN
```

---

## Starting a New Style Batch — Checklist

1. [ ] Add style config to `etsy/style_config.py` (pricing, SKU prefix, extent, etc.)
2. [ ] Create style-specific listing text module (see `etsy/blueprint_listing.py` as template)
3. [ ] Render filler cities in all colors/sizes needed for mockups (24x36 + 18x24 + 16x20)
4. [ ] Create shared PSD4 labeled showcase image
5. [ ] Test render ONE city fully (renders + mockups + detail + text)
6. [ ] Review the test city before batch run
7. [ ] Run full batch with `--skip-etsy` first
8. [ ] Review a few random cities
9. [ ] Push to Etsy as drafts
10. [ ] Sync in Gelato dashboard
11. [ ] Run Gelato connect script
12. [ ] Review on Etsy, publish when ready
