# GeoLine Collective — Growth Plan: 96 → 500+ Listings

## Executive Summary

We have 96 listings and 4 renderers. Top competitors have 300-1,000+. The path to 500+ is not about creating 400 new map designs by hand — it's about **systematically multiplying what we already have** through style × city × occasion × format combinations, each as its own SEO-searchable listing.

---

## Where We Stand Today

| Asset | Count | Status |
|-------|-------|--------|
| Renderers | 4 (Classic, Florence, Blueprint, MonoMap) | Production-ready |
| Crop masks | 4 (full, circle, heart, house) | Classic only |
| Cities configured | 64 | 55 published in Classic |
| Themes | 25 JSON files | 4 active, 19 unused |
| Font presets | 6 + 2 specialty | Production-ready |
| Pin styles | 5 | Classic only |
| Active Etsy listings | 96 | 55 Classic cities + 39 Florence + 2 custom |
| Mockup templates | 7 flat + 3 lifestyle | Automated |

**Key gap:** Competitors have 3-14x our listing count. Each listing is a separate search entry point.

---

## Competitive Landscape

| Shop | Listings | Sales | Stars | Primary Style | Framed? | Shapes | Prices (digital) |
|------|----------|-------|-------|--------------|---------|--------|-------------------|
| **37thParallelDesigns** | **1,338** | 12,804 | 4.9 | Minimalist B&W, 5 design variants | No | Full + Circle + House | $3.16-$14.48 |
| **AtlasMapDesign** | **592** | 2,241 | 5.0 | Colorful mosaic (Florence-like) | No | Full only | $9.00-$14.52 |
| **MapaholicCo** | **1,029** | 1,148 | 4.8 | Minimalist B&W (single style) | No — digital only | Full only | $4.50 flat (24 files per purchase) |
| **GeoLine Collective** | **96** | New | New | 4 styles (Classic, Florence, Blueprint, MonoMap) | **Yes** | Full + Circle + Heart + House | $4.20-$13.99 |

### What competitors do that we don't (yet):
- **Star Maps** (night sky on a date) — 37th has 16 listings, proven seller
- **Set of 3 bundles** — Atlas and 37th offer multi-city gallery wall packs
- **22 size options** — Atlas offers EU/ISO sizes + square formats
- **24 files per purchase** — MapaholicCo delivers every common size in one $4.50 download
- **Rush delivery** — 37th charges $14.48 for 24hr digital turnaround
- **Perpetual sale pricing** — Atlas and 37th run permanent 25% off
- **Video on listings** — Atlas and 37th have listing videos (huge algorithm boost)
- **Notebooks/journals** — Atlas has 7 map-themed stationery listings
- **1,000+ pre-made cities** — 37th (1,338) and MapaholicCo (1,029) have massive catalogs
- **Country & state outline maps** — MapaholicCo has 28 countries + 50 US states
- **Landscape/horizontal format** — Atlas offers separate landscape listings

### What we have that NO competitor offers:
- **Framed prints** (black + white frame via Gelato) — neither competitor offers framing
- **4 distinct visual styles** — competitors have 1-2 max
- **Heart crop shape** — unique to us
- **Blueprint shaded mosaic** — no competitor has this aesthetic
- **MonoMap 6-color choice** — unique product concept
- **Automated Gelato POD** — competitors use manual print partners
- **Full automation pipeline** — render → mockup → list → fulfill in one workflow

### Key strategic insight:
37thParallelDesigns has **14x our listings** but only **1-2 styles**. They scale through city count. AtlasMapDesign has **6x our listings** with one primary style. **We scale through style × city multiplication** — 4 styles across the same cities gives us 4x the SEO surface per city added.

---

## The Multiplication Strategy

### Current Capacity (what we CAN produce today)

```
4 styles × 64 cities × 5 sizes × 3 formats (digital/unframed/framed) = 3,840 possible SKUs
```

But we don't need one listing per SKU. The optimal Etsy strategy is **one listing per city × style** (sizes and formats as variants within):

```
4 styles × 64 cities = 256 city listings
+ 4 styles × 2 custom listings (digital + print) = 8 custom listings
+ Occasion-specific listings = 30-50 listings
+ Bundle/gallery wall listings = 20-30 listings
= 314-344 listings from existing capability
```

To hit 500+, we add:
- 50 more cities (international expansion)
- Occasion-specific listings (graduation, wedding, baby, etc.)
- New product concepts (dual city, neighborhood zoom, gallery sets)

---

## Phase 1: Style Expansion (Current 96 → 220 listings)
**Timeline: 1-2 weeks | Fully automatable**

### 1A. Blueprint City Listings (64 cities × 1 listing each = 64 new)

We have the renderer. We have the cities. We just need to run the pipeline.

```bash
# For each city: render 5 sizes × 4 colors, compose v3c layout, generate mockups
# Script needed: batch_blueprint_production.py (adapts batch_seo_render.py pattern)
```

**Listing strategy:** One listing per city (NOT per color). Colors as personalization choice. This matches how MonoMap custom works — customer picks city + color.

Wait — actually, for pre-made city maps we should do **one listing per city** with all 4 colors as downloadable or printable. But for SEO, splitting by color gives us 4x the listings:

**Option A (fewer listings, more variants):** 64 cities × 1 listing = 64 listings
**Option B (maximum SEO surface):** 64 cities × 4 colors = 256 listings

**Recommendation:** Option A for now (64 listings). Each listing shows all 4 colors in mockups. This keeps the shop manageable and customers can specify color in personalization.

### 1B. MonoMap City Listings (top 30 cities × 1 listing = 30 new)

Same approach — render top 30 cities in all 6 colors, one listing per city.

### 1C. Nordic City Listings (top 20 cities = 20 new)

Nordic renderer exists but isn't mass-produced. Render 20 cities.

### Phase 1 total: 96 + 64 + 30 + 20 = **~210 listings**

### Automation plan:
```python
# New script: scripts/batch_production_all_styles.py
# For each style:
#   1. Render all sizes (subprocess isolation for memory)
#   2. Generate listing text (SEO-optimized per style)
#   3. Generate mockups (7 flat + 3 lifestyle for print)
#   4. Upload to Dropbox
#   5. Create Etsy draft via API
#   6. Upload images via API
#   7. Set variants + pricing via API
#   8. Generate Gelato CSV
```

---

## Phase 2: Occasion-Based Listings (220 → 320 listings)
**Timeline: 2-3 weeks | Mostly automatable**

The market research is clear: **occasion-driven searches dominate**. Same map, different listing angle.

### 2A. "Where We Met" Custom Map (2 listings: digital + print)
- Heart pin at a specific location
- "Where It All Began" / "Where We Met" title options
- Valentine's, Anniversary, Wedding gift positioning
- **Already buildable** with our Standard renderer + heart pin + custom text

### 2B. Graduation Gift Maps (top 50 college towns = 50 listings)
- Graduation cap pin (style 5, already exists!)
- "Class of 2026" text overlay
- Target: April-June seasonal spike
- Cities: Add college towns (Ann Arbor, Chapel Hill, Tuscaloosa, Boulder, etc.)

### 2C. Baby Birth City Map (1 custom listing + 20 pre-made = 21 listings)
- Soft pastel themes (already have `warm_beige`, `watercolor` themes unused)
- "Born in [City]" or nursery-style text
- Heart pin at hospital location for custom
- **Existing capability** — just new theme + listing angle

### 2D. "Our First Home" House Maps (top 20 cities = 20 listings)
- House crop (already built!)
- Font preset 6 (already built!)
- Chimney year text
- Pre-made for top cities + custom listing

### 2E. Anniversary Maps (2 custom listings: digital + print)
- "X Years Together" text
- Heart pin
- Classic or midnight_blue theme
- Same renderer, different listing angle

### 2F. Wedding/Engagement Maps (2 custom listings)
- "Where He Proposed" / "Where She Said Yes"
- Heart pin, elegant fonts (preset 3 or 4)
- Script font title

### Phase 2 total: 210 + ~100 = **~320 listings**

---

## Phase 3: Format & Presentation Expansion (320 → 420 listings)
**Timeline: 3-4 weeks | Partially automatable**

### 3A. Gallery Wall Sets (20-30 bundle listings)
- "Set of 3 City Maps" — popular gallery wall concept
- Curated city combos: NYC/Paris/London, Nashville/Austin/Denver, etc.
- Same renders, new composite mockup showing 3 frames together
- Higher AOV ($25-40 digital, $120-200 physical set)

### 3B. Canvas Prints via Gelato (add canvas format to top 30 cities)
- Gelato supports canvas — just new product UIDs
- Premium positioning ($60-150)
- 30 cities × 1-2 styles = 30-60 new listings

### 3C. Circle Crop City Maps (top 20 cities = 20 listings)
- Circle crop already works with Standard renderer
- Clean modern aesthetic, popular on Pinterest
- Easy to produce — just `--crop circle` flag

### 3D. Dual City "Then & Now" Maps (10 combo listings)
- Side-by-side: hometown + current city
- "Where I'm From / Where I Am" concept
- Composite image from two existing renders
- Underserved niche per market research

### Phase 3 total: 320 + ~80 = **~420 listings**

---

## Phase 4: City Expansion (420 → 500+ listings)
**Timeline: 4-6 weeks | Fully automatable**

### 4A. International Cities (50 new cities)
Target underserved markets:
- **UK:** Manchester, Birmingham, Liverpool, Glasgow, Bristol
- **Europe:** Zurich, Oslo, Helsinki, Athens, Warsaw, Krakow, Porto, Seville
- **Asia-Pacific:** Melbourne, Auckland, Singapore, Bangkok, Seoul, Osaka
- **Americas:** Vancouver, Montreal, Buenos Aires, Lima, Bogota
- **Middle East:** Dubai, Tel Aviv

### 4B. US Cities Tier 7 (30 new cities)
Fill gaps in US market:
- College towns: Ann Arbor, Chapel Hill, Madison, Gainesville, Tuscaloosa
- Growing cities: Scottsdale, Bozeman, Greenville SC, Spokane, Lexington
- Tourist cities: Key West, Napa, Santa Fe, Sedona, Bar Harbor

### Phase 4 total: 420 + 80 = **500+ listings**

---

## Phase 5: New Product Lines (500 → 700+ listings)
**Timeline: 6-10 weeks | Mix of new development + automation**

### 5A. Star Maps / Night Sky Prints (20+ listings)
37thParallelDesigns has 16 star map listings generating solid sales. "The Night We Met" / "The Night You Were Born" are proven sellers.
- **New development needed:** Star chart renderer (stellarium data or astronomy library)
- **Automation:** Same listing pipeline once renderer exists
- **Listing angle:** Wedding date, birth date, anniversary, proposal night
- **Est. listings:** 2 custom + 10 popular dates/occasions + 8 pre-made

### 5B. Rush Delivery Premium (0 new listings, higher revenue)
37th charges $14.48 for 24hr delivery vs $9.05 standard. We can add rush variants to existing custom listings.
- **No new development** — just add a rush variant tier to custom listings
- **Price:** $14.99 rush vs $9.99 standard digital

### 5C. Square Format Maps (30 listings)
AtlasMapDesign offers 7 square sizes (12x12 through 28x28). Square maps look great on Instagram and in modern interiors.
- **Development:** Add square size configs to output_sizes.py
- **Listings:** Top 30 cities in Classic style, square format

### 5D. Landscape/Horizontal Maps (30 listings)
AtlasMapDesign has separate landscape listings. Coastal cities look great in horizontal.
- **Development:** Flip aspect ratio in renderer
- **Cities:** Coastal/waterfront cities (Miami, San Francisco, Sydney, Barcelona)

### 5E. Gallery Wall Curated Sets (20 listings)
Both competitors sell "Set of 3" bundles. Higher AOV.
- **Combos:** NYC/Paris/London, Nashville/Austin/Denver, etc.
- **Pricing:** $25-40 digital bundle, $150-250 physical set
- **Mockup:** Custom 3-frame gallery wall composite image

### 5F. Map Notebooks/Journals via Gelato (10 listings)
AtlasMapDesign has 7 notebook listings. Gelato offers notebook/journal products.
- **Development:** Adapt map renders to notebook cover dimensions
- **Listings:** Top 10 cities, colorful Florence style

### Phase 5 total: 500 + 130 = **630+ listings**

---

## Automation Architecture

### What exists today:
```
cli.py → render single poster (any style/theme/crop/pin/font)
batch_seo_render.py → render all 5 sizes for Classic cities (subprocess isolated)
batch_florence_production.py → render Florence cities (master crop)
mockup_composer.py → 7 flat + 3 lifestyle PSD mockups
listing_generator.py → SEO listing text generation
api_client.py → Etsy API (create draft, upload images, set variants)
gelato_connect.py → Gelato variant connection
batch_dropbox_upload.py → Dropbox upload
```

### What we need to build:

**1. Universal batch pipeline** (`scripts/batch_universal.py`)
```python
# Input: city_name, style, options
# Output: complete listing-ready folder
# Steps:
#   1. Render all 5 sizes (dispatch to correct renderer)
#   2. Generate detail crop
#   3. Generate mockups (flat + lifestyle for print)
#   4. Generate listing text (SEO-optimized per style + occasion)
#   5. Upload to Dropbox
#   6. Create Etsy draft via API
#   7. Upload images
#   8. Set variants + pricing
#   9. Generate Gelato CSV
#   10. Log to progress tracker
```

**2. Occasion-based listing generator** (`etsy/occasion_listing.py`)
- Templates for each occasion (graduation, wedding, baby, etc.)
- SEO-optimized titles and tags per occasion
- Auto-generates description with occasion-specific copy

**3. Gallery wall compositor** (`scripts/create_gallery_sets.py`)
- Takes 3 city renders, composites into gallery wall mockup
- Generates bundle listing text

**4. Dual city compositor** (`scripts/create_dual_city.py`)
- Takes 2 city renders, composites side-by-side
- "Then & Now" / "Hometown + Current City" listings

**5. Progress dashboard** (`scripts/listing_tracker.py`)
- Track which cities × styles × formats are listed
- Identify gaps automatically
- Queue next batch of listings to create

### Full automation flow (per listing):
```
[City + Style + Occasion config]
  → batch_universal.py (render + mockups + listing text)
  → batch_dropbox_upload.py (upload files)
  → api_client.py (create Etsy draft + upload images + set variants)
  → generate_gelato_csvs.py (Gelato CSV)
  → gelato_connect.py (connect variants after Gelato sync)
```

**Estimated time per listing (fully automated):**
- Render 5 sizes: ~10-20 min (CPU-bound, subprocess isolated)
- Mockups: ~2 min
- Dropbox upload: ~3 min
- Etsy API (create + upload 10 images + set variants): ~2 min
- Total: **~20-30 min per listing, fully unattended**

**At 20 min/listing, 500 listings = ~170 hours of compute**
**Running 24/7: ~7 days. Running 8 hrs/day: ~3 weeks.**

---

## Priority Execution Order

| Priority | Action | New Listings | Effort | Automation |
|----------|--------|-------------|--------|------------|
| 1 | Finish CustomMapPack (8 listings) | 7 more | Low | Scripts exist |
| 2 | Blueprint pre-made cities (top 30) | 30 | Medium | Need batch pipeline |
| 3 | MonoMap pre-made cities (top 30) | 30 | Medium | Need batch pipeline |
| 4 | Graduation cap college towns | 30 | Medium | Existing renderer + new cities |
| 5 | Circle crop cities (top 20) | 20 | Low | Just `--crop circle` |
| 6 | Gallery wall bundles | 20 | Medium | Need compositor |
| 7 | "Where We Met" occasion listings | 5 | Low | Existing renderer |
| 8 | Baby/nursery pastel maps | 20 | Medium | Need pastel theme |
| 9 | Nordic pre-made cities (top 20) | 20 | Low | Renderer exists |
| 10 | International city expansion | 50 | Medium | Just new city configs |
| 11 | Dual city combos | 10 | Medium | Need compositor |
| 12 | Canvas format (top 30 cities) | 30 | Low | Gelato config only |
| **Total** | | **~280 new** | | **96 + 280 = 376** |

Plus the existing 96 = **376 listings**, and with college towns + more international = 500+.

---

## SEO & Listing Optimization (Apply to ALL listings)

### Title Formula
```
[City Name] [Style] Map [Format], [Occasion/Gift Keyword], [Descriptor], [Gift Target]
```
Example: "Nashville Blueprint Map Print, Housewarming Gift, Detailed Mosaic Wall Art, New Home Gift"

### Tag Strategy (13 tags per listing)
- 3 city-specific: `nashville map`, `nashville wall art`, `nashville poster`
- 3 style-specific: `blueprint map art`, `mosaic city print`, `detailed street map`
- 3 occasion-specific: `housewarming gift`, `new home gift`, `closing gift`
- 2 format-specific: `framed map print`, `custom city map`
- 2 broad: `map wall art`, `city poster`

### Image Strategy (all 10 slots)
1. Hero (primary thumbnail — optimized for mobile)
2. Color options / style reference
3. Lifestyle mockup (room scene)
4. Lifestyle mockup (different room)
5. Flat mockup (main)
6. Multi-frame mockup (gallery wall feel)
7. Detail crop (shows quality)
8. Size comparison
9. Additional mockup
10. Personalization instructions / how-to-order

### Missing: VIDEO
- Etsy algorithm heavily favors listings with video
- Create 15-30 second clips showing map detail, room placement
- Can be automated with ffmpeg (pan/zoom over renders + fade transitions)
- **High priority — significant ranking boost**

---

## Investment Summary

| Item | Cost | One-time / Ongoing |
|------|------|--------------------|
| Etsy listing fees ($0.20 per listing) | $100 for 500 listings | One-time + $0.20/renewal every 4 months |
| Gelato | $0 until orders placed | Per-order |
| Compute time (rendering) | Electricity only | One-time per listing |
| Dropbox storage | Current plan sufficient | Ongoing |
| Additional fonts (if needed) | $0-50 | One-time |
| Video creation (if outsourced) | $0 if automated with ffmpeg | One-time |

**Total investment to reach 500 listings: ~$100 in Etsy fees + compute time.**

---

## Competitive Moat

What makes this scalable in a way competitors can't easily match:

1. **4 distinct visual styles** — most competitors have 1-2
2. **Fully automated pipeline** — render → mockup → upload → list → connect Gelato in one command
3. **Any city worldwide** — OSM data covers the entire planet
4. **Custom orders at scale** — personalization built into the workflow
5. **Gelato POD integration** — no inventory, global fulfillment
6. **Claude Code as operations AI** — can manage 500+ listings, create new ones, respond to trends

The goal isn't to manually curate 500 maps. The goal is to build the machine that produces them.
