# Custom Map Section Expansion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand GeoLine Collective's Etsy custom map section from 4 listings to 9+ by creating 5 new occasion/style-specific custom map listings using existing renderers and a new listing text generator module.

**Architecture:** One new Python module (`etsy/custom_listings.py`) generates listing text for all 5 new custom listings via a shared framework. Each listing gets sample renders (via CLI), mockups (via `mockup_composer.py`), and a detail crop (via `image_composer.py`). Listing text files are saved to `etsy/renders/CustomExpansion/{listing_slug}/`. No new renderers needed — all 5 listings use existing Classic, Blueprint, or MonoMap renderers with existing crops, pins, and themes.

**Tech Stack:** Python 3.13, existing engine/ renderers, etsy/mockup_composer.py, etsy/image_composer.py, Pillow, matplotlib

---

## Competitive Context

Research on 2026-03-31 of top 20 Etsy "custom map print" results revealed:

| Strategy | Top Practitioners | Relevance |
|----------|-------------------|-----------|
| **Niche multiplication** (separate listing per occasion) | 37thParallelDesigns (2.1k reviews) | Our primary strategy — 5 new angles |
| **Heart-shaped "Where We Met"** | WordsWorkPrints (13.4k reviews, $23) | We have heart crop — listing 1 |
| **Graduation map with cap pin** | Multiple sellers, medium saturation | We have grad cap pin — listing 2 |
| **Multi-style/color options** | AtlasMapDesign, ArtsifOfficial | We have 23 themes — listing 3 |
| **Baby birth/nursery maps** | LEAST saturated category | Soft themes available — listing 4 |
| **Blueprint/architectural custom** | NO competitor has this | Our unique moat — listing 5 |
| **"Always on sale" pricing** | PaperEmporiumCo, ArtsifOfficial, InkxCanvas | 25% off strategy — all listings |

## File Structure

### New Files

| File | Purpose |
|------|---------|
| `etsy/custom_listings.py` | Listing text generator for all 5 new custom listings — titles, tags, descriptions, pricing, SKUs |
| `scripts/render_custom_expansion_samples.py` | Renders sample maps for all 5 listings (hero images + mockup source renders) |
| `scripts/create_custom_expansion_assets.py` | Generates mockups, detail crops, and hero images for all 5 listings |

### Modified Files

| File | Change |
|------|--------|
| `etsy/style_config.py` | Add `CUSTOM_EXPANSION_VARIANTS` pricing table with "always 25% off" sale pricing |

### Output Directories

```
etsy/renders/CustomExpansion/
├── where_we_met/          # Listing 1: heart crop romance map
│   ├── listing.txt
│   ├── hero_where_we_met.png
│   ├── detail_crop.jpg
│   ├── mockup_main.jpg ... mockup_vv1.jpg (7 mockups)
│   └── sample renders (multiple themes × sizes)
├── graduation_map/        # Listing 2: grad cap pin college map
│   ├── listing.txt, hero, detail_crop, 7 mockups, samples
├── multi_style_map/       # Listing 3: 6 theme options
│   ├── listing.txt, hero, detail_crop, 7 mockups, style_showcase.jpg
├── born_in_map/           # Listing 4: baby/nursery soft palette
│   ├── listing.txt, hero, detail_crop, 7 mockups, samples
└── custom_blueprint/      # Listing 5: blueprint mosaic custom
    ├── listing.txt, hero, detail_crop, 7 mockups, color_options.jpg
```

---

## Pricing Strategy

All 5 new custom listings use "always on sale" pricing — list at a higher "original" price, permanently run 25% off. This matches PaperEmporiumCo (34.9k reviews), AtlasMapDesign, and InkxCanvas strategies.

| Format | Original Price | Sale Price (25% off) | SKU Pattern |
|--------|---------------|---------------------|-------------|
| Digital 8x10 | $13.32 | $9.99 | GLC-{SLUG}-DIG-8X10 |
| Digital 11x14 | $13.32 | $9.99 | GLC-{SLUG}-DIG-11X14 |
| Digital 16x20 | $15.99 | $11.99 | GLC-{SLUG}-DIG-16X20 |
| Digital 18x24 | $15.99 | $11.99 | GLC-{SLUG}-DIG-18X24 |
| Digital 24x36 | $17.32 | $12.99 | GLC-{SLUG}-DIG-24X36 |
| Unframed 8x10 | $46.44 | $34.83 | GLC-{SLUG}-UNF-8X10 |
| Unframed 11x14 | $53.13 | $39.85 | GLC-{SLUG}-UNF-11X14 |
| Unframed 16x20 | $61.80 | $46.35 | GLC-{SLUG}-UNF-16X20 |
| Unframed 18x24 | $68.49 | $51.37 | GLC-{SLUG}-UNF-18X24 |
| Unframed 24x36 | $83.27 | $62.45 | GLC-{SLUG}-UNF-24X36 |
| Framed Black 8x10 | $104.09 | $78.07 | GLC-{SLUG}-FBK-8X10 |
| Framed Black 11x14 | $116.67 | $87.50 | GLC-{SLUG}-FBK-11X14 |
| Framed Black 16x20 | $159.49 | $119.62 | GLC-{SLUG}-FBK-16X20 |
| Framed Black 18x24 | $174.83 | $131.12 | GLC-{SLUG}-FBK-18X24 |
| Framed Black 24x36 | $288.23 | $216.17 | GLC-{SLUG}-FBK-24X36 |
| Framed White (same as Black) | ... | ... | GLC-{SLUG}-FWH-* |

Physical prices match existing CITY_MAP_VARIANTS (Gelato costs unchanged). Digital prices are bumped up from pre-made city levels to reflect custom/made-to-order value.

---

## The 5 Listings

### Listing 1: "Where We Met" Custom Map

| Field | Value |
|-------|-------|
| **Slug** | `where_we_met` |
| **SKU prefix** | `GLC-MEET` |
| **Renderer** | Classic (37th_parallel, midnight_blue, clay_sage, warm_beige — buyer picks) |
| **Crop** | Heart (default) or Circle (buyer's choice) |
| **Pin** | Heart pin at specified location |
| **Layout** | `date_night` (names above map, 3 lines below) |
| **Text line 1** | Couple's names (e.g., "Sarah & James") |
| **Text line 2** | "Where It All Began" or custom tagline |
| **Text line 3** | City, State |
| **Text line 4** | Date (e.g., "June 15, 2019") |
| **Target occasions** | Anniversary, Valentine's Day, engagement, wedding |
| **Tags** | where we met map, where it all began, anniversary map gift, couple map print, personalized map gift, custom heart map, romantic map art, engagement gift map, valentine map print, wedding location map, first date map, custom location print, love map print |
| **Sample cities** | Nashville (37th_parallel), Savannah (midnight_blue), Portland (clay_sage), Paris (warm_beige) |
| **Personalization prompt** | "Please provide: (1) Location where you met (city/address), (2) Names to display above map, (3) Date, (4) Style: Classic White, Midnight Blue, Clay & Sage, or Warm Beige, (5) Shape: Heart or Circle" |

### Listing 2: "Graduation Map" Custom Print

| Field | Value |
|-------|-------|
| **Slug** | `graduation_map` |
| **SKU prefix** | `GLC-GRAD` |
| **Renderer** | Classic (37th_parallel, midnight_blue, clay_sage) |
| **Crop** | Full (default) or Circle |
| **Pin** | Graduation cap (pin style 5) at campus location |
| **Layout** | `default` (3 lines below map) |
| **Text line 1** | University name (e.g., "UNIVERSITY OF TEXAS") |
| **Text line 2** | "Class of 2026" or degree/major |
| **Text line 3** | City, State |
| **Target occasions** | College graduation, high school graduation, PhD defense |
| **Tags** | graduation map print, college graduation gift, class of 2026 gift, university map art, campus city map, personalized grad gift, custom graduation art, college town map, senior gift map, school map print, graduation wall art, commencement gift, alma mater map |
| **Sample cities** | Austin (37th_parallel — UT), Nashville (midnight_blue — Vanderbilt), Portland (clay_sage — PSU) |
| **Personalization prompt** | "Please provide: (1) University/school name, (2) City where the school is located, (3) Graduation year or 'Class of' text, (4) Style: Classic White, Midnight Blue, or Clay & Sage, (5) Shape: Full or Circle" |

### Listing 3: "Custom Map — Choose Your Style" (Multi-Theme)

| Field | Value |
|-------|-------|
| **Slug** | `multi_style_map` |
| **SKU prefix** | `GLC-STYLE` |
| **Renderer** | Classic with 6 theme options |
| **Themes** | 37th_parallel (Classic B&W), midnight_blue (Navy & Gold), clay_sage (Clay & Sage), warm_beige (Warm Beige), watercolor (Watercolor), vintage (Vintage) |
| **Crop** | Full (default) or Circle |
| **Pin** | Any pin style (buyer's choice) or none |
| **Layout** | `default` (3 lines below map) |
| **Text** | City name + state/country + coordinates (default) or custom text |
| **Target occasions** | Housewarming, home decor, travel, any gift |
| **Tags** | custom city map print, personalized map art, choose your style map, custom color map, any city map poster, housewarming map gift, custom-map, personalized wall art, custom location print, city map wall art, map print art, modern map poster, travel map gift |
| **Sample cities** | Nashville in all 6 themes at 16x20 (showcases variety) |
| **Key image** | `style_showcase.jpg` — 6-panel grid showing same city in all 6 themes with labels |
| **Personalization prompt** | "Please provide: (1) Location (city/address/coordinates), (2) Style: Classic B&W, Midnight Blue, Clay & Sage, Warm Beige, Watercolor, or Vintage, (3) Custom text (optional — default is city name + coordinates), (4) Pin: None, Heart, Pin, House, or Grad Cap, (5) Shape: Full or Circle" |

### Listing 4: "Born In" Baby/Nursery Map

| Field | Value |
|-------|-------|
| **Slug** | `born_in_map` |
| **SKU prefix** | `GLC-BABY` |
| **Renderer** | Classic with soft themes only (warm_beige, clay_sage, watercolor) |
| **Crop** | Circle (default — clean nursery aesthetic) or Full |
| **Pin** | Heart pin at birth city |
| **Layout** | `default` (3 lines below map) |
| **Text line 1** | Baby's name (e.g., "EMMA GRACE") |
| **Text line 2** | "Born in [City]" or birth date |
| **Text line 3** | Birth date or birth details |
| **Target occasions** | Baby shower, newborn gift, nursery decor, first birthday |
| **Tags** | baby birth map, born in map print, nursery wall art, newborn gift map, baby shower gift, birth city map, personalized nursery, custom baby map, nursery decor art, baby keepsake gift, birth location map, baby room wall art, newborn keepsake |
| **Sample cities** | Nashville (warm_beige), Portland (clay_sage), Paris (watercolor) |
| **Personalization prompt** | "Please provide: (1) Birth city/location, (2) Baby's name, (3) Birth date and/or birth details (weight, time — optional), (4) Style: Warm Beige, Clay & Sage, or Watercolor, (5) Shape: Circle or Full" |

### Listing 5: "Custom Blueprint Mosaic Map"

| Field | Value |
|-------|-------|
| **Slug** | `custom_blueprint` |
| **SKU prefix** | `GLC-CBLU` |
| **Renderer** | Blueprint (4 colors: navy, forest, terracotta, charcoal) |
| **Crop** | Full only (Blueprint's top-header layout doesn't support circle crop) |
| **Layout** | Blueprint v3c (title top-right, swatch bar, map below) |
| **Text** | Auto-generated from city name (Blueprint's own text layout) |
| **Target occasions** | Housewarming, architecture lovers, modern decor |
| **Tags** | blueprint map print, mosaic city map, custom-map, architectural map art, shaded city poster, modern wall art, blueprint wall decor, city block map, detailed map print, custom mosaic map, choose your color map, housewarming gift, unique map art |
| **Sample cities** | Nashville (terracotta), Chicago (navy), Berlin (forest), Paris (charcoal) — reuse existing BlueprintV3 renders |
| **Key image** | Reuse `BlueprintV3/shared_psd4_labeled.jpg` for color showcase |
| **Personalization prompt** | "Please provide: (1) City name or location, (2) Color: Navy, Forest, Terracotta, or Charcoal" |

---

## Task Breakdown

### Task 1: Add Custom Expansion Pricing to style_config.py

**Files:**
- Modify: `etsy/style_config.py:148` (after CITY_MAP_VARIANTS)

- [ ] **Step 1: Add CUSTOM_EXPANSION_VARIANTS pricing table**

Add after the existing `CITY_MAP_VARIANTS` list (line ~148):

```python
# Custom expansion listings — "always 25% off" sale pricing
# Original prices are set so that 25% off = the sale price shown
CUSTOM_DIGITAL_PRICES: dict[str, float] = {
    "8x10": 13.32,    # sale: $9.99
    "11x14": 13.32,   # sale: $9.99
    "16x20": 15.99,   # sale: $11.99
    "18x24": 15.99,   # sale: $11.99
    "24x36": 17.32,   # sale: $12.99
}

CUSTOM_EXPANSION_VARIANTS: list[VariantPrice] = [
    # Digital (5) — original prices (Etsy sale set to 25% off)
    VariantPrice("8x10", "Digital Download", 13.32, "DIG-8X10"),
    VariantPrice("11x14", "Digital Download", 13.32, "DIG-11X14"),
    VariantPrice("16x20", "Digital Download", 15.99, "DIG-16X20"),
    VariantPrice("18x24", "Digital Download", 15.99, "DIG-18X24"),
    VariantPrice("24x36", "Digital Download", 17.32, "DIG-24X36"),
    # Unframed (5) — same as city maps (Gelato costs unchanged)
    VariantPrice("8x10", "Unframed Print", 34.83, "UNF-8X10"),
    VariantPrice("11x14", "Unframed Print", 39.85, "UNF-11X14"),
    VariantPrice("16x20", "Unframed Print", 46.35, "UNF-16X20"),
    VariantPrice("18x24", "Unframed Print", 51.37, "UNF-18X24"),
    VariantPrice("24x36", "Unframed Print", 62.45, "UNF-24X36"),
    # Framed Black (5)
    VariantPrice("8x10", "Framed - Black", 78.07, "FBK-8X10"),
    VariantPrice("11x14", "Framed - Black", 87.50, "FBK-11X14"),
    VariantPrice("16x20", "Framed - Black", 119.62, "FBK-16X20"),
    VariantPrice("18x24", "Framed - Black", 131.12, "FBK-18X24"),
    VariantPrice("24x36", "Framed - Black", 216.17, "FBK-24X36"),
    # Framed White (5)
    VariantPrice("8x10", "Framed - White", 78.07, "FWH-8X10"),
    VariantPrice("11x14", "Framed - White", 87.50, "FWH-11X14"),
    VariantPrice("16x20", "Framed - White", 119.62, "FWH-16X20"),
    VariantPrice("18x24", "Framed - White", 131.12, "FWH-18X24"),
    VariantPrice("24x36", "Framed - White", 216.17, "FWH-24X36"),
]
```

- [ ] **Step 2: Verify no syntax errors**

Run: `python -c "from etsy.style_config import CUSTOM_EXPANSION_VARIANTS; print(f'{len(CUSTOM_EXPANSION_VARIANTS)} variants loaded')"`
Expected: `20 variants loaded`

- [ ] **Step 3: Commit**

```bash
git add etsy/style_config.py
git commit -m "feat: add custom expansion variant pricing with sale strategy"
```

---

### Task 2: Create Custom Listings Text Generator Module

**Files:**
- Create: `etsy/custom_listings.py`

This is the core module. It contains the listing definitions (title, tags, description, personalization, pricing) for all 5 new custom listings and a function to generate the listing.txt file for each.

- [ ] **Step 1: Create `etsy/custom_listings.py` with listing definitions**

```python
"""Custom map expansion listings — text generator for 5 new Etsy listings.

Each listing targets a specific occasion/style niche with tailored SEO.
All use existing renderers (Classic, Blueprint) with existing crops/pins.

Usage:
    python -m etsy.custom_listings --all                # Generate all 5
    python -m etsy.custom_listings --listing where_we_met  # Generate one
    python -m etsy.custom_listings --preview where_we_met  # Print to stdout
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from etsy.style_config import CUSTOM_EXPANSION_VARIANTS, VariantPrice


# ---------------------------------------------------------------------------
# Listing dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CustomListing:
    """Definition for one custom map Etsy listing."""
    slug: str
    sku_prefix: str
    title: str
    tags: list[str]
    description: str
    personalization_prompt: str
    shop_section_id: int = 57768965  # Custom Maps section
    variants: list[VariantPrice] = field(default_factory=lambda: list(CUSTOM_EXPANSION_VARIANTS))


# ---------------------------------------------------------------------------
# Listing 1: Where We Met
# ---------------------------------------------------------------------------

WHERE_WE_MET = CustomListing(
    slug="where_we_met",
    sku_prefix="GLC-MEET",
    title=(
        "Where We Met Map Print | Custom Heart Map, Anniversary Gift "
        "| Personalized Couple Map | Valentine's Day"
    ),
    tags=[
        "where we met map",
        "where it all began",
        "anniversary map gift",
        "couple map print",
        "personalized map gift",
        "custom heart map",
        "romantic map art",
        "engagement gift map",
        "valentine map print",
        "wedding location map",
        "first date map",
        "custom location print",
        "love map print",
    ],
    description="""\
📍 The place where your story began — captured in a beautiful custom map.

Mark the exact spot where you first met, had your first date, or fell in \
love. This personalized heart-shaped map print makes the perfect romantic \
gift for anniversaries, Valentine's Day, engagements, or weddings.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🔸 HOW TO ORDER

1. Add this listing to your cart
2. In the "Personalization" box, tell us:
   → Location where you met (city, address, or coordinates)
   → Names to display above the map (e.g., "Sarah & James")
   → Date (e.g., "June 15, 2019")
   → Style preference (see below)
   → Shape: Heart or Circle
3. We'll design your map and send a proof within 1-2 business days
4. After your approval, we deliver the final file or ship your print

━━━━━━━━━━━━━━━━━━━━━━━━━━

🎨 CHOOSE YOUR STYLE

◈ Classic White — clean black roads on white, blue water, green parks
◈ Midnight Blue — golden roads on deep navy, luxury atlas aesthetic
◈ Clay & Sage — warm clay tones with sage green, cool slate water
◈ Warm Beige — earthy neutrals with sepia tones, vintage feel

━━━━━━━━━━━━━━━━━━━━━━━━━━

🖼️ WHAT YOU GET

◈ Digital Download — High-resolution 300 DPI PNG, ready to print anywhere
◈ Physical Print — Museum-quality poster on premium matte paper
◈ Framed Option — Black or white frame, shipped ready to hang

━━━━━━━━━━━━━━━━━━━━━━━━━━

📐 AVAILABLE SIZES

◈ 8×10 inches (20×25 cm) — desk or shelf
◈ 11×14 inches (28×36 cm) — gallery wall
◈ 16×20 inches (41×51 cm) — statement piece
◈ 18×24 inches (46×61 cm) — large format
◈ 24×36 inches (61×91 cm) — above the sofa

━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ ABOUT THIS DESIGN

Your names appear elegantly above the heart-shaped map, with a heart pin \
marking the exact location where your story began. Below the map: your \
custom tagline, city name, and date.

Every map is rendered from professional cartographic data — capturing \
every street, park, waterway, and building footprint at 300+ DPI. \
No two maps are alike because no two cities are alike.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🚚 SHIPPING & DELIVERY

◈ Digital: Proof within 1-2 business days, final file after approval
◈ Physical prints: 2-3 days design + 3-5 days production + shipping
◈ Framed prints: 5-7 business days + shipping
◈ Ships from the US via our premium print partner

━━━━━━━━━━━━━━━━━━━━━━━━━━

💛 PERFECT FOR

♥ Anniversary gifts — celebrate where it all began
♥ Valentine's Day — the most romantic map gift
♥ Engagement gifts — the spot where they said yes
♥ Wedding gifts — a keepsake of the couple's story
♥ First date memories — because you never forget that place

━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ Questions? Message us anytime — we love helping you create the perfect map.

© GeoLine Collective — Cartography as Craft""",
    personalization_prompt=(
        "Please provide:\n"
        "1. Location where you met (city, address, or coordinates)\n"
        "2. Names to display above the map (e.g., 'Sarah & James')\n"
        "3. Date (e.g., 'June 15, 2019')\n"
        "4. Style: Classic White, Midnight Blue, Clay & Sage, or Warm Beige\n"
        "5. Shape: Heart or Circle"
    ),
)


# ---------------------------------------------------------------------------
# Listing 2: Graduation Map
# ---------------------------------------------------------------------------

GRADUATION_MAP = CustomListing(
    slug="graduation_map",
    sku_prefix="GLC-GRAD",
    title=(
        "Graduation Map Print | Custom College Town Map, Class of 2026 Gift "
        "| Personalized University Map"
    ),
    tags=[
        "graduation map print",
        "college graduation gift",
        "class of 2026 gift",
        "university map art",
        "campus city map",
        "personalized grad gift",
        "custom graduation art",
        "college town map",
        "senior gift map",
        "school map print",
        "graduation wall art",
        "commencement gift",
        "alma mater map",
    ],
    description="""\
📍 Celebrate their achievement with a map of the city where they earned it.

A custom map of their college town with a graduation cap pin marking \
the campus — the perfect keepsake for any graduate. Personalized with \
the university name, graduation year, and city.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🔸 HOW TO ORDER

1. Add this listing to your cart
2. In the "Personalization" box, tell us:
   → University or school name
   → City where the school is located
   → Graduation year or "Class of" text
   → Style preference (see below)
   → Shape: Full or Circle
3. We'll design your map and send a proof within 1-2 business days
4. After your approval, we deliver the final file or ship your print

━━━━━━━━━━━━━━━━━━━━━━━━━━

🎨 CHOOSE YOUR STYLE

◈ Classic White — clean black roads on white, blue water, green parks
◈ Midnight Blue — golden roads on deep navy, premium look
◈ Clay & Sage — warm earth tones, sophisticated and timeless

━━━━━━━━━━━━━━━━━━━━━━━━━━

🖼️ WHAT YOU GET

◈ Digital Download — High-resolution 300 DPI PNG, ready to print anywhere
◈ Physical Print — Museum-quality poster on premium matte paper
◈ Framed Option — Black or white frame, shipped ready to hang

━━━━━━━━━━━━━━━━━━━━━━━━━━

📐 AVAILABLE SIZES

◈ 8×10 inches (20×25 cm) — desk or dorm room
◈ 11×14 inches (28×36 cm) — gallery wall
◈ 16×20 inches (41×51 cm) — statement piece
◈ 18×24 inches (46×61 cm) — large format
◈ 24×36 inches (61×91 cm) — living room centerpiece

━━━━━━━━━━━━━━━━━━━━━━━━━━

🎓 ABOUT THIS DESIGN

Each map features a graduation cap pin at the campus location, with the \
university name displayed prominently below the map alongside the \
graduation year and city. Every street, park, and waterway surrounding \
the campus is captured in stunning cartographic detail at 300+ DPI.

A meaningful gift that captures not just where they studied — but the \
entire city that became their home for those formative years.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🚚 SHIPPING & DELIVERY

◈ Digital: Proof within 1-2 business days, final file after approval
◈ Physical prints: 2-3 days design + 3-5 days production + shipping
◈ Framed prints: 5-7 business days + shipping
◈ Ships from the US via our premium print partner

━━━━━━━━━━━━━━━━━━━━━━━━━━

💛 PERFECT FOR

🎓 College graduation gifts
🎓 High school graduation
🎓 PhD / Master's degree celebrations
🎓 Alumni nostalgia gifts
🎓 Dorm room or first apartment decor

━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ Questions? Message us anytime — we love helping you create the perfect map.

© GeoLine Collective — Cartography as Craft""",
    personalization_prompt=(
        "Please provide:\n"
        "1. University or school name\n"
        "2. City where the school is located\n"
        "3. Graduation year or 'Class of' text\n"
        "4. Style: Classic White, Midnight Blue, or Clay & Sage\n"
        "5. Shape: Full or Circle"
    ),
)


# ---------------------------------------------------------------------------
# Listing 3: Multi-Style Custom Map
# ---------------------------------------------------------------------------

MULTI_STYLE_MAP = CustomListing(
    slug="multi_style_map",
    sku_prefix="GLC-STYLE",
    title=(
        "Custom City Map Print - Choose Your Style | 6 Color Options "
        "| Personalized Map Art | Any Location"
    ),
    tags=[
        "custom city map print",
        "personalized map art",
        "choose your style map",
        "custom color map",
        "any city map poster",
        "housewarming map gift",
        "custom-map",
        "personalized wall art",
        "custom location print",
        "city map wall art",
        "map print art",
        "modern map poster",
        "travel map gift",
    ],
    description="""\
📍 Your city, your style — choose from 6 unique color palettes.

The same stunning street map rendered in the color that matches YOUR \
decor. Pick from our 6 curated styles — from clean black and white to \
warm vintage tones to luxurious midnight blue.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🔸 HOW TO ORDER

1. Add this listing to your cart
2. In the "Personalization" box, tell us:
   → Location (city, address, or coordinates)
   → Style choice (see the 6 options below)
   → Custom text (optional — default is city name + coordinates)
   → Pin: None, Heart, Pin, House, or Grad Cap
   → Shape: Full or Circle
3. We'll design your map and send a proof within 1-2 business days
4. After your approval, we deliver the final file or ship your print

━━━━━━━━━━━━━━━━━━━━━━━━━━

🎨 6 STYLE OPTIONS

◈ Classic B&W — timeless black roads on white, blue water, green parks
◈ Midnight Blue — luxurious gold roads on deep navy background
◈ Clay & Sage — warm clay tones with sage green accents
◈ Warm Beige — earthy sepia neutrals, vintage map feel
◈ Watercolor — soft painted water and parks on clean white
◈ Vintage — terracotta roads with sage parks and deep navy water

All 6 styles are shown in our listing photos so you can see exactly \
how your map will look.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🖼️ WHAT YOU GET

◈ Digital Download — High-resolution 300 DPI PNG, ready to print anywhere
◈ Physical Print — Museum-quality poster on premium matte paper
◈ Framed Option — Black or white frame, shipped ready to hang

━━━━━━━━━━━━━━━━━━━━━━━━━━

📐 AVAILABLE SIZES

◈ 8×10 inches (20×25 cm)
◈ 11×14 inches (28×36 cm)
◈ 16×20 inches (41×51 cm)
◈ 18×24 inches (46×61 cm)
◈ 24×36 inches (61×91 cm)

━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ ABOUT THIS DESIGN

Every map is rendered from professional OpenStreetMap cartographic data \
at 300+ DPI — capturing every street from highways to residential lanes, \
every park, waterway, and building footprint. The clean typography shows \
your city name, state, and coordinates.

◈ 5 pin styles available — heart, classic pin, house, or graduation cap
◈ Full rectangle or circle crop
◈ Custom text on up to 3 lines

━━━━━━━━━━━━━━━━━━━━━━━━━━

🚚 SHIPPING & DELIVERY

◈ Digital: Proof within 1-2 business days, final file after approval
◈ Physical prints: 2-3 days design + 3-5 days production + shipping
◈ Framed prints: 5-7 business days + shipping
◈ Ships from the US via our premium print partner

━━━━━━━━━━━━━━━━━━━━━━━━━━

💛 PERFECT FOR

♥ Housewarming gifts — match any room's color scheme
♥ Travel memories — your favorite city in your favorite color
♥ Moving away gifts — a piece of home in their style
♥ Anniversary & wedding gifts — personalized and unique
♥ Office or dorm decor — choose the palette that fits

━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ Questions? Message us anytime — we love helping you create the perfect map.

© GeoLine Collective — Cartography as Craft""",
    personalization_prompt=(
        "Please provide:\n"
        "1. Location (city, address, or coordinates)\n"
        "2. Style: Classic B&W, Midnight Blue, Clay & Sage, Warm Beige, "
        "Watercolor, or Vintage\n"
        "3. Custom text (optional — default is city name + coordinates)\n"
        "4. Pin: None, Heart, Pin, House, or Grad Cap\n"
        "5. Shape: Full or Circle"
    ),
)


# ---------------------------------------------------------------------------
# Listing 4: Born In Baby Map
# ---------------------------------------------------------------------------

BORN_IN_MAP = CustomListing(
    slug="born_in_map",
    sku_prefix="GLC-BABY",
    title=(
        "Baby Birth Map Print | Born In Custom City Map, Nursery Wall Art "
        "| Personalized Newborn Gift"
    ),
    tags=[
        "baby birth map",
        "born in map print",
        "nursery wall art",
        "newborn gift map",
        "baby shower gift",
        "birth city map",
        "personalized nursery",
        "custom baby map",
        "nursery decor art",
        "baby keepsake gift",
        "birth location map",
        "baby room wall art",
        "newborn keepsake",
    ],
    description="""\
📍 A beautiful map of the city where their journey began.

Celebrate a new arrival with a custom map of their birthplace — \
personalized with baby's name, birth date, and a heart pin marking \
the city. Rendered in soft, nursery-friendly color palettes.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🔸 HOW TO ORDER

1. Add this listing to your cart
2. In the "Personalization" box, tell us:
   → Birth city or location
   → Baby's name
   → Birth date (and optional details: weight, time)
   → Style preference (see below)
   → Shape: Circle or Full
3. We'll design your map and send a proof within 1-2 business days
4. After your approval, we deliver the final file or ship your print

━━━━━━━━━━━━━━━━━━━━━━━━━━

🎨 NURSERY-FRIENDLY STYLES

◈ Warm Beige — soft earthy neutrals, gentle sepia tones
◈ Clay & Sage — warm blush with soft green accents
◈ Watercolor — painted pastels on clean white canvas

All three styles use muted, calming color palettes that complement \
any nursery decor.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🖼️ WHAT YOU GET

◈ Digital Download — High-resolution 300 DPI PNG, ready to print anywhere
◈ Physical Print — Museum-quality poster on premium matte paper
◈ Framed Option — Black or white frame, shipped ready to hang

━━━━━━━━━━━━━━━━━━━━━━━━━━

📐 AVAILABLE SIZES

◈ 8×10 inches (20×25 cm) — above the crib
◈ 11×14 inches (28×36 cm) — nursery gallery wall
◈ 16×20 inches (41×51 cm) — statement piece
◈ 18×24 inches (46×61 cm) — large nursery wall
◈ 24×36 inches (61×91 cm) — feature wall

━━━━━━━━━━━━━━━━━━━━━━━━━━

🍼 ABOUT THIS DESIGN

A heart pin marks the birth city, with baby's name displayed \
prominently below the map alongside the birth date and city name. \
The circle crop creates a clean, modern look that pairs beautifully \
with other nursery art.

Every street, park, and waterway is rendered from professional \
cartographic data at 300+ DPI — a meaningful keepsake they'll \
treasure as they grow.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🚚 SHIPPING & DELIVERY

◈ Digital: Proof within 1-2 business days, final file after approval
◈ Physical prints: 2-3 days design + 3-5 days production + shipping
◈ Framed prints: 5-7 business days + shipping
◈ Ships from the US via our premium print partner

━━━━━━━━━━━━━━━━━━━━━━━━━━

💛 PERFECT FOR

🍼 Baby shower gifts
🍼 Newborn welcome gifts
🍼 Nursery decor
🍼 First birthday keepsake
🍼 Birth announcement art

━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ Questions? Message us anytime — we love helping you create the perfect map.

© GeoLine Collective — Cartography as Craft""",
    personalization_prompt=(
        "Please provide:\n"
        "1. Birth city or location\n"
        "2. Baby's name\n"
        "3. Birth date (and optional details: weight, time)\n"
        "4. Style: Warm Beige, Clay & Sage, or Watercolor\n"
        "5. Shape: Circle or Full"
    ),
)


# ---------------------------------------------------------------------------
# Listing 5: Custom Blueprint Mosaic Map
# ---------------------------------------------------------------------------

CUSTOM_BLUEPRINT = CustomListing(
    slug="custom_blueprint",
    sku_prefix="GLC-CBLU",
    title=(
        "Custom Blueprint Mosaic Map Print | Detailed City Block Art "
        "| 4 Colors | Personalized Map Gift"
    ),
    tags=[
        "blueprint map print",
        "mosaic city map",
        "custom-map",
        "architectural map art",
        "shaded city poster",
        "modern wall art",
        "blueprint wall decor",
        "city block map",
        "detailed map print",
        "custom mosaic map",
        "choose your color map",
        "housewarming gift",
        "unique map art",
    ],
    description="""\
📍 An incredibly detailed mosaic map of ANY city — choose from 4 rich color palettes.

Every city block is individually shaded in 8 tones of a single color, \
with every street, alley, and path rendered as a crisp white overlay. \
The result is a stunning architectural-style map that reveals the \
hidden geometry of any city's street grid.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🔸 HOW TO ORDER

1. Add this listing to your cart
2. In the "Personalization" box, tell us:
   → City name or location
   → Color choice (see below)
3. We'll design your map and send a proof within 1-2 business days
4. After your approval, we deliver the final file or ship your print

━━━━━━━━━━━━━━━━━━━━━━━━━━

🎨 CHOOSE YOUR COLOR

◈ Navy — deep blues from midnight to sky blue
◈ Forest — rich greens from pine to sage
◈ Terracotta — warm earth tones from espresso to peach
◈ Charcoal — elegant greys from black to silver

Each color features 8 carefully graded shades that bring depth and \
dimension to the city's blocks.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🖼️ WHAT YOU GET

◈ Digital Download — High-resolution PNG file, ready to print anywhere
◈ Physical Print — Museum-quality poster on premium matte paper
◈ Framed Option — Black or white frame, shipped ready to hang

━━━━━━━━━━━━━━━━━━━━━━━━━━

📐 AVAILABLE SIZES

◈ 8×10 inches (20×25 cm)
◈ 11×14 inches (28×36 cm)
◈ 16×20 inches (41×51 cm)
◈ 18×24 inches (46×61 cm)
◈ 24×36 inches (61×91 cm)

━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ ABOUT THIS DESIGN

This map is created by breaking the city's entire street network into \
individual blocks using a technique called polygonization. Each block \
is assigned a shade from our 8-tone palette based on its size, creating \
a richly textured mosaic. A detailed white road overlay reveals every \
street, path, and alley — including footways and cycleways that most \
maps miss.

The layout features the city name in modern lowercase typography at \
top-right, with GPS coordinates embedded in a color swatch bar. \
A unique design you won't find anywhere else.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🚚 SHIPPING & DELIVERY

◈ Digital: Proof within 1-2 business days, final file after approval
◈ Physical prints: 2-3 days design + 3-5 days production + shipping
◈ Framed prints: 5-7 business days + shipping
◈ Ships from the US via our premium print partner

━━━━━━━━━━━━━━━━━━━━━━━━━━

💛 PERFECT FOR

♥ Architecture and design lovers
♥ Housewarming gifts — truly unique wall art
♥ Travel memories — your favorite city in a new light
♥ Office decor — sophisticated and modern
♥ Anyone who appreciates cartographic detail

━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ Questions? Message us anytime — we love helping you create the perfect map.

© GeoLine Collective — Cartography as Craft""",
    personalization_prompt=(
        "Please provide:\n"
        "1. City name or location\n"
        "2. Color: Navy, Forest, Terracotta, or Charcoal"
    ),
)


# ---------------------------------------------------------------------------
# All listings registry
# ---------------------------------------------------------------------------

ALL_CUSTOM_LISTINGS: dict[str, CustomListing] = {
    "where_we_met": WHERE_WE_MET,
    "graduation_map": GRADUATION_MAP,
    "multi_style_map": MULTI_STYLE_MAP,
    "born_in_map": BORN_IN_MAP,
    "custom_blueprint": CUSTOM_BLUEPRINT,
}


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------

def _format_variants(listing: CustomListing) -> str:
    """Format variant table for listing.txt."""
    lines: list[str] = []
    for v in listing.variants:
        sku = f"{listing.sku_prefix}-{v.sku_suffix}"
        lines.append(f"{sku:<28} | {v.size:<6} | {v.format_name:<18} | ${v.price:.2f}")
    return "\n".join(lines)


def generate_listing_text(slug: str, output_dir: str | None = None) -> str:
    """Generate a listing.txt file for the given custom listing slug.

    Returns the output file path.
    """
    listing = ALL_CUSTOM_LISTINGS[slug]

    out_dir = Path(output_dir) if output_dir else Path("etsy/renders/CustomExpansion") / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "listing.txt"

    content = "\n".join([
        "=" * 70,
        f"ETSY LISTING — {listing.title.split('|')[0].strip()}",
        "=" * 70,
        "",
        "TITLE",
        "-" * 40,
        listing.title,
        "",
        "TAGS",
        "-" * 40,
        ", ".join(listing.tags),
        "",
        "DESCRIPTION",
        "-" * 40,
        listing.description,
        "",
        "PERSONALIZATION INSTRUCTIONS",
        "-" * 40,
        listing.personalization_prompt,
        "",
        "VARIATIONS (SKU / Size / Format / Price)",
        "-" * 40,
        _format_variants(listing),
        "",
    ])

    out_path.write_text(content, encoding="utf-8")
    return str(out_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate custom expansion listing text")
    parser.add_argument("--listing", "-l", choices=list(ALL_CUSTOM_LISTINGS.keys()),
                        help="Generate one listing")
    parser.add_argument("--all", "-a", action="store_true", help="Generate all 5 listings")
    parser.add_argument("--preview", "-p", choices=list(ALL_CUSTOM_LISTINGS.keys()),
                        help="Preview listing to stdout without saving")
    args = parser.parse_args()

    if args.preview:
        sys.stdout.reconfigure(encoding="utf-8")
        listing = ALL_CUSTOM_LISTINGS[args.preview]
        print(f"Title ({len(listing.title)} chars):\n  {listing.title}")
        print(f"\nTags ({len(listing.tags)}):")
        for tag in listing.tags:
            print(f"  - {tag} ({len(tag)} chars)")
        print(f"\nSKU prefix: {listing.sku_prefix}")
        print(f"\nPersonalization:\n  {listing.personalization_prompt}")
        print(f"\nDescription (first 500 chars):\n  {listing.description[:500]}...")
        return

    if args.all:
        for slug in ALL_CUSTOM_LISTINGS:
            path = generate_listing_text(slug)
            print(f"Generated: {path}")
    elif args.listing:
        path = generate_listing_text(args.listing)
        print(f"Generated: {path}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify module loads and preview works**

Run: `cd /c/mapgen_glcollective && python -m etsy.custom_listings --preview where_we_met`
Expected: Title, tags, SKU prefix, personalization prompt printed to stdout. Title should be under 140 chars. Tags should be 13 items.

- [ ] **Step 3: Generate all 5 listing text files**

Run: `cd /c/mapgen_glcollective && python -m etsy.custom_listings --all`
Expected: 5 files created in `etsy/renders/CustomExpansion/{slug}/listing.txt`

- [ ] **Step 4: Verify all listing text files exist and have content**

Run: `for d in where_we_met graduation_map multi_style_map born_in_map custom_blueprint; do echo "=== $d ===" && wc -l etsy/renders/CustomExpansion/$d/listing.txt; done`
Expected: Each file has 60+ lines of content.

- [ ] **Step 5: Commit**

```bash
git add etsy/custom_listings.py etsy/renders/CustomExpansion/
git commit -m "feat: add custom expansion listing text generator for 5 new listings"
```

---

### Task 3: Render Sample Maps for All 5 Listings

**Files:**
- Create: `scripts/render_custom_expansion_samples.py`

This script renders the sample cities/themes needed for mockups and hero images. It uses subprocess isolation (same pattern as `batch_seo_render.py`) to prevent memory leaks.

- [ ] **Step 1: Create `scripts/render_custom_expansion_samples.py`**

```python
"""Render sample maps for custom expansion listings.

Renders hero/mockup source images for all 5 new custom listings.
Each listing needs renders at 16x20, 18x24, and 24x36 for mockups.

Usage:
    python scripts/render_custom_expansion_samples.py                  # All listings
    python scripts/render_custom_expansion_samples.py --listing where_we_met  # One listing
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path("etsy/renders/CustomExpansion")

# Each listing: list of (city, theme, extra_cli_args, filename_prefix)
RENDER_SPECS: dict[str, list[dict]] = {
    "where_we_met": [
        {
            "city": "Nashville", "theme": "37th_parallel",
            "args": ["--crop", "heart", "--layout", "date_night",
                     "--pin-style", "1", "--pin-color", "#CC3333",
                     "--text-line-1", "Sarah & James",
                     "--text-line-2", "Where It All Began",
                     "--text-line-3", "Nashville, Tennessee",
                     "--text-line-4", "June 15, 2019"],
            "prefix": "wwm_nashville_classic",
        },
        {
            "city": "Savannah", "theme": "midnight_blue",
            "args": ["--crop", "heart", "--layout", "date_night",
                     "--pin-style", "1", "--pin-color", "#D4AF37",
                     "--text-line-1", "Emma & Liam",
                     "--text-line-2", "Where It All Began",
                     "--text-line-3", "Savannah, Georgia",
                     "--text-line-4", "March 22, 2020"],
            "prefix": "wwm_savannah_midnight",
        },
        {
            "city": "Portland", "theme": "clay_sage",
            "args": ["--crop", "heart", "--layout", "date_night",
                     "--pin-style", "1", "--pin-color", "#8B4A34",
                     "--text-line-1", "Ava & Noah",
                     "--text-line-2", "Where It All Began",
                     "--text-line-3", "Portland, Oregon",
                     "--text-line-4", "October 8, 2021"],
            "prefix": "wwm_portland_clay",
        },
        {
            "city": "Paris", "theme": "warm_beige",
            "args": ["--crop", "heart", "--layout", "date_night",
                     "--pin-style", "1", "--pin-color", "#8B7355",
                     "--text-line-1", "Sophie & Antoine",
                     "--text-line-2", "Where It All Began",
                     "--text-line-3", "Paris, France",
                     "--text-line-4", "July 4, 2018"],
            "prefix": "wwm_paris_beige",
        },
    ],
    "graduation_map": [
        {
            "city": "Austin", "theme": "37th_parallel",
            "args": ["--pin-style", "5", "--pin-color", "#CC3333",
                     "--text-line-1", "UNIVERSITY OF TEXAS",
                     "--text-line-2", "Class of 2026",
                     "--text-line-3", "Austin, Texas"],
            "prefix": "grad_austin_classic",
        },
        {
            "city": "Nashville", "theme": "midnight_blue",
            "args": ["--pin-style", "5", "--pin-color", "#D4AF37",
                     "--text-line-1", "VANDERBILT UNIVERSITY",
                     "--text-line-2", "Class of 2026",
                     "--text-line-3", "Nashville, Tennessee"],
            "prefix": "grad_nashville_midnight",
        },
        {
            "city": "Portland", "theme": "clay_sage",
            "args": ["--pin-style", "5", "--pin-color", "#5C3A2E",
                     "--text-line-1", "PORTLAND STATE UNIVERSITY",
                     "--text-line-2", "Class of 2026",
                     "--text-line-3", "Portland, Oregon"],
            "prefix": "grad_portland_clay",
        },
    ],
    "multi_style_map": [
        # Nashville in all 6 themes — showcases the style variety
        {"city": "Nashville", "theme": "37th_parallel", "args": [],
         "prefix": "style_nashville_classic"},
        {"city": "Nashville", "theme": "midnight_blue", "args": [],
         "prefix": "style_nashville_midnight"},
        {"city": "Nashville", "theme": "clay_sage", "args": [],
         "prefix": "style_nashville_clay"},
        {"city": "Nashville", "theme": "warm_beige", "args": [],
         "prefix": "style_nashville_beige"},
        {"city": "Nashville", "theme": "watercolor", "args": [],
         "prefix": "style_nashville_watercolor"},
        {"city": "Nashville", "theme": "vintage", "args": [],
         "prefix": "style_nashville_vintage"},
    ],
    "born_in_map": [
        {
            "city": "Nashville", "theme": "warm_beige",
            "args": ["--crop", "circle", "--pin-style", "1",
                     "--pin-color", "#8B7355",
                     "--text-line-1", "EMMA GRACE",
                     "--text-line-2", "Born in Nashville",
                     "--text-line-3", "March 15, 2026"],
            "prefix": "baby_nashville_beige",
        },
        {
            "city": "Portland", "theme": "clay_sage",
            "args": ["--crop", "circle", "--pin-style", "1",
                     "--pin-color", "#8B4A34",
                     "--text-line-1", "OLIVER JAMES",
                     "--text-line-2", "Born in Portland",
                     "--text-line-3", "January 8, 2026"],
            "prefix": "baby_portland_clay",
        },
        {
            "city": "Paris", "theme": "watercolor",
            "args": ["--crop", "circle", "--pin-style", "1",
                     "--pin-color", "#555555",
                     "--text-line-1", "CHARLOTTE ROSE",
                     "--text-line-2", "Born in Paris",
                     "--text-line-3", "November 22, 2025"],
            "prefix": "baby_paris_watercolor",
        },
    ],
    "custom_blueprint": [
        # Reuse existing BlueprintV3 renders where available (Chicago navy, Berlin forest,
        # Nashville terracotta, Paris charcoal). Only render what's missing.
        # The blueprint renderer uses its own CLI path, not the standard cli.py.
        # For this listing, we mainly need the labeled PSD4 and detail crop
        # which already exist in BlueprintV3/. New renders only if needed.
    ],
}

# Sizes to render for each sample (mockup needs 24x36 + 18x24, detail crop needs 16x20)
RENDER_SIZES = ["16x20", "18x24", "24x36"]


def render_one(city: str, theme: str, size: str, extra_args: list[str],
               output_path: str) -> bool:
    """Render a single map via subprocess (memory-safe)."""
    cmd = [
        sys.executable, "cli.py",
        "--location", city,
        "--theme", theme,
        "--size", size,
        "--output", output_path,
        "--dpi", "300",
    ] + extra_args

    print(f"  Rendering {city} / {theme} / {size}...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[:200]}")
        return False
    return True


def render_listing(slug: str) -> None:
    """Render all samples for one listing."""
    specs = RENDER_SPECS.get(slug, [])
    if not specs:
        print(f"  No render specs for {slug} (uses existing renders)")
        return

    out_dir = BASE_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    for spec in specs:
        for size in RENDER_SIZES:
            filename = f"{spec['prefix']}_{size}.png"
            output_path = str(out_dir / filename)

            if Path(output_path).exists():
                print(f"  Skipping (exists): {filename}")
                continue

            render_one(
                city=spec["city"],
                theme=spec["theme"],
                size=size,
                extra_args=spec["args"],
                output_path=output_path,
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Render custom expansion samples")
    parser.add_argument("--listing", "-l",
                        choices=list(RENDER_SPECS.keys()),
                        help="Render samples for one listing only")
    args = parser.parse_args()

    if args.listing:
        print(f"=== Rendering: {args.listing} ===")
        render_listing(args.listing)
    else:
        for slug in RENDER_SPECS:
            print(f"\n=== Rendering: {slug} ===")
            render_listing(slug)

    print("\nDone!")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test with a single small render (one city, one size)**

Run: `cd /c/mapgen_glcollective && python scripts/render_custom_expansion_samples.py --listing where_we_met`

This will render 4 cities × 3 sizes = 12 renders. Takes ~30-60 min at 300 DPI. Can start with just one city by temporarily commenting out the other specs.

For a quick test, modify the script to render only Nashville at 16x20 first:
```bash
cd /c/mapgen_glcollective && python cli.py --location "Nashville" --theme 37th_parallel --size 16x20 --crop heart --layout date_night --pin-style 1 --pin-color "#CC3333" --text-line-1 "Sarah & James" --text-line-2 "Where It All Began" --text-line-3 "Nashville, Tennessee" --text-line-4 "June 15, 2019" --output "etsy/renders/CustomExpansion/where_we_met/wwm_nashville_classic_16x20.png" --dpi 300
```

Expected: A 16x20 heart-cropped map of Nashville with names above, date below.

- [ ] **Step 3: Commit the render script (renders themselves are gitignored)**

```bash
git add scripts/render_custom_expansion_samples.py
git commit -m "feat: add render script for custom expansion sample maps"
```

---

### Task 4: Create Asset Generation Script (Mockups, Detail Crops, Hero Images)

**Files:**
- Create: `scripts/create_custom_expansion_assets.py`

This generates mockups (via `mockup_composer.py` patterns), detail crops (via `image_composer.py`), and a style showcase grid for the multi-style listing.

- [ ] **Step 1: Create `scripts/create_custom_expansion_assets.py`**

```python
"""Generate mockups, detail crops, and hero images for custom expansion listings.

Requires sample renders to already exist in etsy/renders/CustomExpansion/{slug}/.
Run render_custom_expansion_samples.py first.

Usage:
    python scripts/create_custom_expansion_assets.py --listing where_we_met
    python scripts/create_custom_expansion_assets.py --all
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path("etsy/renders/CustomExpansion")
FONTS_DIR = Path("fonts")


def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a font from the fonts directory, fall back to default."""
    path = FONTS_DIR / name
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def create_detail_crop(listing_slug: str, source_16x20: str) -> str | None:
    """Create a detail crop with 'EVERY STREET. EVERY DETAIL.' badge.

    Uses the same approach as etsy/image_composer.py._draw_detail_badge().
    """
    source = Path(source_16x20)
    if not source.exists():
        print(f"  Source not found for detail crop: {source}")
        return None

    img = Image.open(source)
    w, h = img.size

    # Determine map area based on style
    # Blueprint: map starts at 22% from top; Classic/date_night: map is top 76%
    if "blueprint" in listing_slug:
        map_top = int(h * 0.22)
        map_bottom = h
    else:
        map_top = 0
        map_bottom = int(h * 0.76)

    map_h = map_bottom - map_top
    # Center 40% crop
    crop_size = int(min(w, map_h) * 0.6)
    cx = w // 2
    cy = map_top + map_h // 2
    left = cx - crop_size // 2
    top = cy - crop_size // 2
    right = left + crop_size
    bottom = top + crop_size

    # Clamp to image bounds
    left = max(0, left)
    top = max(0, top)
    right = min(w, right)
    bottom = min(h, bottom)

    cropped = img.crop((left, top, right, bottom))
    cropped = cropped.resize((2000, 2000), Image.LANCZOS)

    # Draw badge
    draw = ImageDraw.Draw(cropped)
    badge_font = _load_font("CenturyGothic-Bold.ttf", 42)
    badge_text = "EVERY STREET. EVERY DETAIL."
    margin = int(2000 * 0.04)

    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 24, 16

    rx = margin
    ry = margin
    rw = tw + pad_x * 2
    rh = th + pad_y * 2

    draw.rounded_rectangle(
        [rx, ry, rx + rw, ry + rh],
        radius=12,
        fill=(30, 30, 30, 200),
    )
    draw.text(
        (rx + pad_x, ry + pad_y),
        badge_text,
        font=badge_font,
        fill=(255, 255, 255),
    )

    out_path = BASE_DIR / listing_slug / "detail_crop.jpg"
    cropped.save(str(out_path), "JPEG", quality=92, dpi=(300, 300))
    print(f"  Detail crop: {out_path}")
    return str(out_path)


def create_style_showcase(listing_slug: str) -> str | None:
    """Create a 3x2 grid showing the same city in 6 themes (multi_style_map only).

    Each cell shows the 16x20 render with a label below.
    """
    if listing_slug != "multi_style_map":
        return None

    themes = [
        ("style_nashville_classic_16x20.png", "Classic B&W"),
        ("style_nashville_midnight_16x20.png", "Midnight Blue"),
        ("style_nashville_clay_16x20.png", "Clay & Sage"),
        ("style_nashville_beige_16x20.png", "Warm Beige"),
        ("style_nashville_watercolor_16x20.png", "Watercolor"),
        ("style_nashville_vintage_16x20.png", "Vintage"),
    ]

    src_dir = BASE_DIR / listing_slug
    images = []
    for filename, label in themes:
        path = src_dir / filename
        if not path.exists():
            print(f"  Missing for showcase: {path}")
            return None
        images.append((Image.open(path), label))

    # Layout: 3 columns x 2 rows
    cell_w, cell_h = 800, 1000
    label_h = 80
    padding = 30
    cols, rows = 3, 2
    canvas_w = cols * cell_w + (cols + 1) * padding
    canvas_h = rows * (cell_h + label_h) + (rows + 1) * padding + 100  # +100 for title

    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    # Title
    title_font = _load_font("Montserrat-Bold.ttf", 64)
    title = "Choose Your Style"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    draw.text(((canvas_w - title_w) // 2, 30), title, font=title_font, fill=(40, 40, 40))

    label_font = _load_font("Montserrat-Bold.ttf", 48)

    for i, (img, label) in enumerate(images):
        col = i % cols
        row = i // cols
        x = padding + col * (cell_w + padding)
        y = 100 + padding + row * (cell_h + label_h + padding)

        # Resize render to fit cell
        img_resized = img.copy()
        img_resized.thumbnail((cell_w, cell_h), Image.LANCZOS)
        # Center in cell
        ox = x + (cell_w - img_resized.width) // 2
        oy = y + (cell_h - img_resized.height) // 2
        canvas.paste(img_resized, (ox, oy))

        # Label
        lbbox = draw.textbbox((0, 0), label, font=label_font)
        lw = lbbox[2] - lbbox[0]
        lx = x + (cell_w - lw) // 2
        ly = y + cell_h + 10
        draw.text((lx, ly), label, font=label_font, fill=(60, 60, 60))

    out_path = src_dir / "style_showcase.jpg"
    canvas.save(str(out_path), "JPEG", quality=92)
    print(f"  Style showcase: {out_path}")
    return str(out_path)


def generate_assets(listing_slug: str) -> None:
    """Generate all assets for one listing."""
    src_dir = BASE_DIR / listing_slug
    if not src_dir.exists():
        print(f"  Directory not found: {src_dir}")
        return

    # Find the first 16x20 render for detail crop
    renders_16x20 = sorted(src_dir.glob("*_16x20.png"))
    if renders_16x20:
        create_detail_crop(listing_slug, str(renders_16x20[0]))
    else:
        print(f"  No 16x20 render found for detail crop in {src_dir}")

    # Style showcase (multi_style_map only)
    if listing_slug == "multi_style_map":
        create_style_showcase(listing_slug)

    # Note: Full PSD mockups use etsy/mockup_composer.py which requires
    # the renders to be in the expected directory structure. For custom
    # expansion listings, mockups can be generated by running:
    #   python -m etsy.mockup_composer --city <slug> --source-dir <path>
    # This is done manually after renders are ready.
    print(f"  Assets complete for {listing_slug}")
    print(f"  For mockups, run: python -m etsy.mockup_composer with renders from {src_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate custom expansion assets")
    parser.add_argument("--listing", "-l", help="Generate assets for one listing")
    parser.add_argument("--all", "-a", action="store_true", help="Generate all")
    args = parser.parse_args()

    if args.all:
        for slug in ["where_we_met", "graduation_map", "multi_style_map",
                      "born_in_map", "custom_blueprint"]:
            print(f"\n=== {slug} ===")
            generate_assets(slug)
    elif args.listing:
        print(f"=== {args.listing} ===")
        generate_assets(args.listing)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test with one listing that has renders available**

Run: `cd /c/mapgen_glcollective && python scripts/create_custom_expansion_assets.py --listing where_we_met`
Expected: `detail_crop.jpg` created in `etsy/renders/CustomExpansion/where_we_met/`

- [ ] **Step 3: Commit**

```bash
git add scripts/create_custom_expansion_assets.py
git commit -m "feat: add asset generation script for custom expansion mockups and detail crops"
```

---

### Task 5: Render All Samples and Generate All Assets

This is the execution task — running the render and asset scripts for all 5 listings.

- [ ] **Step 1: Render where_we_met samples (4 cities × 3 sizes = 12 renders)**

Run: `cd /c/mapgen_glcollective && python scripts/render_custom_expansion_samples.py --listing where_we_met`

This takes ~30-60 min. Verify a few renders visually.

- [ ] **Step 2: Render graduation_map samples (3 cities × 3 sizes = 9 renders)**

Run: `cd /c/mapgen_glcollective && python scripts/render_custom_expansion_samples.py --listing graduation_map`

- [ ] **Step 3: Render multi_style_map samples (6 themes × 3 sizes = 18 renders)**

Run: `cd /c/mapgen_glcollective && python scripts/render_custom_expansion_samples.py --listing multi_style_map`

This is the biggest batch. ~60-90 min.

- [ ] **Step 4: Render born_in_map samples (3 cities × 3 sizes = 9 renders)**

Run: `cd /c/mapgen_glcollective && python scripts/render_custom_expansion_samples.py --listing born_in_map`

- [ ] **Step 5: Verify custom_blueprint has existing renders**

Blueprint listing reuses existing renders from `etsy/renders/BlueprintV3/`. Verify:
```bash
ls etsy/renders/BlueprintV3/ | head -20
ls etsy/renders/BlueprintV3/shared_psd4_labeled.jpg
```

If `shared_psd4_labeled.jpg` exists, copy it to the custom_blueprint folder:
```bash
mkdir -p etsy/renders/CustomExpansion/custom_blueprint
cp etsy/renders/BlueprintV3/shared_psd4_labeled.jpg etsy/renders/CustomExpansion/custom_blueprint/color_options.jpg
```

- [ ] **Step 6: Generate detail crops and style showcase for all listings**

Run: `cd /c/mapgen_glcollective && python scripts/create_custom_expansion_assets.py --all`

- [ ] **Step 7: Visual review of key outputs**

Open and check:
- `etsy/renders/CustomExpansion/where_we_met/detail_crop.jpg` — heart map close-up
- `etsy/renders/CustomExpansion/multi_style_map/style_showcase.jpg` — 6-panel grid
- `etsy/renders/CustomExpansion/born_in_map/detail_crop.jpg` — circle map close-up
- `etsy/renders/CustomExpansion/graduation_map/detail_crop.jpg` — grad cap map close-up

---

### Task 6: Generate Mockups for All 5 Listings

Mockups use `etsy/mockup_composer.py` patterns. For custom expansion listings, we generate the same 7 flat mockups using the primary sample render (24x36 + 18x24).

- [ ] **Step 1: Identify the primary render for each listing**

For mockups, we need 24x36 and 18x24 renders. The "featured" city for each listing:

| Listing | Featured Render (24x36) | Featured Render (18x24) |
|---------|------------------------|------------------------|
| where_we_met | `wwm_nashville_classic_24x36.png` | `wwm_nashville_classic_18x24.png` |
| graduation_map | `grad_austin_classic_24x36.png` | `grad_austin_classic_18x24.png` |
| multi_style_map | `style_nashville_classic_24x36.png` | `style_nashville_classic_18x24.png` |
| born_in_map | `baby_nashville_beige_24x36.png` | `baby_nashville_beige_18x24.png` |
| custom_blueprint | Reuse from `BlueprintV3/` | Reuse from `BlueprintV3/` |

- [ ] **Step 2: Generate mockups using mockup_composer patterns**

For each listing, the mockups can be generated by pointing `mockup_composer.py` at the render directory. Since `mockup_composer.py` expects a specific directory structure, the simplest approach is to use it directly with `--source-dir`:

```bash
# Example for where_we_met (adapt paths for each listing):
cd /c/mapgen_glcollective
python -m etsy.mockup_composer --city wwm_nashville_classic \
  --source-dir etsy/renders/CustomExpansion/where_we_met \
  --output-dir etsy/renders/CustomExpansion/where_we_met
```

If `mockup_composer.py` doesn't support `--source-dir`, mockups can be generated manually by copying renders to the expected location or by modifying the composer call. Check:

```bash
python -m etsy.mockup_composer --help
```

Alternative: manually composite using the PSD template patterns from `etsy/TUR2/Best/Flat/`.

- [ ] **Step 3: Verify mockup outputs**

Each listing directory should have 7 mockup JPGs:
```
mockup_main.jpg, mockup_mockup4.jpg, mockup_once.jpg, mockup_vv1.jpg,
mockup_2frames.jpg, mockup_cls4.jpg, mockup_framepsd.jpg
```

- [ ] **Step 4: Commit the scripts (render outputs are gitignored)**

```bash
git add -A
git commit -m "feat: complete custom expansion — renders, assets, and mockups for 5 new listings"
```

---

## Post-Implementation: Manual Etsy Steps

After all renders, assets, and listing text are generated, the following manual steps publish the listings:

1. **Refresh Etsy auth token:** `python -m etsy.auth --refresh`
2. **Create Etsy drafts** via API or manually in Etsy dashboard
3. **Upload images** in the order specified in `docs/STYLE_WORKFLOW.md` Section 8
4. **Set variants** with the pricing from `CUSTOM_EXPANSION_VARIANTS`
5. **Enable personalization** with the prompts from each listing definition
6. **Set Etsy sale** to 25% off on all custom expansion listings
7. **Sync Gelato** and connect physical variants
8. **Review and publish** each listing

---

## Verification Checklist

- [ ] All 5 listing.txt files generated with correct titles (under 140 chars) and 13 tags each
- [ ] Sample renders exist for all 5 listings in `etsy/renders/CustomExpansion/`
- [ ] Detail crops generated for all 5 listings
- [ ] Style showcase grid generated for multi_style_map
- [ ] Mockups generated for all 5 listings (7 per listing = 35 total)
- [ ] No tag contains periods (Etsy rejects them)
- [ ] All tags are under 20 characters
- [ ] Custom Blueprint listing includes `custom-map` tag
- [ ] Multi-Style listing includes `custom-map` tag
- [ ] Pricing uses original prices (sale set in Etsy dashboard)
