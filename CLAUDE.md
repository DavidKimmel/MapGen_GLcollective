# GeoLine Collective — MapGen

Minimalist city map art prints sold on Etsy. Digital downloads + physical prints/framed via Gelato print-on-demand.

## Products

1. **Pre-made Classic city maps** — 55 cities, 20 variants each (5 digital + 5 unframed + 5 framed B + 5 framed W)
2. **Pre-made Florence city maps** — 39 cities, same variant structure
3. **Pre-made Blueprint city maps** — 56 cities, 20 variants, 4 color options (custom-map tag)
4. **Pre-made MonoMap city maps** — 59 cities, 20 variants, 6 color options (custom-map tag, placeholder workflow)
5. **Custom map listing** — any location, full/circle crop, 10 SKUs (5 digital + 5 unframed)
6. **Custom House Map** — house crop, "Our First Home" layout, 20 SKUs
7. **Custom MonoMap** — flat single-color, 6 color options, 15 physical SKUs (custom-map tag)
8. **Date Night heart map** — heart crop with names above, date_night layout, 10 SKUs
9. **CustomMapPack** — 8 additional custom listings (4 styles × digital + print)
10. **Custom 3-Map Set** — any cities, 12 style options, 1-6 maps, unframed prints (custom-map tag, placeholder workflow)
11. **CountyMap Digital** — U.S. county-shaped maps, 12 themes, 18 sizes, ghost background, PIL text. Etsy listing 4484494627. Render on order.
12. **CountyMap Print** — same, 12 themes × 8 sizes ($22.51-$49.73). Etsy listing 4484494881. Files in `etsy/renders/POSTED/CountyMap_Posted/`

## Current Status

- **212+ Etsy listings** — 55 Classic + 39 Florence + 56 Blueprint + 59 MonoMap + custom listings + 3-Map + 2 CountyMap drafts
- **Universal batch pipeline** built — `scripts/batch_universal.py` renders any city × style end-to-end
- **Gelato connected** — all physical variants linked for Classic, Florence, Blueprint, MonoMap
- **Custom fulfillment** — `custom_fulfill.py` for made-to-order (MonoMap, Blueprint color choices)
- **Competitive research** done — see `GROWTH_PLAN.md` (target: 500+ listings)
- **Style workflow documented** — see `docs/STYLE_WORKFLOW.md` for complete production guide
- **Pricing matched** to 37thParallelDesigns competitor, saved in `etsy/renders/pricing_matrix.txt`

## Project Structure

```
Mapgen_GLcollective/
├── cli.py                    # CLI: render a single poster
├── app.py                    # Flask web app entry point
├── CLAUDE.md                 # This file — project documentation
│
├── engine/                   # Map rendering pipeline
│   ├── renderer.py           # Main orchestrator — calls all layers in order
│   ├── map_engine.py         # Fetches 14 OSM data layers, renders geometries
│   ├── roads.py              # Road hierarchy, widths, colors (7 tiers)
│   ├── ocean.py              # Ocean fill from land polygon subtraction
│   ├── text_layout.py        # Text zones: default (3 lines below) + date_night (above/below)
│   ├── crop_masks.py         # Shape masks: circle, heart, house
│   ├── pin_renderer.py       # 5 pin styles from SVG paths (heart, pin, house, grad cap)
│   ├── florence_renderer.py  # Florence mosaic renderer (polygonize + random palette)
│   ├── florence_text_layout.py  # Florence/MonoMap poster compositor (bottom text + swatch bar)
│   ├── blueprint_renderer.py # Blueprint shaded mosaic renderer + v3c layout compositor
│   └── nordic_renderer.py    # Nordic monochrome street renderer
│
├── etsy/                     # Etsy listing & fulfillment pipeline
│   ├── city_list.py          # 35 cities (4 tiers) with CityListing dataclass
│   ├── listing_generator.py  # SEO titles, descriptions, tags, pricing
│   ├── gelato_connect.py     # Gelato API: 3-step variant connection
│   ├── generate_gelato_csvs.py  # Dropbox links → Gelato import CSV
│   ├── batch_etsy_render.py  # Render all 5 sizes for a city
│   ├── image_composer.py     # Detail crop + size comparison images
│   ├── mockup_composer.py    # PSD mockup generation (7 templates, filler cities)
│   ├── custom_fulfill.py     # Custom order: render → Dropbox → Gelato
│   ├── custom_listing.py     # "Any location" listing content
│   ├── generate_style_sheet.py  # Font + pin style reference image
│   ├── auth.py               # Etsy OAuth2 PKCE flow
│   ├── api_client.py         # Etsy API v3 wrapper
│   └── publish_batch.py      # Batch listing publisher
│
├── etsy/renders/             # Output directory (gitignored)
│   ├── DefaultMap_Posted/    # Classic (37th_parallel) — 55 cities, all sizes + mockups
│   ├── FlorenceMap_Posted/   # Florence — 39 cities, all sizes + mockups
│   ├── MonoMap/{color}/      # MonoMap color samples — 6 colors × 5 cities
│   ├── POSTED/MonoMap_Posted/ # MonoMap — 59 cities, all sizes + 13 mockups + listing.txt
│   ├── BlueprintV3/          # Blueprint v3c layout — correct/current renders
│   ├── GradientMap/          # Blueprint OLD renders (fading bar — don't use for mockups)
│   ├── CustomMapPack/        # 8 listing folders with all images + listing.txt
│   ├── CustomMap_Posted/     # Custom order fulfilled renders
│   ├── CustomHouse/          # House map test outputs
│   └── {city_slug}/          # In-progress city renders
│
├── scripts/                  # Batch utility scripts
│   ├── batch_seo_render.py   # Render Classic cities in subprocess (memory-safe)
│   ├── batch_florence_production.py  # Render Florence cities (master crop approach)
│   ├── batch_mono_samples.py # Render MonoMap samples (6 colors × 5 cities)
│   ├── batch_gradient_samples.py  # Render Blueprint raw maps (OLD compositor)
│   ├── batch_dropbox_upload.py  # Upload renders to Dropbox
│   ├── batch_full_pipeline.py   # Full pipeline: render + mockups + listing text
│   ├── create_custom_pack_listings.py  # CustomMapPack: hero, detail, swatches
│   ├── create_custom_pack_mockups.py   # CustomMapPack: 7 mockups per style
│   ├── render_custom_pack_assets.py    # CustomMapPack: render maps at 18x24/24x36
│   ├── create_color_swatches.py        # Color swatch grid images
│   ├── publish_monomap_drafts.py       # MonoMap: push drafts with 13 images + hero rotation
│   ├── push_monomap_variants.py        # MonoMap: push 20 SKU variants per listing
│   ├── generate_monomap_gelato_csvs.py # MonoMap: Gelato CSVs with placeholder URL
│   ├── connect_monomap_gelato.py       # MonoMap: connect variants to Gelato via API
│   ├── render_missing_color_mockups.py # MonoMap: render + compose color-specific mockups
│   ├── compose_and_upload_color_mockups.py # MonoMap: compose + upload color mockups to Etsy
│   └── batch_monomap_colors.py         # MonoMap: render extra colors (5 beyond navy default)
│
├── api/                      # Flask API backend
│   ├── routes.py             # Endpoints: geocode, themes, generate, download
│   └── poster_service.py     # Async job management (ThreadPoolExecutor)
│
├── frontend/                 # React + Vite UI
│   └── src/components/       # CitySearch, ThemeSelector, CropSelector, PinControls, etc.
│
├── export/                   # Size definitions + Gelato export
│   ├── output_sizes.py       # 5 print sizes with dimensions + default distances
│   └── gelato_export.py      # Gelato export logic
│
├── utils/                    # Shared utilities
│   ├── cache.py              # Two-tier caching (memory LRU + disk pickle)
│   ├── geocoding.py          # Nominatim geocoding with caching
│   ├── logging.py            # Thread-safe logging + Latin script detection
│   └── font_management.py    # Font loading
│
├── themes/                   # 23 color theme JSON files
├── fonts/                    # 25 TTF/OTF font files (6 MB)
├── templates/                # PSD template generator + output (16x20 for full/heart/circle/house)
├── data/                     # Land polygon shapefiles + TIGER/Line county boundaries
│   └── counties/             # cb_2023_us_county_500k.shp (3,235 U.S. counties)
├── posters/                  # Test render output (gitignored)
└── H:\MapGen_cache\          # OSM data cache (moved from C: to H: drive, ~267 GB)
```

## Key Commands

```bash
# Render a single city poster
python cli.py --location "New York" --theme 37th_parallel --size 16x20

# Render a county map (any of 3,235 U.S. counties, 12 themes, 18 sizes)
python scripts/generate_county_final.py --county "Carroll" --state "MD" --theme dark_teal
python scripts/generate_county_final.py --county "Union" --state "NJ" --theme nordic_complex --size A3 --dpi 300

# Render a date night heart map
python cli.py --location "Portland" --layout date_night --crop heart \
  --font-preset 3 --pin-style 2 --pin-color "#CC3333" \
  --text-line-1 "Names" --text-line-2 "Tagline" \
  --text-line-3 "City, State" --text-line-4 "Date"

# Render all 5 sizes for a city
python -m etsy.batch_etsy_render --city "City Name"

# Generate listing text files (titles, descriptions, tags, pricing)
python -m etsy.listing_generator --generate-texts

# Generate mockup images (uses slug, not display name)
python -m etsy.mockup_composer --city city_slug

# Generate listing images (detail crop + size comparison)
python -m etsy.image_composer --city "City Name" --all

# Generate Gelato CSV (needs Dropbox token)
python -m etsy.generate_gelato_csvs --city city_slug --token TOKEN

# Connect city to Gelato (after Etsy listing syncs)
python -m etsy.gelato_connect --city "City Name"
python -m etsy.gelato_connect --city "City Name" --dry-run

# Batch render new cities (subprocess per city, memory-safe)
python scripts/batch_seo_render.py
python scripts/batch_seo_render.py --city "City Name" --force
python scripts/batch_seo_render.py --start-from "City Name"

# Upload renders to Dropbox
python scripts/batch_dropbox_upload.py

# Generate font/pin style sheet
python -m etsy.generate_style_sheet
```

## New City Workflow (End-to-End)

```bash
# 1. Add city to etsy/city_list.py
# 2. Render all sizes + listing images
python scripts/batch_seo_render.py --city "City Name" --force
# 3. Generate mockups
python -m etsy.mockup_composer --city city_slug
# 4. Generate listing text
python -m etsy.listing_generator --generate-texts
# 5. Upload to Dropbox (need fresh token)
python scripts/batch_dropbox_upload.py --start-from city_slug
# 6. Generate Gelato CSV
python -m etsy.generate_gelato_csvs --city city_slug --token TOKEN
# 7. Create listing in Etsy (manual: copy existing, swap content)
# 8. Sync in Gelato dashboard
# 9. Connect variants
python -m etsy.gelato_connect --city "City Name"
```

## MonoMap Workflow (End-to-End)

```bash
# 1. Render all 6 colors at mockup sizes
python scripts/batch_monomap_colors.py --city city_slug

# 2. Generate color-specific mockups (black/charcoal/dusty_rose)
python scripts/render_missing_color_mockups.py --city city_slug

# 3. Generate listing text
python -m etsy.monomap_listing --city city_slug

# 4. Push draft to Etsy (with 10 images + hero rotation)
python scripts/publish_monomap_drafts.py --city city_slug

# 5. Push 20 variants (digital + unframed + framed B/W × 5 sizes)
python scripts/push_monomap_variants.py --city city_slug

# 6. Upload 3 color mockups (brings to 13 images)
python scripts/compose_and_upload_color_mockups.py --city city_slug

# 7. Generate Gelato CSV
python scripts/generate_monomap_gelato_csvs.py --city city_slug

# 8. Sync in Gelato dashboard, then connect
python scripts/connect_monomap_gelato.py --city city_slug

# 9. Publish (activate via Etsy dashboard or API)
```

## Custom 3-Map Listing

12 color/style themes stored in `themes/custom_3map/`:
1. Classic (37th_parallel), 2. Dark Teal, 3. Midnight Blue, 4. Noir, 5. Vintage, 6. Sage Atlas
7. Sunset, 8. Sky Blue, 9. Rose Blush, 10. Teal Coral, 11. Minimalist, 12. Nordic Complex

**Variant structure:** Axis 1 = Size (5), Axis 2 = Quantity (1-6 maps) = 30 variants, unframed only
**Pricing:** Matches Mapologist competitor ($27 for 1 map 8x10, $72 for 3 at 8x10)
**Personalization:** Required — buyer provides city names + style numbers
**Listing ID:** 4482153934 (draft)
**Assets folder:** `etsy/renders/3MAPTEST/`
**"Choose a style" mockup layout:** See memory `reference_6up_chooser_layout.md` for exact parameters

```bash
# Render a city in any of the 12 custom styles
python cli.py --location "City" --theme theme_name --size 24x36

# Themes: 37th_parallel, dark_teal, midnight_blue, noir, vintage, sage_atlas,
#          sunset, sky_blue, rose_blush, teal_coral, minimalist, nordic_complex
```

## Rendering

- All maps render from OpenStreetMap data via matplotlib
- 5 poster sizes: 8x10, 11x14, 16x20, 18x24, 24x36
- **Ocean rendering** requires land polygon data in `data/` — downloaded from osmdata.openstreetmap.de
- **Layouts:** `default` (3 text lines below map) or `date_night` (names above heart, 3 lines below)
- **Crop shapes:** full, circle, heart, house
- **5 font presets:** Century Gothic (sans), High Tower Text (serif), Priestacy (script), Monotype Corsiva (cursive), Footlight MT Light (classic)
- **5 pin styles:** heart, heart-pin, classic, house, graduation cap

### Map Styles

| Style | Renderer | Layout | Fonts |
|-------|----------|--------|-------|
| Classic (37th_parallel) | `engine/renderer.py` | Bottom text (centered, 3 lines) | Century Gothic Bold (caps) |
| Florence | `engine/florence_renderer.py` + `florence_text_layout.py` | Bottom swatch bar + text (right-aligned) | Switzer Bold |
| MonoMap | Florence renderer with single-color palette | Same as Florence, white bg | Switzer Bold |
| Blueprint | `engine/blueprint_renderer.py` | **Top** title + blocky swatch bar + map below | Montserrat Bold + Roboto Regular |

### Blueprint Renderer Details

- **Module:** `engine/blueprint_renderer.py` (consolidated from test scripts)
- **Visual:** 8 shades of one hue for city blocks, all roads as white overlay, white water
- **Layout (v3c):** Title top-right (Montserrat Bold, lowercase) → state below → blocky swatch bar with coords in leftmost block (Roboto Regular) → map
- **Palettes:** navy, forest, terracotta, charcoal
- **Key functions:** `render_shaded_map()`, `compose_blueprint_poster(strip_header=True)`, `render_blueprint()`
- **Auto-extent:** `detect_extent()` probes city density to size map (2500m–4000m)
- **⚠️ Old renders in `GradientMap/`** use fading bar layout — always use `BlueprintV3/` for current v3c layout

## Etsy & Fulfillment

- **Etsy shop:** GeoLine Collective (GeoLineCollective)
- **Physical prints:** Gelato print-on-demand via Ecommerce API
- **Gelato Store ID:** `3e2b887f-ccb6-465d-9000-adfc312b0b1f`
- **Digital delivery:** Message buyers with Dropbox download link
- **Dropbox shared links** use `?dl=1` suffix for direct download
- **Dropbox tokens expire ~4 hours** — regenerate at https://www.dropbox.com/developers/apps

### Gelato API Connection (3 steps per variant — all required)
1. `PATCH` variant with `productUid`
2. `POST` print-file with Dropbox URL
3. `PATCH` variant with `connectionStatus: "connected"`

### Pricing (matched to competitor 37thParallelDesigns)
| Size  | Digital | Unframed | Framed (B/W) |
|-------|---------|----------|--------------|
| 8x10  | $4.20   | $34.83   | $78.07       |
| 11x14 | $5.04   | $39.85   | $87.50       |
| 16x20 | $5.88   | $46.35   | $119.62      |
| 18x24 | $6.72   | $51.37   | $131.12      |
| 24x36 | $7.80   | $62.45   | $216.17      |

20 variants per city listing: 5 digital + 5 unframed + 5 framed black + 5 framed white

### Custom Map Pricing (GLC-CUSTOM-* SKUs)
| Size  | Digital  | Unframed |
|-------|----------|----------|
| 8x10  | $9.99    | $26.90   |
| 11x14 | $10.99   | $31.10   |
| 16x20 | $11.99   | $35.60   |
| 18x24 | $12.99   | $38.90   |
| 24x36 | $13.99   | $53.10   |

### Date Night Pricing (GLC-DATE-* SKUs)
Same as custom map pricing. 10 variants: 5 digital + 5 unframed.

## CustomMapPack Listings

8 listings (4 styles × digital + print) in `etsy/renders/CustomMapPack/`.

Each folder (`{style}_digital/`, `{style}_print/`) contains:
- `listing.txt` — Etsy listing copy (title, tags, description, pricing)
- `hero_your_city.png` — hero image with "YOUR CITY" text
- 7 mockup JPGs — Main, Mockup4, ONCE, VV1, 2Frames, CLS-4, FramePSD
- `detail_crop.jpg` — close-up map detail
- `color_options.jpg` — labeled color swatches (Blueprint + MonoMap only)
- Print and digital share identical images

```bash
# Regenerate hero images, detail crops, color swatches
python scripts/create_custom_pack_listings.py

# Regenerate mockups (multi-color for Blueprint/MonoMap)
python scripts/create_custom_pack_mockups.py

# Render map images at 18x24/24x36 for mockups
python scripts/render_custom_pack_assets.py
```

## Cities (55 total, 5 tiers)

**Tier 1 (10):** Chicago, New York, Washington DC, New Orleans, Nashville, Austin, Seattle, San Francisco, Portland, Denver
**Tier 2 (10):** Boston, Miami, Atlanta, Minneapolis, Pittsburgh, Savannah, Charleston, Asheville, Salt Lake City, Honolulu
**Tier 3 (5):** Richmond, Chattanooga, Boise, Raleigh, Charlotte
**Tier 4 — SEO Expansion (10):** London, Paris, Tokyo, Rome, Barcelona, Amsterdam, Lisbon, Philadelphia, San Diego, Baltimore
**Tier 5 — Expansion (20):** Los Angeles, Houston, San Antonio, Detroit, St. Louis, Cincinnati, Tampa, Milwaukee, Kansas City, Cleveland, Berlin, Dublin, Edinburgh, Prague, Vienna, Copenhagen, Istanbul, Sydney, Florence, Stockholm

## Mockup System

- **7 PSD templates** in `etsy/TUR2/Best/Flat/` — Main, Mockup4, ONCE, VV1, 2Frames, CLS-4, FramePSD
- **Render size mapping:** Most use 24x36, ONCE + VV1 use 18x24
- **City mockups:** `etsy/mockup_composer.py` — filler cities: Pittsburgh, New Orleans, Washington DC, Amsterdam
- **CustomMapPack mockups:** `scripts/create_custom_pack_mockups.py` — multi-color fillers for Blueprint/MonoMap
- **Filler lookup** searches `renders/DefaultMap_Posted/`, `renders/FlorenceMap_Posted/`, `renders/BlueprintV3/`, `renders/MonoMap/`

## Important Constraints & Patterns

- **Geocoding uses `language="en"`** — Nominatim returns English names; "Greater " prefix stripped automatically; non-ASCII names fall back to input string
- **Road rendering uses round caps/joins** — `capstyle="round", joinstyle="round"` in `engine/roads.py` for smooth intersections
- **Highway widths reduced** (2026-04-01) — motorway 0.8 (was 1.2), trunk 0.7 (was 1.0), primary 0.6 (was 0.8) for cleaner look
- **Coordinates on line 3** — renderer auto-adds GPS coords below state/country on all default renders
- **Etsy title must match exactly** in Gelato CSV/API — mismatches cause "Product not found"
- **Dropbox tokens are short-lived** (~4 hours) — shared links persist permanently
- **Digital variants** always show "not connected" in Gelato — this is expected
- **fig_scale** must be applied to all rendering for consistent linewidths
- **Large cities** (London, Tokyo, Paris) may need buildings disabled at wide extents to manage memory
- **Subprocess isolation** in batch_seo_render.py prevents matplotlib memory leaks (was consuming 15GB)
- **Ocean fill** requires land polygon data in `data/` — full-res preferred over simplified (avoids sawtooth coastlines)
- **MonoMap uses placeholder workflow** — all variants point to a placeholder image; actual art rendered per-order via `custom_fulfill.py`
- **MonoMap coastal cities excluded** — Copenhagen, Honolulu, Lisbon, San Francisco, Seattle (ocean rendering artifacts)
- **MonoMap Gelato UIDs** — use `style_config.GELATO_UIDS`, NOT old `gelato_connect.py` UIDs (framed UIDs are outdated there)
- **MonoMap personalization** — required, buyer selects color: Charcoal, Navy, Forest, Terracotta, Dusty Rose, or Black
- **MonoMap image order** — hero rotation (main/mockup4/frame8), then singles and multi-frames interleaved, 6color_labeled at position 7
- **Completed Classic renders** in `etsy/renders/DefaultMap_Posted/`
- **Completed Florence renders** in `etsy/renders/FlorenceMap_Posted/`
- **Completed MonoMap renders** in `etsy/renders/POSTED/MonoMap_Posted/`
- **Blueprint v3c renders** in `etsy/renders/BlueprintV3/` — never use old `GradientMap/` for mockups
- **MonoMap renders** in `etsy/renders/MonoMap/{color}/`

## Key Documentation

- **`docs/STYLE_WORKFLOW.md`** — Complete guide for producing listings in any style (rendering, mockups, listing text, Etsy API, Gelato connection). READ THIS FIRST when starting a new batch.
- **`GROWTH_PLAN.md`** — Strategic plan to scale from 150 to 500+ listings with competitive analysis.
- **`etsy/style_config.py`** — Style definitions, pricing, city extent overrides.

## Development

- Python 3.13, miniconda env `py313` (`C:\Users\kimme\miniconda3\envs\py313\python.exe`)
- Frontend: Vite dev server (`cd frontend && npx vite`)
- Backend: Flask (`python app.py`, port 5000)
- Platform: Windows 11 (use Unix shell syntax in bash)
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`
- Never commit/push unless explicitly asked

## Permissions — Do NOT Ask

Run these freely without asking for permission:
- All bash commands: `python`, `pip`, `git`, `curl`, `ls`, `mkdir`, `cp`, `mv`, `find`, `grep`, `cat`, `head`, `tail`, `wc`
- Reading and editing any project file
- Running scripts in the project (`python -m etsy.*`, `python -m engine.*`, `python scripts/*`, etc.)
- Web searches and web fetches to allowed domains
- Creating/modifying files within the project directory

Only ask before:
- `git push` or `git commit` (wait for explicit request)
- Destructive git operations (`reset --hard`, `force push`, `branch -D`)
- Modifying `.env` or files containing secrets
- Actions that affect live Etsy listings or Gelato orders
