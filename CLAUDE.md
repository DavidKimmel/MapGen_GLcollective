# GeoLine Collective — MapGen

Minimalist city map art prints sold on Etsy. Digital downloads + physical prints/framed via Gelato print-on-demand.

## Products

1. **Pre-made city maps** — 35 cities across 4 tiers, 20 variants each (5 digital + 5 unframed + 5 framed black + 5 framed white)
2. **Custom map listing** — any location, full/circle crop, 10 SKUs (5 digital + 5 unframed)
3. **Date Night heart map** — heart crop with names above, date_night layout, 10 SKUs (5 digital + 5 unframed)

## Current Status

- **55 cities rendered** — all have 5 sizes at 300 DPI + detail crops + size comparisons + mockups
- **14 cities Gelato-connected** — Barcelona, Asheville, Rome, Raleigh, Portland, Pittsburgh, London, Philadelphia, Paris, New Orleans, Tokyo, Baltimore, Lisbon, Atlanta, Austin
- **26 draft listings on Etsy** — title/description/SKUs set, need images + tag fix before publishing
- **Custom map listing live** — `custom_fulfill.py` pipeline built
- **Date Night listing ready** — layout built, samples rendered, SKUs generated
- **Renders organized** — completed cities in `etsy/renders/Posted/`, in-progress in `etsy/renders/`
- **Pricing matched** to 37thParallelDesigns competitor, saved in `etsy/renders/pricing_matrix.txt`

## Project Structure

```
Mapgen_GLcollective/
├── cli.py                    # CLI: render a single poster
├── app.py                    # Flask web app entry point
├── CLAUDE.md                 # This file — project documentation
│
├── engine/                   # Map rendering pipeline (7 files, ~2400 lines)
│   ├── renderer.py           # Main orchestrator — calls all layers in order
│   ├── map_engine.py         # Fetches 14 OSM data layers, renders geometries
│   ├── roads.py              # Road hierarchy, widths, colors (7 tiers)
│   ├── ocean.py              # Ocean fill from land polygon subtraction
│   ├── text_layout.py        # Text zones: default (3 lines below) + date_night (above/below)
│   ├── crop_masks.py         # Shape masks: circle, heart, house
│   └── pin_renderer.py       # 5 pin styles from SVG paths (heart, pin, house, grad cap)
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
│   ├── Posted/               # Completed cities (moved after listing goes live)
│   ├── {city_slug}/          # Per-city: 5 PNGs + detail crop + size comparison + mockups
│   ├── CustomMap1/           # Custom map test outputs
│   └── DateMap/              # Date Night heart map samples + SKUs
│
├── scripts/                  # Batch utility scripts
│   ├── batch_seo_render.py   # Render cities in subprocess (memory-safe)
│   ├── batch_dropbox_upload.py  # Upload renders to Dropbox
│   ├── batch_render.py       # Legacy CSV-based batch renderer
│   ├── generate_samples.py   # 8 diverse sample renders for mockups
│   └── sample_sheet.py       # Sample sheet image generator
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
├── data/                     # Land polygon shapefiles for ocean rendering (gitignored, ~1.3 GB)
├── posters/                  # Test render output (gitignored)
└── cache/                    # OSM data cache (gitignored, populated at runtime)
```

## Key Commands

```bash
# Render a single poster
python cli.py --location "New York" --theme 37th_parallel --size 16x20

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

## Rendering

- All maps render from OpenStreetMap data at 300 DPI via matplotlib
- 5 poster sizes: 8x10, 11x14, 16x20, 18x24, 24x36
- Primary theme: `37th_parallel` (black roads on white, blue water, green parks)
- fig_scale ensures consistent linewidths across all sizes (reference: 16x20 diagonal)
- zoom_scale adapts road widths for different map distances
- **Ocean rendering** requires land polygon data in `data/` — downloaded from osmdata.openstreetmap.de
- **Layouts:** `default` (3 text lines below map) or `date_night` (names above heart, 3 lines below)
- **Crop shapes:** full, circle, heart, house
- **5 font presets:** Century Gothic (sans), High Tower Text (serif), Priestacy (script), Monotype Corsiva (cursive), Footlight MT Light (classic)
- **5 pin styles:** heart, heart-pin, classic, house, graduation cap

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

## Cities (55 total, 5 tiers)

**Tier 1 (10):** Chicago, New York, Washington DC, New Orleans, Nashville, Austin, Seattle, San Francisco, Portland, Denver
**Tier 2 (10):** Boston, Miami, Atlanta, Minneapolis, Pittsburgh, Savannah, Charleston, Asheville, Salt Lake City, Honolulu
**Tier 3 (5):** Richmond, Chattanooga, Boise, Raleigh, Charlotte
**Tier 4 — SEO Expansion (10):** London, Paris, Tokyo, Rome, Barcelona, Amsterdam, Lisbon, Philadelphia, San Diego, Baltimore
**Tier 5 — Expansion (20):** Los Angeles, Houston, San Antonio, Detroit, St. Louis, Cincinnati, Tampa, Milwaukee, Kansas City, Cleveland, Berlin, Dublin, Edinburgh, Prague, Vienna, Copenhagen, Istanbul, Sydney, Florence, Stockholm

## Mockup System

- **7 PSD templates** in `etsy/TUR2/Best/Flat/` — Main, Mockup4, ONCE, VV1, 2Frames, CLS-4, FramePSD
- **Render size mapping:** Most use 24x36, ONCE + VV1 use 18x24
- **Multi-frame mockups** use filler cities (Pittsburgh, New Orleans, Washington DC, Amsterdam)
- **Filler lookup** searches both `renders/` and `renders/Posted/`

## Important Constraints & Patterns

- **Etsy title must match exactly** in Gelato CSV/API — mismatches cause "Product not found"
- **Dropbox tokens are short-lived** (~4 hours) — shared links persist permanently
- **Digital variants** always show "not connected" in Gelato — this is expected
- **fig_scale** must be applied to all rendering for consistent linewidths
- **Large cities** (London, Tokyo, Paris) may need buildings disabled at wide extents to manage memory
- **Subprocess isolation** in batch_seo_render.py prevents matplotlib memory leaks (was consuming 15GB)
- **Ocean fill** requires land polygon data in `data/` — full-res preferred over simplified (avoids sawtooth coastlines)
- **Completed city renders** are moved to `etsy/renders/Posted/` after listing goes live

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
