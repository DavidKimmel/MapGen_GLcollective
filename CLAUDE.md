# GeoLine Collective — MapGen

Minimalist black-and-white city map art prints sold on Etsy. Digital downloads + physical prints/framed via Gelato print-on-demand.

## Project Structure

```
engine/           # Map rendering pipeline (OSM data -> poster PNGs)
  map_engine.py   # Core: fetches OSM data, builds geometries
  renderer.py     # Figure setup, DPI, fig_scale calculation
  roads.py        # Road rendering with zoom_scale + fig_scale
  ocean.py        # Water/ocean fill
  text_layout.py  # City name + subtitle text placement
  crop_masks.py   # Edge cropping
  pin_renderer.py # Location pin overlay

etsy/             # Etsy listing & fulfillment pipeline
  city_list.py    # 25 cities (3 tiers) with CityListing dataclass
  listing_generator.py  # SEO titles, descriptions, tags, pricing
  batch_etsy_render.py  # Batch render all sizes for a city
  generate_gelato_csvs.py  # Dropbox API -> Gelato import CSVs
  image_composer.py     # Size comparison + detail crop images
  cloudinary_upload.py  # Upload listing photos to Cloudinary
  publish_batch.py      # Batch listing publisher
  auth.py               # Etsy OAuth2 PKCE flow
  dynamic_mockups.py    # Dynamic Mockups API integration
  mockup_psd.py         # PSD mockup generation

etsy/renders/{city_slug}/  # Per-city output directory
  gelato_import.csv        # Gelato product mapping CSV
  {city}_listing.txt       # Listing cheat sheet (title, desc, tags)
  {city}_variations.txt    # Variant/pricing reference

export/           # Gelato print-ready export
```

## Rendering

- All maps render from OpenStreetMap data at 300 DPI
- 5 poster sizes: 8x10, 11x14, 16x20, 18x24, 24x36
- Primary theme: `37th_parallel` (black roads on white background)
- fig_scale ensures consistent linewidths across all sizes (reference: 16x20)
- File naming: `{city_slug}_{size}.png` (default theme), `{city_slug}_{theme}_{size}.png` (other themes)

## Etsy & Fulfillment

- **Etsy shop:** GeoLine Collective (GeoLineCollective)
- **Physical prints:** Gelato print-on-demand, connected via CSV import
- **Digital delivery:** Message buyers with Dropbox download link
- **Dropbox path:** `C:/Users/kimme/Dropbox/GeoLine/{city_slug}/`
- **Shared links** use `?dl=1` suffix for direct download

### Gelato Product UIDs
- Unframed: `flat_{size}-inch-{mm}-mm_170-gsm-65lb-uncoated_4-0_ver`
- Framed black: `framed_poster_mounted_premium_{mm}-{size}_black_wood_w20xt20-mm_plexiglass_{mm}-{size}_200-gsm-80lb-uncoated_4-0_ver`
- Framed white: same pattern with `_white_wood_`

### Listing Workflow (manual, until Etsy API approved)
1. Copy an existing listing in Etsy Listings Manager
2. Update title, description, photos, digital file from `_listing.txt`
3. Generate Gelato CSV: `python -m etsy.generate_gelato_csvs --token TOKEN --city SLUG --listing-id ID --title "exact title"`
4. Upload CSV to Gelato to connect variants
5. Publish

### Pricing
| Size  | Digital | Unframed | Framed (B/W) |
|-------|---------|----------|--------------|
| 8x10  | $4.99   | $32.00   | $75.00       |
| 11x14 | $5.99   | $39.00   | $89.00       |
| 16x20 | $7.99   | $44.00   | $115.00      |
| 18x24 | $8.99   | $49.00   | $129.00      |
| 24x36 | $9.99   | $59.00   | $209.00      |

20 variants per listing: 5 digital + 5 unframed + 5 framed black + 5 framed white

## Cities (25 total)

**Tier 1 (live):** Chicago, New York, Washington DC, New Orleans, Nashville, Austin, Seattle, San Francisco, Portland, Denver
**Tier 2:** Boston, Miami, Atlanta, Minneapolis, Pittsburgh, Savannah, Charleston, Asheville, Salt Lake City, Honolulu
**Tier 3:** Richmond, Chattanooga, Boise, Raleigh, Charlotte

## Strategy

- Pre-made city listings = SEO entry points driving shop traffic
- Custom "any location" listings = primary revenue driver
- Business plan: `GeoLine_Task5_FinalReport.docx.md`

## Development

- Python 3.13, virtual environment at `.venv`
- Platform: Windows 11 (use Unix shell syntax in bash)
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`
- Never commit/push unless explicitly asked
