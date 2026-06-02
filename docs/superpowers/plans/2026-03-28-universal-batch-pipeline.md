# Universal Batch Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `scripts/batch_universal.py` — a single script that takes (city, style) and produces a complete Etsy listing end-to-end: render → mockups → listing text → Etsy draft → Gelato CSV.

**Architecture:** Style-specific renderers are wrapped behind a unified `render_city(city, style)` dispatch function. Each city is rendered in a subprocess for memory isolation. Post-render stages (mockups, listing text, Etsy API, Gelato CSV) run in the parent process since they're lightweight. A progress tracker prevents re-doing completed work on restart.

**Tech Stack:** Python 3.13, PIL/Pillow, psd-tools, matplotlib, osmnx, Etsy API v3, Gelato CSV format

---

## File Structure

| File | Responsibility |
|------|---------------|
| `scripts/batch_universal.py` | CLI entry point + orchestrator — dispatches to renderers, coordinates all stages |
| `etsy/style_config.py` | Style definitions (pricing, SKUs, tags, descriptions, render params per style) |
| `etsy/listing_text.py` | SEO-optimized listing text generation for all 4 styles |
| `etsy/etsy_lister.py` | Etsy API orchestration — create draft + upload images + set variants in one call |

**Existing files modified:**
| File | Change |
|------|--------|
| `etsy/city_list.py` | No changes — used as-is for city data |
| `etsy/mockup_composer.py` | No changes — used as-is for mockup generation |
| `etsy/api_client.py` | No changes — used as-is for API calls |
| `engine/blueprint_renderer.py` | No changes — called via subprocess |
| `engine/florence_renderer.py` | No changes — called via subprocess |
| `engine/renderer.py` | No changes — called via subprocess |

---

### Task 1: Style Configuration Module

**Files:**
- Create: `etsy/style_config.py`

This module defines everything that varies per style: renderer invocation, pricing, SKU patterns, SEO keywords, Gelato product UIDs, and render parameters.

- [ ] **Step 1: Create style_config.py with StyleConfig dataclass and all 4 style definitions**

```python
# etsy/style_config.py
"""Style configuration for all map products — pricing, SKUs, tags, render params."""

from __future__ import annotations
from dataclasses import dataclass, field

# Gelato product UIDs per size × format
GELATO_UIDS: dict[str, dict[str, str]] = {
    "unframed": {
        "8x10": "flat_8x10-inch-200x250-mm_170-gsm-65lb-uncoated_4-0_ver",
        "11x14": "flat_11x14-inch-270x350-mm_170-gsm-65lb-uncoated_4-0_ver",
        "16x20": "flat_16x20-inch-400x500-mm_170-gsm-65lb-uncoated_4-0_ver",
        "18x24": "flat_18x24-inch-450x600-mm_170-gsm-65lb-uncoated_4-0_ver",
        "24x36": "flat_24x36-inch-600x900-mm_170-gsm-65lb-uncoated_4-0_ver",
    },
    "framed_black": {
        "8x10": "framed-poster_8x10-inch-200x250-mm_black_170-gsm-65lb-uncoated_4-0_ver",
        "11x14": "framed-poster_11x14-inch-280x355-mm_black_170-gsm-65lb-uncoated_4-0_ver",
        "16x20": "framed-poster_16x20-inch-400x500-mm_black_170-gsm-65lb-uncoated_4-0_ver",
        "18x24": "framed-poster_18x24-inch-450x600-mm_black_170-gsm-65lb-uncoated_4-0_ver",
        "24x36": "framed-poster_24x36-inch-600x900-mm_black_170-gsm-65lb-uncoated_4-0_ver",
    },
    "framed_white": {
        "8x10": "framed-poster_8x10-inch-200x250-mm_white_170-gsm-65lb-uncoated_4-0_ver",
        "11x14": "framed-poster_11x14-inch-280x355-mm_white_170-gsm-65lb-uncoated_4-0_ver",
        "16x20": "framed-poster_16x20-inch-400x500-mm_white_170-gsm-65lb-uncoated_4-0_ver",
        "18x24": "framed-poster_18x24-inch-450x600-mm_white_170-gsm-65lb-uncoated_4-0_ver",
        "24x36": "framed-poster_24x36-inch-600x900-mm_white_170-gsm-65lb-uncoated_4-0_ver",
    },
}

# Etsy shop constants
SHOP_ID = 64614087
SHIPPING_PROFILE_ID = 299396504426  # Gelato: Free shipping
RETURN_POLICY_ID = 1470278944285
READINESS_STATE_ID = 1470278628937
TAXONOMY_ID = 1029  # Art > Prints
SECTION_CITY_MAPS = 57587152
SECTION_CUSTOM_MAPS = 57768965


@dataclass(frozen=True)
class VariantPrice:
    """Price for a single size × format combination."""
    size: str
    format_name: str  # "Unframed Print", "Framed - Black", "Framed - White"
    price: float
    sku_suffix: str   # e.g., "UNF-8x10", "FBK-16x20"


@dataclass(frozen=True)
class StyleConfig:
    """Complete configuration for one map style."""
    name: str                       # "classic", "florence", "blueprint", "monomap"
    display_name: str               # "Classic Street Map", "Florence Mosaic", etc.
    renderer: str                   # "classic", "florence", "blueprint", "monomap"
    sku_prefix: str                 # "GLC-CLASSIC", "GLC-FLOR", etc.
    shop_section_id: int            # Etsy shop section
    listing_type: str               # "physical" or "both" (digital + physical)
    dpi: int                        # Render DPI
    render_timeout: int             # Subprocess timeout in seconds
    title_templates: list[str]      # SEO title templates with {city}, {state}, {gift} placeholders
    base_tags: list[str]            # Style-specific tags (city tags added dynamically)
    description_intro: str          # Style-specific description opening
    variants: list[VariantPrice]    # All size × format × price combinations
    distance_scale: float = 1.0    # Multiplier on city_list distance
    color_name: str | None = None   # For styles with color variants (blueprint default color)
    extra_render_args: dict = field(default_factory=dict)


# ── Variant pricing tables ────────────────────────────────────────────────────

CITY_MAP_VARIANTS: list[VariantPrice] = [
    # Digital (5)
    VariantPrice("8x10", "Digital Download", 4.20, "DIG-8x10"),
    VariantPrice("11x14", "Digital Download", 5.04, "DIG-11x14"),
    VariantPrice("16x20", "Digital Download", 5.88, "DIG-16x20"),
    VariantPrice("18x24", "Digital Download", 6.72, "DIG-18x24"),
    VariantPrice("24x36", "Digital Download", 7.80, "DIG-24x36"),
    # Unframed (5)
    VariantPrice("8x10", "Unframed Print", 34.83, "UNF-8x10"),
    VariantPrice("11x14", "Unframed Print", 39.85, "UNF-11x14"),
    VariantPrice("16x20", "Unframed Print", 46.35, "UNF-16x20"),
    VariantPrice("18x24", "Unframed Print", 51.37, "UNF-18x24"),
    VariantPrice("24x36", "Unframed Print", 62.45, "UNF-24x36"),
    # Framed Black (5)
    VariantPrice("8x10", "Framed - Black", 78.07, "FBK-8x10"),
    VariantPrice("11x14", "Framed - Black", 87.50, "FBK-11x14"),
    VariantPrice("16x20", "Framed - Black", 119.62, "FBK-16x20"),
    VariantPrice("18x24", "Framed - Black", 131.12, "FBK-18x24"),
    VariantPrice("24x36", "Framed - Black", 216.17, "FBK-24x36"),
    # Framed White (5)
    VariantPrice("8x10", "Framed - White", 78.07, "FWH-8x10"),
    VariantPrice("11x14", "Framed - White", 87.50, "FWH-11x14"),
    VariantPrice("16x20", "Framed - White", 119.62, "FWH-16x20"),
    VariantPrice("18x24", "Framed - White", 131.12, "FWH-18x24"),
    VariantPrice("24x36", "Framed - White", 216.17, "FWH-24x36"),
]

GIFT_KEYWORDS: list[str] = [
    "Housewarming Gift", "New Home Gift", "Anniversary Gift",
    "Travel Gift", "Birthday Gift", "Moving Away Gift", "Graduation Gift",
]


# ── Style definitions ─────────────────────────────────────────────────────────

CLASSIC = StyleConfig(
    name="classic",
    display_name="Classic Street Map",
    renderer="classic",
    sku_prefix="GLC",
    shop_section_id=SECTION_CITY_MAPS,
    listing_type="physical",
    dpi=300,
    render_timeout=3600,
    distance_scale=1.0,
    title_templates=[
        "{city} Map Print, Minimalist City Poster, Black White Wall Art, {gift}",
        "{city} Street Map Wall Art, Modern Home Decor, City Poster, {gift}",
        "Minimalist {city} Map Print, {state} City Poster, Black White Art, {gift}",
        "{city} Map Poster, City Street Art, Minimalist Wall Decor, {gift}",
    ],
    base_tags=[
        "minimalist map print", "street map poster", "black white map",
        "city map wall art", "modern map print", "map wall decor",
    ],
    description_intro=(
        "A clean, elegant street map featuring detailed black roads on a crisp "
        "white background with blue waterways and green parks. The timeless design "
        "works beautifully in any room."
    ),
    variants=CITY_MAP_VARIANTS,
)

FLORENCE = StyleConfig(
    name="florence",
    display_name="Florence Mosaic Map",
    renderer="florence",
    sku_prefix="GLC-FLOR",
    shop_section_id=SECTION_CITY_MAPS,
    listing_type="physical",
    dpi=300,
    render_timeout=7200,
    distance_scale=0.65,
    title_templates=[
        "{city} Map Wall Art, Colorful Mosaic City Poster, Abstract Street Map, {gift}",
        "{city} Colorful Map Print, Mosaic City Block Art, Modern Wall Decor, {gift}",
        "Colorful {city} Map Poster, Abstract City Art, Mosaic Street Map, {gift}",
        "{city} Map Art Print, Vibrant City Mosaic Poster, Block Map Wall Art, {gift}",
    ],
    base_tags=[
        "colorful map print", "mosaic city poster", "abstract city art",
        "city block art", "modern map print", "vibrant wall art",
    ],
    description_intro=(
        "A vibrant, colorful mosaic map where each city block is individually "
        "colored from a warm palette of oranges, ambers, greens, grays, and teals, "
        "creating a stunning mosaic that reveals your city's unique street grid."
    ),
    variants=CITY_MAP_VARIANTS,
)

BLUEPRINT = StyleConfig(
    name="blueprint",
    display_name="Blueprint Mosaic Map",
    renderer="blueprint",
    sku_prefix="GLC-BLUE",
    shop_section_id=SECTION_CITY_MAPS,
    listing_type="physical",
    dpi=200,  # Blueprint renders at 200 DPI (still high quality, faster)
    render_timeout=3600,
    distance_scale=0.7,
    color_name="terracotta",  # Default color for pre-made listings
    title_templates=[
        "{city} Map Print, Blueprint Mosaic Wall Art, Detailed Street Map Poster, {gift}",
        "{city} Blueprint Map Poster, Shaded City Mosaic Art, Modern Wall Decor, {gift}",
        "Blueprint {city} Map Print, Detailed Mosaic Street Art, City Poster, {gift}",
        "{city} Map Wall Art, Blueprint Style Poster, Mosaic City Print, {gift}",
    ],
    base_tags=[
        "blueprint map art", "mosaic city print", "detailed street map",
        "shaded map poster", "modern map art", "city block art",
    ],
    description_intro=(
        "A beautifully detailed mosaic map combining shaded blocks with an "
        "incredibly detailed street overlay, revealing every road, path, and "
        "alley in the city."
    ),
    variants=CITY_MAP_VARIANTS,
)

MONOMAP = StyleConfig(
    name="monomap",
    display_name="Monochrome Map",
    renderer="monomap",
    sku_prefix="GLC-MONO",
    shop_section_id=SECTION_CITY_MAPS,
    listing_type="physical",
    dpi=300,
    render_timeout=7200,
    distance_scale=0.65,
    color_name="navy",  # Default color for pre-made listings
    title_templates=[
        "{city} Map Print, Minimalist Monochrome Wall Art, Navy City Poster, {gift}",
        "{city} Monochrome Map Poster, Bold City Art, Minimalist Wall Decor, {gift}",
        "Monochrome {city} Map Print, Navy City Poster, Modern Wall Art, {gift}",
        "{city} Map Wall Art, Monochrome City Print, Bold Street Map Poster, {gift}",
    ],
    base_tags=[
        "monochrome map print", "navy map poster", "minimalist wall art",
        "bold city art", "modern map print", "city block art",
    ],
    description_intro=(
        "A striking monochrome map that transforms the city's street grid "
        "into a bold, minimalist mosaic with crisp white streets on a rich "
        "solid color background."
    ),
    variants=CITY_MAP_VARIANTS,
)

ALL_STYLES: dict[str, StyleConfig] = {
    "classic": CLASSIC,
    "florence": FLORENCE,
    "blueprint": BLUEPRINT,
    "monomap": MONOMAP,
}


def get_style(name: str) -> StyleConfig:
    """Get a style config by name. Raises KeyError if not found."""
    return ALL_STYLES[name]
```

- [ ] **Step 2: Verify it imports**

Run: `python -c "from etsy.style_config import ALL_STYLES; print(list(ALL_STYLES.keys()))"`
Expected: `['classic', 'florence', 'blueprint', 'monomap']`

- [ ] **Step 3: Commit**

```bash
git add etsy/style_config.py
git commit -m "feat: add style configuration module for universal batch pipeline"
```

---

### Task 2: Listing Text Generator (Multi-Style)

**Files:**
- Create: `etsy/listing_text.py`

Generates SEO-optimized titles, descriptions, and tags for any style × city combination.

- [ ] **Step 1: Create listing_text.py**

```python
# etsy/listing_text.py
"""Generate SEO-optimized listing text for any style × city combination."""

from __future__ import annotations

import hashlib

from etsy.city_list import CityListing
from etsy.style_config import StyleConfig, GIFT_KEYWORDS


def _rotate_choice(items: list, seed: str) -> str:
    """Deterministic rotation based on seed string."""
    idx = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(items)
    return items[idx]


def generate_title(city: CityListing, style: StyleConfig) -> str:
    """Generate an SEO-optimized title (max 140 chars)."""
    template = _rotate_choice(style.title_templates, f"{city.slug}_{style.name}")
    gift = _rotate_choice(GIFT_KEYWORDS, f"{city.slug}_{style.name}_gift")

    display_city = city.display_city or city.city
    title = template.format(city=display_city, state=city.state, gift=gift)
    return title[:140]


def generate_tags(city: CityListing, style: StyleConfig) -> list[str]:
    """Generate 13 SEO tags (max 20 chars each)."""
    display_city = city.display_city or city.city
    city_lower = display_city.lower()

    # City-specific tags (3-4)
    city_tags = [
        f"{city_lower} map",
        f"{city_lower} wall art",
        f"{city_lower} poster",
    ]

    # Gift occasion tags (2-3)
    gift_tags = [
        "housewarming gift",
        "new home gift",
        "anniversary gift",
    ]

    # Combine: city + style base + gift, truncate to 20 chars, max 13
    all_tags = city_tags + style.base_tags + gift_tags
    # Filter to 20 char max and deduplicate
    seen: set[str] = set()
    result: list[str] = []
    for tag in all_tags:
        tag = tag[:20]
        if tag not in seen:
            seen.add(tag)
            result.append(tag)
        if len(result) == 13:
            break
    return result


def generate_description(city: CityListing, style: StyleConfig) -> str:
    """Generate a full listing description."""
    display_city = city.display_city or city.city
    state = city.display_subtitle or city.state

    sizes_section = (
        "AVAILABLE SIZES\n"
        "- 8x10 inches (20x25 cm)\n"
        "- 11x14 inches (28x36 cm)\n"
        "- 16x20 inches (40x50 cm)\n"
        "- 18x24 inches (45x60 cm)\n"
        "- 24x36 inches (60x90 cm)"
    )

    physical_section = (
        "PRINT QUALITY\n"
        "- Museum-quality 170gsm uncoated matte paper\n"
        "- Vibrant, fade-resistant inks\n"
        "- Optional black or white frame\n"
        "- Ships flat in protective packaging"
    )

    return (
        f"{display_city}, {state}\n\n"
        f"{style.description_intro}\n\n"
        f"{sizes_section}\n\n"
        f"{physical_section}\n\n"
        "All maps are rendered from OpenStreetMap data at 300 DPI — "
        "every street, park, and waterway is captured in precise detail.\n\n"
        "Makes a perfect gift for anyone who loves their city."
    )


def generate_listing_text(city: CityListing, style: StyleConfig) -> dict:
    """Generate complete listing text for a city × style combination.

    Returns dict with title, tags, description keys.
    """
    return {
        "title": generate_title(city, style),
        "tags": generate_tags(city, style),
        "description": generate_description(city, style),
    }
```

- [ ] **Step 2: Verify it generates text**

Run: `python -c "from etsy.listing_text import generate_listing_text; from etsy.style_config import CLASSIC; from etsy.city_list import CITIES; text = generate_listing_text(CITIES[0], CLASSIC); print(text['title']); print(text['tags'][:5])"`

- [ ] **Step 3: Commit**

```bash
git add etsy/listing_text.py
git commit -m "feat: add multi-style listing text generator"
```

---

### Task 3: Etsy Lister Orchestration Module

**Files:**
- Create: `etsy/etsy_lister.py`

Wraps the Etsy API client into a single `create_full_listing()` call that creates a draft, uploads images, sets variants, and enables personalization.

- [ ] **Step 1: Create etsy_lister.py**

```python
# etsy/etsy_lister.py
"""Orchestrates Etsy listing creation — draft + images + variants in one call."""

from __future__ import annotations

import os
import time
from pathlib import Path

from etsy.api_client import EtsyClient
from etsy.style_config import (
    StyleConfig, SHOP_ID, SHIPPING_PROFILE_ID, RETURN_POLICY_ID,
    READINESS_STATE_ID, TAXONOMY_ID,
)


def create_full_listing(
    client: EtsyClient,
    title: str,
    description: str,
    tags: list[str],
    style: StyleConfig,
    image_paths: list[str],
    image_alt_texts: list[str] | None = None,
) -> dict:
    """Create a complete Etsy draft listing with images and variants.

    Returns dict with listing_id and variant count.
    """
    # Ensure tags are max 20 chars
    clean_tags = [t[:20] for t in tags[:13]]

    # Create draft
    base_price = min(v.price for v in style.variants)
    result = client.create_draft_listing(
        shop_id=SHOP_ID,
        title=title,
        description=description,
        price=base_price,
        quantity=999,
        tags=clean_tags,
        who_made="i_did",
        when_made="made_to_order",
        taxonomy_id=TAXONOMY_ID,
        listing_type="physical",
        shipping_profile_id=SHIPPING_PROFILE_ID,
        return_policy_id=RETURN_POLICY_ID,
        shop_section_id=style.shop_section_id,
        readiness_state_id=READINESS_STATE_ID,
    )
    listing_id = result["listing_id"]

    # Upload images (max 10)
    alt_texts = image_alt_texts or [""] * len(image_paths)
    for rank, (img_path, alt) in enumerate(zip(image_paths[:10], alt_texts[:10]), 1):
        if os.path.exists(img_path):
            client.upload_listing_image(
                SHOP_ID, listing_id, img_path, rank=rank, alt_text=alt[:500],
            )
            time.sleep(0.3)

    # Set inventory variants
    products = []
    for v in style.variants:
        products.append({
            "sku": f"{style.sku_prefix}-{v.sku_suffix}".upper(),
            "property_values": [
                {"property_id": 513, "property_name": "Format", "values": [v.format_name]},
                {"property_id": 514, "property_name": "Size", "values": [v.size]},
            ],
            "offerings": [{
                "price": v.price,
                "quantity": 999,
                "is_enabled": True,
                "readiness_state_id": READINESS_STATE_ID,
            }],
        })

    client.update_listing_inventory(
        listing_id=listing_id,
        products=products,
        price_on_property=[513, 514],
        quantity_on_property=[513, 514],
        sku_on_property=[513, 514],
    )

    return {"listing_id": listing_id, "variant_count": len(products)}
```

- [ ] **Step 2: Verify it imports**

Run: `python -c "from etsy.etsy_lister import create_full_listing; print('OK')"`

- [ ] **Step 3: Commit**

```bash
git add etsy/etsy_lister.py
git commit -m "feat: add Etsy lister orchestration module"
```

---

### Task 4: Universal Batch Pipeline Script

**Files:**
- Create: `scripts/batch_universal.py`

The main orchestrator. Takes (city, style) and runs the full pipeline: render → mockups → listing text → Etsy draft → Gelato CSV. Uses subprocess isolation for rendering and a progress tracker to resume interrupted runs.

- [ ] **Step 1: Create batch_universal.py**

```python
# scripts/batch_universal.py
"""Universal batch pipeline — render any city × style → complete Etsy listing.

Usage:
    # Single city, single style
    python scripts/batch_universal.py --city "Nashville" --style blueprint

    # All cities, one style
    python scripts/batch_universal.py --style blueprint

    # Specific cities, all styles
    python scripts/batch_universal.py --city "Nashville" --city "Chicago" --style all

    # Resume interrupted run
    python scripts/batch_universal.py --style blueprint --resume

    # Render only (no Etsy API)
    python scripts/batch_universal.py --style blueprint --render-only

    # Dry run (show what would be done)
    python scripts/batch_universal.py --style blueprint --dry-run
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from etsy.city_list import CITIES, CityListing
from etsy.style_config import (
    ALL_STYLES, StyleConfig, GELATO_UIDS, SHOP_ID, get_style,
)
from etsy.listing_text import generate_listing_text

PYTHON = sys.executable
SIZES = ["8x10", "11x14", "16x20", "18x24", "24x36"]
PROGRESS_FILE = "etsy/renders/.batch_progress.json"


# ── Progress tracking ─────────────────────────────────────────────────────────

def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {}


def save_progress(progress: dict) -> None:
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def progress_key(city: CityListing, style: StyleConfig) -> str:
    return f"{city.slug}_{style.name}"


# ── Render dispatch (subprocess isolated) ─────────────────────────────────────

def render_city_classic(city: CityListing, style: StyleConfig, out_dir: str) -> bool:
    """Render all 5 sizes using Classic (37th_parallel) renderer."""
    script = f"""
import sys, os, gc
sys.path.insert(0, os.getcwd())
from engine.renderer import render_poster
for size in {SIZES}:
    out = os.path.join("{out_dir}", "{city.slug}_" + size + ".png")
    if os.path.exists(out):
        print(f"  {{size}} exists, skipping")
        continue
    print(f"  Rendering {{size}}...")
    render_poster(
        location="{city.lat},{city.lon}",
        theme="37th_parallel",
        size=size,
        distance={city.distance},
        output_path=out,
        dpi={style.dpi},
    )
    gc.collect()
print("DONE")
"""
    result = subprocess.run(
        [PYTHON, "-c", script], cwd=PROJECT_ROOT,
        timeout=style.render_timeout, capture_output=True, text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"  STDERR: {result.stderr[-500:]}")
    return result.returncode == 0


def render_city_florence(city: CityListing, style: StyleConfig, out_dir: str) -> bool:
    """Render all 5 sizes using Florence renderer (master crop approach)."""
    distance = int(city.distance * style.distance_scale)
    script = f"""
import sys, os, gc
sys.path.insert(0, os.getcwd())
from engine.renderer import load_theme
from engine.florence_renderer import render_florence_all_sizes
theme = load_theme("florence")
render_florence_all_sizes(
    location="{city.lat},{city.lon}",
    theme_data=theme,
    sizes={SIZES},
    dpi={style.dpi},
    output_dir="{out_dir}",
    distance={distance},
    city_name="{city.display_city or city.city}",
    state_name="{city.display_subtitle or city.state}",
    city_slug="{city.slug}",
    force=False,
)
gc.collect()
print("DONE")
"""
    result = subprocess.run(
        [PYTHON, "-c", script], cwd=PROJECT_ROOT,
        timeout=style.render_timeout, capture_output=True, text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"  STDERR: {result.stderr[-500:]}")
    return result.returncode == 0


def render_city_blueprint(city: CityListing, style: StyleConfig, out_dir: str) -> bool:
    """Render Blueprint style — all 5 sizes via master crop approach."""
    color = style.color_name or "terracotta"
    distance = int(city.distance * style.distance_scale)
    script = f"""
import sys, os, gc
sys.path.insert(0, os.getcwd())
from engine.blueprint_renderer import render_shaded_map, compose_blueprint_poster, PALETTES, detect_extent
from export.output_sizes import get_size_config
from PIL import Image

color = "{color}"
palette_data = PALETTES[color]
lat, lon = {city.lat}, {city.lon}
distance = {distance}
out_dir = "{out_dir}"
dpi = {style.dpi}
slug = "{city.slug}"
city_name = "{city.display_city or city.city}"
state_name = "{city.display_subtitle or city.state}"
os.makedirs(out_dir, exist_ok=True)

# Auto-detect extent if not specified
radius = detect_extent(lat, lon)

# Render master raw map at 24x36 aspect (tallest)
master_raw = os.path.join(out_dir, f"_master_raw.png")
ps = get_size_config("24x36")
render_shaded_map(
    lat=lat, lon=lon, radius=radius,
    palette=palette_data["shades"],
    dpi=dpi, fig_width=ps["width_in"], fig_height=ps["height_in"],
    output_path=master_raw,
)

master_img = Image.open(master_raw).convert("RGB")
master_w, master_h = master_img.size
print(f"  Master: {{master_w}}x{{master_h}} px")

# Compose each size from master crop
for size in {SIZES}:
    out_path = os.path.join(out_dir, f"{{slug}}_{{size}}.png")
    if os.path.exists(out_path):
        print(f"  {{size}} exists, skipping")
        continue
    ps = get_size_config(size)
    target_aspect = ps["height_in"] / ps["width_in"]
    master_aspect = 36 / 24  # 1.5

    if target_aspect < master_aspect:
        crop_h = int(master_w * target_aspect)
        y_offset = (master_h - crop_h) // 2
        cropped = master_img.crop((0, y_offset, master_w, y_offset + crop_h))
    else:
        cropped = master_img

    # Save cropped raw map to temp
    tmp_crop = os.path.join(out_dir, f"_crop_{{size}}.png")
    cropped.save(tmp_crop)

    compose_blueprint_poster(
        map_image_path=tmp_crop,
        city_name=city_name,
        state_or_region=state_name,
        lat=lat, lon=lon,
        palette=palette_data["shades"],
        text_color=palette_data["text_color"],
        size_name=size, dpi=dpi,
        output_path=out_path,
    )
    os.remove(tmp_crop)
    print(f"  {{size}} done")

# Cleanup
os.remove(master_raw)
gc.collect()
print("DONE")
"""
    result = subprocess.run(
        [PYTHON, "-c", script], cwd=PROJECT_ROOT,
        timeout=style.render_timeout, capture_output=True, text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"  STDERR: {result.stderr[-500:]}")
    return result.returncode == 0


def render_city_monomap(city: CityListing, style: StyleConfig, out_dir: str) -> bool:
    """Render MonoMap style — single color, Florence renderer with mono palette."""
    color_hex = {"navy": "#1C3D6E", "charcoal": "#4A4A4A", "forest": "#2A5A2A",
                 "terracotta": "#B5553A", "dusty_rose": "#A35580", "black": "#1A1A1A",
                 }.get(style.color_name or "navy", "#1C3D6E")
    text_color = color_hex
    distance = int(city.distance * style.distance_scale)
    script = f"""
import sys, os, gc, json
sys.path.insert(0, os.getcwd())
from engine.florence_renderer import render_florence_all_sizes

theme = {{
    "palette": ["{color_hex}"],
    "bg_color": "#FFFFFF",
    "water_color": "#FFFFFF",
    "street_color": "#FFFFFF",
    "poster_bg": "#FFFFFF",
    "text_color": "{text_color}",
    "font": "Switzer-Bold.ttf",
}}

render_florence_all_sizes(
    location="{city.lat},{city.lon}",
    theme_data=theme,
    sizes={SIZES},
    dpi={style.dpi},
    output_dir="{out_dir}",
    distance={distance},
    city_name="{city.display_city or city.city}",
    state_name="{city.display_subtitle or city.state}",
    city_slug="{city.slug}",
    force=False,
)
gc.collect()
print("DONE")
"""
    result = subprocess.run(
        [PYTHON, "-c", script], cwd=PROJECT_ROOT,
        timeout=style.render_timeout, capture_output=True, text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"  STDERR: {result.stderr[-500:]}")
    return result.returncode == 0


RENDERERS = {
    "classic": render_city_classic,
    "florence": render_city_florence,
    "blueprint": render_city_blueprint,
    "monomap": render_city_monomap,
}


def render_city(city: CityListing, style: StyleConfig, out_dir: str) -> bool:
    """Dispatch to the correct renderer for this style."""
    renderer_fn = RENDERERS[style.renderer]
    return renderer_fn(city, style, out_dir)


# ── Mockup generation ─────────────────────────────────────────────────────────

def generate_mockups(city: CityListing, style: StyleConfig, out_dir: str) -> list[str]:
    """Generate mockups for a city's renders. Returns list of mockup paths."""
    from PIL import Image
    from etsy.mockup_composer import (
        ALL_MOCKUPS, LIFESTYLE_MOCKUPS, MockupDef,
        get_smart_object_slots, fit_to_slot,
    )
    from psd_tools import PSDImage

    mockup_paths: list[str] = []
    slug = city.slug

    # Use ALL_MOCKUPS for digital-shared images
    for mockup_def in ALL_MOCKUPS + LIFESTYLE_MOCKUPS:
        out_name = f"{slug}_{mockup_def.short_name}.jpg"
        out_path = os.path.join(out_dir, out_name)

        if os.path.exists(out_path):
            mockup_paths.append(out_path)
            continue

        # Find the best render for this mockup's required size
        render_path = None
        for try_size in [mockup_def.render_size, "24x36", "18x24", "16x20"]:
            candidate = os.path.join(out_dir, f"{slug}_{try_size}.png")
            if os.path.exists(candidate):
                render_path = candidate
                break

        if render_path is None:
            continue

        # Load PSD and compose
        try:
            psd_filename = mockup_def.filename
            if Path(psd_filename).is_absolute():
                psd_path = Path(psd_filename)
            else:
                from etsy.mockup_composer import MOCKUP_DIR
                psd_path = MOCKUP_DIR / psd_filename

            psd = PSDImage.open(str(psd_path))
            base = psd.composite().convert("RGBA")

            if mockup_def.use_smart_object_bounds:
                slots = get_smart_object_slots(psd)
            else:
                slots = list(mockup_def.slots)

            if not slots:
                continue

            city_render = Image.open(render_path).convert("RGBA")

            # For multi-slot mockups, use the same render for all slots (filler)
            for i, slot in enumerate(slots):
                fitted = fit_to_slot(city_render, slot)
                base.paste(fitted, (slot.left, slot.top), fitted)

            base.convert("RGB").save(out_path, "JPEG", quality=95)
            mockup_paths.append(out_path)
        except Exception as e:
            print(f"    Mockup {mockup_def.short_name} failed: {e}")

    return mockup_paths


# ── Detail crop ───────────────────────────────────────────────────────────────

def generate_detail_crop(city: CityListing, out_dir: str) -> str | None:
    """Generate a detail crop from the 16x20 render."""
    from PIL import Image

    src = os.path.join(out_dir, f"{city.slug}_16x20.png")
    if not os.path.exists(src):
        return None

    out_path = os.path.join(out_dir, f"{city.slug}_detail_crop.jpg")
    if os.path.exists(out_path):
        return out_path

    img = Image.open(src).convert("RGB")
    w, h = img.size
    crop_size = int(min(w, h) * 0.35)
    cx, cy = int(w * 0.45), int(h * 0.38)
    left = max(0, cx - crop_size // 2)
    top = max(0, cy - crop_size // 2)

    detail = img.crop((left, top, left + crop_size, top + crop_size))
    detail = detail.resize((2000, 2000), Image.LANCZOS)
    detail.save(out_path, quality=92)
    return out_path


# ── Gelato CSV ────────────────────────────────────────────────────────────────

def generate_gelato_csv(
    city: CityListing, style: StyleConfig, listing_title: str,
    listing_id: int, out_dir: str,
) -> str:
    """Generate Gelato import CSV for a city listing."""
    out_path = os.path.join(out_dir, "gelato_import.csv")

    formats = [
        ("Unframed Print", "unframed", "UNF"),
        ("Framed - Black", "framed_black", "FBK"),
        ("Framed - White", "framed_white", "FWH"),
    ]

    rows = []
    for fmt_display, fmt_key, fmt_code in formats:
        for size in SIZES:
            sku = f"{style.sku_prefix}-{city.slug.upper()}-{fmt_code}-{size.upper()}"
            product_uid = GELATO_UIDS[fmt_key][size]
            rows.append({
                "Product Title": listing_title,
                "Product ID": str(listing_id),
                "Variant Title": f"Format {fmt_display}, Size {size}",
                "Variant Option #1 Name": "Format",
                "Variant Option #1 Value": fmt_display,
                "Variant Option #2 Name": "Size",
                "Variant Option #2 Value": size,
                "Product UID": product_uid,
                "File URL": "",  # Filled after Dropbox upload
                "Production Partners": "Printed and shipped by our professional print partner",
                "SKU": sku,
            })

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)

    return out_path


# ── Etsy listing creation ─────────────────────────────────────────────────────

def create_etsy_listing(
    city: CityListing, style: StyleConfig, out_dir: str,
    image_paths: list[str],
) -> int | None:
    """Create Etsy draft listing with images and variants. Returns listing_id."""
    try:
        from etsy.api_client import EtsyClient
        from etsy.etsy_lister import create_full_listing

        text = generate_listing_text(city, style)
        client = EtsyClient()

        result = create_full_listing(
            client=client,
            title=text["title"],
            description=text["description"],
            tags=text["tags"],
            style=style,
            image_paths=image_paths,
        )

        return result["listing_id"]
    except Exception as e:
        print(f"    Etsy API error: {e}")
        return None


# ── Main pipeline ─────────────────────────────────────────────────────────────

def process_city(
    city: CityListing,
    style: StyleConfig,
    render_only: bool = False,
    skip_etsy: bool = False,
    dry_run: bool = False,
) -> bool:
    """Full pipeline for one city × style."""
    slug = city.slug
    style_suffix = {
        "classic": "", "florence": "_florence",
        "blueprint": "_blueprint", "monomap": "_monomap",
    }[style.name]
    out_dir = os.path.join("etsy", "renders", f"{slug}{style_suffix}")
    os.makedirs(out_dir, exist_ok=True)

    display = city.display_city or city.city
    print(f"\n{'='*60}")
    print(f"  {display} — {style.display_name}")
    print(f"  Output: {out_dir}/")
    print(f"{'='*60}")

    if dry_run:
        text = generate_listing_text(city, style)
        print(f"  Title: {text['title']}")
        print(f"  Tags: {text['tags'][:5]}...")
        print(f"  Variants: {len(style.variants)}")
        print(f"  DRY RUN — skipping render + API")
        return True

    # 1. Render all sizes
    print(f"\n  [1/5] Rendering {len(SIZES)} sizes...")
    all_exist = all(
        os.path.exists(os.path.join(out_dir, f"{slug}_{s}.png"))
        for s in SIZES
    )
    if all_exist:
        print(f"    All sizes exist, skipping render")
    else:
        success = render_city(city, style, out_dir)
        if not success:
            print(f"    RENDER FAILED")
            return False

    if render_only:
        print(f"  Render-only mode — done.")
        return True

    # 2. Generate detail crop
    print(f"  [2/5] Detail crop...")
    detail_path = generate_detail_crop(city, out_dir)

    # 3. Generate mockups
    print(f"  [3/5] Mockups...")
    mockup_paths = generate_mockups(city, style, out_dir)
    print(f"    {len(mockup_paths)} mockups generated")

    # 4. Collect images for upload (mockups + detail, ranked)
    image_paths = mockup_paths[:9]  # Max 9 mockups
    if detail_path:
        image_paths.append(detail_path)  # Rank 10 = detail

    # 5. Generate listing text
    print(f"  [4/5] Listing text...")
    text = generate_listing_text(city, style)
    print(f"    Title: {text['title'][:70]}...")

    # Save listing text to file
    text_path = os.path.join(out_dir, f"{slug}_listing.txt")
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(f"TITLE\n{text['title']}\n\n")
        f.write(f"TAGS\n{', '.join(text['tags'])}\n\n")
        f.write(f"DESCRIPTION\n{text['description']}\n")

    if skip_etsy:
        print(f"  [5/5] Skipping Etsy API (--skip-etsy)")
    else:
        # 6. Create Etsy listing
        print(f"  [5/5] Creating Etsy draft...")
        listing_id = create_etsy_listing(city, style, out_dir, image_paths)
        if listing_id:
            print(f"    Listing created: {listing_id}")

            # 7. Generate Gelato CSV
            csv_path = generate_gelato_csv(city, style, text["title"], listing_id, out_dir)
            print(f"    Gelato CSV: {csv_path}")
        else:
            print(f"    Etsy listing creation failed — Gelato CSV skipped")

    return True


# ── CLI ───────────────────────────────────────────────────────────────────────

def find_city(name: str) -> CityListing | None:
    """Find a city by name or slug (case-insensitive)."""
    name_lower = name.lower().replace(" ", "_")
    for city in CITIES:
        if city.slug == name_lower or city.city.lower() == name.lower():
            return city
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Universal batch pipeline — render + list any city × style",
    )
    parser.add_argument("--city", action="append", help="City name(s) — omit for all")
    parser.add_argument("--style", required=True, help="Style name or 'all'")
    parser.add_argument("--render-only", action="store_true", help="Render only, no mockups/API")
    parser.add_argument("--skip-etsy", action="store_true", help="Skip Etsy API calls")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--resume", action="store_true", help="Skip already-completed cities")
    parser.add_argument("--start-from", help="Start from this city (skip earlier)")
    parser.add_argument("--limit", type=int, help="Max cities to process")
    args = parser.parse_args()

    # Resolve styles
    if args.style == "all":
        styles = list(ALL_STYLES.values())
    else:
        styles = [get_style(args.style)]

    # Resolve cities
    if args.city:
        cities = []
        for name in args.city:
            city = find_city(name)
            if city:
                cities.append(city)
            else:
                print(f"WARNING: City '{name}' not found, skipping")
    else:
        cities = list(CITIES)

    # Start-from filter
    if args.start_from:
        start_slug = args.start_from.lower().replace(" ", "_")
        found = False
        filtered = []
        for city in cities:
            if city.slug == start_slug:
                found = True
            if found:
                filtered.append(city)
        cities = filtered

    # Limit
    if args.limit:
        cities = cities[:args.limit]

    # Resume filter
    progress = load_progress() if args.resume else {}

    total = len(cities) * len(styles)
    done = 0
    failed = 0

    print(f"\n{'='*60}")
    print(f"  Universal Batch Pipeline")
    print(f"  {len(cities)} cities x {len(styles)} styles = {total} listings")
    print(f"{'='*60}")

    for style in styles:
        for city in cities:
            key = progress_key(city, style)

            if args.resume and progress.get(key) == "done":
                print(f"\n  SKIP (already done): {city.city} — {style.display_name}")
                done += 1
                continue

            success = process_city(
                city, style,
                render_only=args.render_only,
                skip_etsy=args.skip_etsy,
                dry_run=args.dry_run,
            )

            if success:
                done += 1
                progress[key] = "done"
                save_progress(progress)
            else:
                failed += 1
                progress[key] = "failed"
                save_progress(progress)

    print(f"\n{'='*60}")
    print(f"  Complete: {done}/{total} done, {failed} failed")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify it parses and shows help**

Run: `python scripts/batch_universal.py --help`

- [ ] **Step 3: Test dry-run with one city**

Run: `python scripts/batch_universal.py --city "Nashville" --style blueprint --dry-run`
Expected: Shows title, tags, variant count, no actual rendering

- [ ] **Step 4: Test render-only with one city**

Run: `python scripts/batch_universal.py --city "Nashville" --style blueprint --render-only`
Expected: Renders 5 sizes to `etsy/renders/nashville_blueprint/`, no Etsy API calls

- [ ] **Step 5: Commit**

```bash
git add scripts/batch_universal.py
git commit -m "feat: add universal batch pipeline — render + list any city × style"
```

---

### Task 5: Integration Test — Full Pipeline

**Files:**
- No new files — tests the end-to-end flow

- [ ] **Step 1: Run full pipeline for one city with skip-etsy**

Run: `python scripts/batch_universal.py --city "Nashville" --style blueprint --skip-etsy`
Expected:
- Renders 5 sizes to `etsy/renders/nashville_blueprint/`
- Generates detail crop
- Generates mockups (7 flat + 3 lifestyle)
- Generates listing text file
- Skips Etsy API

- [ ] **Step 2: Verify output folder contents**

Run: `ls etsy/renders/nashville_blueprint/`
Expected: `nashville_8x10.png`, `nashville_11x14.png`, `nashville_16x20.png`, `nashville_18x24.png`, `nashville_24x36.png`, `nashville_detail_crop.jpg`, mockup JPGs, `nashville_listing.txt`

- [ ] **Step 3: Run full pipeline with Etsy API (one city)**

Run: `python scripts/batch_universal.py --city "Nashville" --style blueprint`
Expected: Creates Etsy draft listing + uploads images + sets 20 variants + generates Gelato CSV

- [ ] **Step 4: Verify on Etsy dashboard**

Check that listing appears as draft with correct title, images, and variant pricing

- [ ] **Step 5: Commit integration test results**

```bash
git commit -m "test: verify universal batch pipeline end-to-end for blueprint/Nashville"
```

---

### Task 6: Multi-City Batch Test

- [ ] **Step 1: Run batch for 3 Blueprint cities**

Run: `python scripts/batch_universal.py --city "Nashville" --city "Chicago" --city "Amsterdam" --style blueprint --skip-etsy`

- [ ] **Step 2: Verify all 3 output folders**

- [ ] **Step 3: Test resume functionality**

Run the same command again with `--resume`. Should skip all 3 cities (already done).

- [ ] **Step 4: Test with Florence style**

Run: `python scripts/batch_universal.py --city "Nashville" --style florence --skip-etsy`

- [ ] **Step 5: Commit**

```bash
git commit -m "test: verify multi-city batch and resume for blueprint and florence"
```
