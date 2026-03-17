# MapGen Code Review — 2026-03-17

## What This Project Does

MapGen generates print-quality city map posters from OpenStreetMap data. It powers the GeoLine Collective Etsy shop — selling digital downloads and physical prints (via Gelato print-on-demand) of minimalist city maps.

**Two product lines:**
1. **Pre-made city maps** — 35 cities, 5 sizes each, auto-fulfilled via Gelato
2. **Custom maps** — any location, made-to-order with personalized text/pins/themes

---

## How It Works (Simple Version)

```
Customer orders on Etsy
    ↓
Map renders from OpenStreetMap data (roads, water, parks, buildings)
    ↓
Saved as high-res PNG (300 DPI, up to 24x36 inches)
    ↓
Uploaded to Dropbox → linked to Gelato → printed & shipped
```

For custom orders, an extra step: we render on-demand with the customer's location/text/style choices.

---

## Folder Structure (Current)

```
Mapgen_GLcollective/
├── engine/              Core rendering (7 files, ~2400 lines)
├── etsy/                Business pipeline (15+ files, ~4500 lines)
├── api/                 Flask backend (3 files)
├── frontend/            React UI (15 components)
├── export/              Size definitions + Gelato export
├── utils/               Caching, geocoding, logging
├── themes/              23 color theme JSON files
├── fonts/               25 font files (6 MB)
├── templates/           PSD template generator + output
├── data/                Land polygon shapefiles (2.2 GB)
├── posters/             Test render output
├── cache/               OSM data cache (currently empty)
├── cli.py               Command-line poster generator
├── app.py               Flask app entry point
├── batch_seo_render.py  Batch city renderer
├── batch_dropbox_upload.py  Upload to Dropbox
├── generate_samples.py  Sample render generator
└── CLAUDE.md            Project documentation
```

---

## The Rendering Engine (engine/)

| File | What It Does |
|------|-------------|
| renderer.py | Main orchestrator — calls everything else in order |
| map_engine.py | Downloads 14 OSM data layers (roads, water, parks, buildings, etc.) |
| roads.py | Draws roads with proper widths by type (highway > residential > path) |
| ocean.py | Fills ocean areas by subtracting land polygons from the viewport |
| text_layout.py | Places city name + subtitle + coordinates below the map |
| crop_masks.py | Applies circle, heart, or house shape masks |
| pin_renderer.py | Draws location markers (5 styles: heart, pin, house, grad cap) |

**Key concept: fig_scale** — ensures road widths look identical whether you're printing 8x10 or 24x36.

---

## The Etsy Pipeline (etsy/)

| File | What It Does |
|------|-------------|
| city_list.py | Master list of 35 cities with coordinates, distances, tiers |
| listing_generator.py | Creates SEO titles, descriptions, tags, pricing for listings |
| batch_etsy_render.py | Renders all 5 sizes for a city at 300 DPI |
| image_composer.py | Creates "detail crop" and "size comparison" listing photos |
| mockup_composer.py | Places renders into PSD mockup frames |
| generate_gelato_csvs.py | Creates CSV with Dropbox links for Gelato import |
| gelato_connect.py | Connects Etsy variants to Gelato products via API (3-step) |
| custom_fulfill.py | End-to-end custom order: render → Dropbox → Gelato |
| custom_listing.py | Generates the "any location" custom map listing content |
| auth.py | Etsy OAuth2 login flow |
| api_client.py | Etsy API wrapper for creating/updating listings |
| publish_batch.py | Orchestrates full listing publication pipeline |
| cloudinary_upload.py | Uploads posters to Cloudinary CDN (for Dynamic Mockups) |
| dynamic_mockups.py | Generates mockups via Dynamic Mockups API |
| mockup_psd.py | Legacy PSD mockup compositor |

---

## Issues Found

### 1. Duplicate/Overlapping Mockup Files (HIGH)

There are **4 separate mockup-related files** in etsy/:

| File | Status | Notes |
|------|--------|-------|
| mockup_composer.py | **ACTIVE** — the one we use | Finds fillers from Posted/, uses TUR2/Best/Flat PSDs |
| mockup_psd.py | Legacy | Uses TUR2/PSD Mockups, different approach |
| mockup_generator.py | Unclear | May be deprecated |
| mockup_compositor.py | Unclear | May be deprecated |

**Recommendation:** Keep `mockup_composer.py`, review the other 3 and delete if unused.

### 2. Root-Level Script Clutter (MEDIUM)

These files at the project root should be organized:

| File | Recommendation |
|------|---------------|
| test_dc.py (321 lines) | Delete — old test code |
| test_residential.py (369 lines) | Delete — old test code |
| batch_render.py | Delete if `batch_seo_render.py` replaced it |
| sample_sheet.py | Move to etsy/ or delete if unused |
| generate_samples.py | Move to etsy/ |

### 3. Untracked/Orphaned Files (MEDIUM)

| Item | Action |
|------|--------|
| .claude/worktrees/amazing-faraday/ | Delete — orphaned git worktree |
| env (root) | Delete — stale .env backup with old keys |
| etsy/mockup_composer.py | Commit — actively used but untracked |
| etsy/style_sheet.png | Add to .gitignore — generated asset |
| etsy/mockup_templates/ | Delete if replaced by templates/psd/ |

### 4. Unused Fonts (LOW)

25 fonts installed but only 7 are actively used:
- CenturyGothic-Bold, HighTowerText (Regular + Italic), Priestacy, LucidaCalligraphy-Italic, MonotypeCorsiva, FootlightMTLight, Garamond-Bold

Others (Roboto, Montserrat, PlayfairDisplay, CormorantGaramond, etc.) may be from earlier iterations. Could clean up if not needed.

### 5. Themes Directory (LOW)

23 themes exist but only 4 are actively used for custom listings:
- 37th_parallel, midnight_blue, clay_sage, gradient_roads

The other 19 still work and could be used by the frontend, but aren't part of any Etsy listing.

### 6. Storage (INFO)

| Item | Size | Notes |
|------|------|-------|
| data/ (land polygons) | 2.2 GB | Needed for ocean rendering, correctly gitignored |
| data/*.zip | 939 MB | Can delete after extraction |
| etsy/TUR2/ | 17 MB | Mockup PSDs, correctly gitignored |
| posters/ | 145 MB | Test renders, could clean periodically |

---

## Suggested Folder Restructure

### Option A: Minimal cleanup (recommended)

Just fix the obvious issues without moving core files:

1. Delete: `test_dc.py`, `test_residential.py`, `env`, `.claude/worktrees/`
2. Delete if unused: `batch_render.py`, `etsy/mockup_psd.py`, `etsy/mockup_generator.py`, `etsy/mockup_compositor.py`, `etsy/mockup_templates/`
3. Commit: `etsy/mockup_composer.py`
4. Move to etsy/: `generate_samples.py`, `sample_sheet.py`
5. Add to .gitignore: `env`, `etsy/style_sheet.png`
6. Delete zip: `data/land-polygons-complete-3857.zip` (already extracted)

### Option B: Full reorganization

Move batch scripts into a `scripts/` directory:

```
scripts/
├── batch_seo_render.py
├── batch_dropbox_upload.py
├── generate_samples.py
└── sample_sheet.py
```

This keeps the root clean but requires updating imports. More disruptive.

---

## Code Quality Summary

| Area | Grade | Notes |
|------|-------|-------|
| Engine (rendering) | A | Clean, modular, well-separated concerns |
| Etsy pipeline | B+ | Works well, just needs mockup consolidation |
| API/Frontend | B | Functional, less actively developed |
| Error handling | A | Proper try/catch, retries, rate limiting |
| Caching | A | Two-tier (memory + disk), rounded keys |
| Documentation | B | CLAUDE.md is good but needs update |
| File organization | C+ | Root clutter, duplicate mockup files |
| Git hygiene | B- | Untracked active files, orphaned worktree |

---

## What CLAUDE.md Needs Updated

1. Project structure section is outdated (missing Tier 4 cities, new scripts)
2. Should document the `renders/Posted/` pattern
3. Should list all active scripts with their purpose
4. Mockup composer workflow not documented
5. Land polygon data requirement not mentioned
6. Session handoff workflow should be referenced
7. Current city count (35, not 25)

---

## Next Steps (Your Call)

1. **Review this document** — tell me what you agree/disagree with
2. **Approve cleanups** — I'll delete/move files per your approval
3. **Update CLAUDE.md** — rewrite with full current state
4. **Commit everything** — clean commit with all changes
