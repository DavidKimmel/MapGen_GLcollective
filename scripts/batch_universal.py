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

from etsy.city_list import ALL_CITIES as CITIES, CityListing
from etsy.style_config import (
    ALL_STYLES, StyleConfig, GELATO_UIDS, SHOP_ID, get_style, get_city_extent,
)
from etsy.listing_text import generate_listing_text

PYTHON = sys.executable
SIZES = ["8x10", "11x14", "16x20", "18x24", "24x36"]
PROGRESS_FILE = "etsy/renders/.batch_progress.json"

# Blueprint filler cities for multi-frame mockups (city, color) pairs
# Each pair is a different city in a different Blueprint color
BLUEPRINT_FILLERS: list[tuple[str, str]] = [
    ("chicago", "navy"),
    ("berlin", "forest"),
    ("paris", "charcoal"),
    ("amsterdam", "terracotta"),
]

# Blueprint color display names (order matches PSD4 grid: TL, TR, BL, BR)
BLUEPRINT_COLORS: list[tuple[str, str]] = [
    ("navy", "Navy"),
    ("forest", "Forest"),
    ("terracotta", "Terracotta"),
    ("charcoal", "Charcoal"),
]

# MonoMap color display names (6 total, pick 4 for PSD4: TL, TR, BL, BR)
MONOMAP_ALL_COLORS: list[tuple[str, str]] = [
    ("charcoal", "Charcoal"),
    ("navy", "Navy"),
    ("forest", "Forest"),
    ("terracotta", "Terracotta"),
    ("dusty_rose", "Dusty Rose"),
    ("black", "Black"),
]
# Top 4 for PSD4 showcase
MONOMAP_PSD4_COLORS: list[tuple[str, str]] = [
    ("navy", "Navy"),
    ("forest", "Forest"),
    ("terracotta", "Terracotta"),
    ("dusty_rose", "Dusty Rose"),
]

# MonoMap filler cities — different cities × different colors for multi-frame mockups
MONOMAP_FILLERS: list[tuple[str, str]] = [
    ("chicago", "forest"),
    ("berlin", "terracotta"),
    ("paris", "dusty_rose"),
    ("rome", "charcoal"),
]

# Shared color assets — multi-color mockups and swatch grids from CustomMapPack
# These get injected into listings for styles that have color variants
SHARED_COLOR_ASSETS: dict[str, dict[str, str]] = {
    "blueprint": {
        "color_swatch": "etsy/renders/CustomMapPack/blueprint_digital/color_options.jpg",
        "multi_color_3frame": "etsy/renders/CustomMapPack/blueprint_digital/mockup_cls4.jpg",
        "multi_color_2frame": "etsy/renders/CustomMapPack/blueprint_digital/mockup_2frames.jpg",
    },
    "monomap": {
        "color_swatch": "etsy/renders/CustomMapPack/monomap_digital/color_options.jpg",
        "multi_color_3frame": "etsy/renders/CustomMapPack/monomap_digital/mockup_cls4.jpg",
        "multi_color_2frame": "etsy/renders/CustomMapPack/monomap_digital/mockup_2frames.jpg",
    },
}


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
    """Render Blueprint style — master crop approach (same as Florence).

    Renders one master at 24x36 aspect, crops to each size, composes poster.
    """
    color = style.color_name or "terracotta"
    radius = get_city_extent(city.slug, style)
    script = f"""
import sys, os, gc
sys.path.insert(0, os.getcwd())
from engine.blueprint_renderer import render_shaded_map, compose_blueprint_poster, PALETTES
from export.output_sizes import get_size_config
from PIL import Image

color = "{color}"
palette_data = PALETTES[color]
lat, lon = {city.lat}, {city.lon}
out_dir = "{out_dir}"
dpi = {style.dpi}
slug = "{city.slug}"
city_name = "{city.display_city or city.city}"
state_name = "{city.display_subtitle or city.state}"
os.makedirs(out_dir, exist_ok=True)

radius = {radius}
print(f"  Extent: {{radius}}m")

# Render master raw map at 24x36 aspect (tallest ratio = 1.5)
master_raw = os.path.join(out_dir, "_master_raw.png")
render_shaded_map(
    lat=lat, lon=lon, radius=radius,
    palette=palette_data["shades"],
    dpi=dpi, fig_width=24, fig_height=36,
    output_path=master_raw,
)

master_img = Image.open(master_raw).convert("RGB")
master_px_w, master_px_h = master_img.size
print(f"  Master: {{master_px_w}}x{{master_px_h}} px")

# Crop master to each size's aspect ratio then compose poster
for size in {SIZES}:
    out_path = os.path.join(out_dir, f"{{slug}}_{{size}}.png")
    if os.path.exists(out_path):
        print(f"  {{size}} exists, skipping")
        continue

    ps = get_size_config(size)
    target_aspect = ps["height_in"] / ps["width_in"]
    master_aspect = 36 / 24  # 1.5

    if target_aspect < master_aspect:
        crop_h = int(master_px_w * target_aspect)
        y_offset = (master_px_h - crop_h) // 2
        cropped = master_img.crop((0, y_offset, master_px_w, y_offset + crop_h))
    else:
        cropped = master_img

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
    distance = get_city_extent(city.slug, style)
    script = f"""
import sys, os, gc, json
sys.path.insert(0, os.getcwd())
from engine.florence_renderer import render_florence_all_sizes
print(f"  Extent: {distance}m")

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

def _find_style_filler_render(
    style: StyleConfig, city_slug: str, render_size: str,
) -> str | None:
    """Find a same-style filler render for multi-frame mockups.

    For Blueprint: looks in BlueprintV3/ for color variants.
    For Florence: looks in FlorenceMap_Posted/.
    For Classic: uses standard find_city_render().
    Falls back across size preferences.
    """
    renders_dir = Path("etsy/renders")

    for try_size in [render_size, "24x36", "18x24", "16x20"]:
        if style.name == "blueprint":
            # Blueprint fillers from BlueprintV3/ — try each color
            for color, _ in BLUEPRINT_COLORS:
                p = renders_dir / "BlueprintV3" / f"{city_slug}_{color}_{try_size}.png"
                if p.exists():
                    return str(p)
            # Also check batch-rendered cities (terracotta default)
            p = renders_dir / f"{city_slug}_blueprint" / f"{city_slug}_{try_size}.png"
            if p.exists():
                return str(p)
        elif style.name == "florence":
            p = renders_dir / "POSTED" / "FlorenceMap_Posted" / f"{city_slug}_florence" / f"{city_slug}_{try_size}.png"
            if p.exists():
                return str(p)
        elif style.name == "monomap":
            # Try all MonoMap colors for this city (fillers should be in different colors)
            for color, _ in MONOMAP_ALL_COLORS:
                p = renders_dir / "MonoMap" / color / f"{city_slug}_{try_size}.png"
                if p.exists():
                    return str(p)
            # Also check batch-rendered monomap cities
            p = renders_dir / f"{city_slug}_monomap" / f"{city_slug}_{try_size}.png"
            if p.exists():
                return str(p)
        else:
            # Classic — check POSTED/DefaultMap_Posted
            p = renders_dir / "POSTED" / "DefaultMap_Posted" / city_slug / f"{city_slug}_{try_size}.png"
            if p.exists():
                return str(p)
    return None


# Same-style filler cities per style (different cities, different colors where applicable)
STYLE_FILLERS: dict[str, list[str]] = {
    "blueprint": ["chicago", "berlin", "paris", "nashville"],
    "florence": ["pittsburgh", "new_orleans", "washington_dc", "amsterdam"],
    "monomap": ["chicago", "berlin", "paris", "nashville"],
    "classic": ["pittsburgh", "new_orleans", "washington_dc", "amsterdam"],
}


def generate_mockups(city: CityListing, style: StyleConfig, out_dir: str) -> list[str]:
    """Generate mockups with same-style filler cities in multi-frame slots.

    Multi-frame mockups show the featured city in the designated slot and
    different filler cities FROM THE SAME STYLE in remaining slots.
    Blueprint fillers come from BlueprintV3/ (correct colors).
    """
    from PIL import Image
    from psd_tools import PSDImage
    from etsy.mockup_composer import (
        ALL_MOCKUPS, LIFESTYLE_MOCKUPS, MOCKUP_DIR,
        get_smart_object_slots, fit_to_slot,
    )

    mockup_paths: list[str] = []
    slug = city.slug

    for mockup_def in ALL_MOCKUPS + LIFESTYLE_MOCKUPS:
        out_name = f"{slug}_{mockup_def.short_name}.jpg"
        out_path = os.path.join(out_dir, out_name)

        if os.path.exists(out_path):
            mockup_paths.append(out_path)
            continue

        # Find featured city render at best available size
        render_path = None
        for try_size in [mockup_def.render_size, "24x36", "18x24", "16x20"]:
            candidate = os.path.join(out_dir, f"{slug}_{try_size}.png")
            if os.path.exists(candidate):
                render_path = candidate
                break
        if render_path is None:
            continue

        try:
            # Resolve PSD path
            if Path(mockup_def.filename).is_absolute():
                psd_path = Path(mockup_def.filename)
            else:
                psd_path = MOCKUP_DIR / mockup_def.filename

            psd = PSDImage.open(str(psd_path))
            base = psd.composite().convert("RGBA")

            if mockup_def.use_smart_object_bounds:
                slots = get_smart_object_slots(psd)
            else:
                slots = list(mockup_def.slots)

            if not slots:
                continue

            city_render = Image.open(render_path).convert("RGBA")

            # Load same-style filler renders for multi-slot mockups
            # For color-variant styles, use explicit (city, color) pairs
            # so each filler is a DIFFERENT color
            filler_renders: list[Image.Image] = []
            if len(slots) > 1:
                if style.name == "monomap":
                    filler_pairs = MONOMAP_FILLERS
                elif style.name == "blueprint":
                    filler_pairs = BLUEPRINT_FILLERS
                else:
                    filler_pairs = [(s,) for s in STYLE_FILLERS.get(style.name, [])]

                renders_dir = Path("etsy/renders")
                for pair in filler_pairs:
                    filler_slug = pair[0]
                    if filler_slug == slug:
                        continue
                    if len(pair) == 2:
                        # Explicit city+color pair — find directly
                        filler_color = pair[1]
                        filler_path = None
                        for try_size in [mockup_def.render_size, "24x36", "18x24", "16x20"]:
                            if style.name == "monomap":
                                p = renders_dir / "MonoMap" / filler_color / f"{filler_slug}_{try_size}.png"
                            elif style.name == "blueprint":
                                p = renders_dir / "BlueprintV3" / f"{filler_slug}_{filler_color}_{try_size}.png"
                            else:
                                p = None
                            if p and p.exists():
                                filler_path = str(p)
                                break
                        # Fallback: batch-rendered default
                        if not filler_path:
                            filler_path = _find_style_filler_render(
                                style, filler_slug, mockup_def.render_size,
                            )
                    else:
                        filler_path = _find_style_filler_render(
                            style, filler_slug, mockup_def.render_size,
                        )

                    if filler_path:
                        filler_renders.append(Image.open(filler_path).convert("RGBA"))
                    if len(filler_renders) >= len(slots) - 1:
                        break

            # Place renders in slots
            filler_idx = 0
            for i, slot in enumerate(slots):
                if i == mockup_def.featured_slot:
                    fitted = fit_to_slot(city_render, slot)
                elif filler_idx < len(filler_renders):
                    fitted = fit_to_slot(filler_renders[filler_idx], slot)
                    filler_idx += 1
                else:
                    fitted = fit_to_slot(city_render, slot)
                base.paste(fitted, (slot.left, slot.top), fitted)

            base.convert("RGB").save(out_path, "JPEG", quality=95)
            mockup_paths.append(out_path)
        except Exception as e:
            print(f"    Mockup {mockup_def.short_name} failed: {e}")

    return mockup_paths


# ── Detail crop ───────────────────────────────────────────────────────────────

def create_labeled_psd4(city: CityListing, style: StyleConfig, out_dir: str) -> str | None:
    """Create PSD4 mockup with city in 4 color variations + labels.

    This is the PRIMARY image for color-variant listings (Blueprint, MonoMap).
    Shows all color options in a 4-frame grid with labels so customers know
    what to request in the personalization field.
    """
    if style.name not in ("blueprint", "monomap"):
        return None

    from PIL import Image, ImageDraw, ImageFont
    from psd_tools import PSDImage
    from etsy.mockup_composer import get_smart_object_slots, fit_to_slot, BEST_DIR

    out_path = os.path.join(out_dir, f"{city.slug}_psd4_labeled.jpg")
    if os.path.exists(out_path):
        return out_path

    slug = city.slug
    renders_dir = Path("etsy/renders")

    # Determine colors and render paths based on style
    if style.name == "blueprint":
        psd4_colors = BLUEPRINT_COLORS
        shared_path = "etsy/renders/BlueprintV3/shared_psd4_labeled.jpg"

        def find_color_render(s: str, color: str) -> Path | None:
            p = renders_dir / "BlueprintV3" / f"{s}_{color}_16x20.png"
            return p if p.exists() else None

    elif style.name == "monomap":
        psd4_colors = MONOMAP_PSD4_COLORS
        shared_path = "etsy/renders/MonoMap/shared_psd4_labeled.jpg"

        def find_color_render(s: str, color: str) -> Path | None:
            for try_size in ["16x20", "24x36", "11x14"]:
                p = renders_dir / "MonoMap" / color / f"{s}_{try_size}.png"
                if p.exists():
                    return p
            return None
    else:
        return None

    # Check if this city has all 4 color renders
    has_all_colors = all(
        find_color_render(slug, color) is not None
        for color, _ in psd4_colors
    )

    if has_all_colors:
        # City-specific PSD4: same city in 4 colors with title + labels
        psd = PSDImage.open(str(BEST_DIR / "PSD.psd"))
        base = psd.composite().convert("RGBA")
        slots = get_smart_object_slots(psd)
        psd_w, psd_h = psd.width, psd.height

        # Slots: 0=BL, 1=TL, 2=BR, 3=TR
        slot_order = [1, 3, 0, 2]  # TL, TR, BL, BR

        for idx, (color_key, _) in enumerate(psd4_colors):
            slot = slots[slot_order[idx]]
            render_path = find_color_render(slug, color_key)
            city_render = Image.open(str(render_path)).convert("RGBA")
            fitted = fit_to_slot(city_render, slot)
            base.paste(fitted, (slot.left, slot.top), fitted)

        result = base.convert("RGB")
        draw = ImageDraw.Draw(result)
        font_path = os.path.join("fonts", "Montserrat-Bold.ttf")

        # Title across the top: "Choose Your Color Style"
        title_font = ImageFont.truetype(font_path, 90)
        title_text = "Choose Your Color Style"
        bbox = draw.textbbox((0, 0), title_text, font=title_font)
        title_w = bbox[2] - bbox[0]
        title_h = bbox[3] - bbox[1]
        # Center in the top space (above top row of frames)
        top_space = slots[1].top  # ~559px
        title_y = (top_space - title_h) // 2
        draw.text(
            ((psd_w - title_w) // 2, title_y),
            title_text, fill="#333333", font=title_font,
        )

        # Color labels — just under top row frames, further below bottom row
        label_font = ImageFont.truetype(font_path, 72)
        # Top row labels: below the frame with some breathing room
        top_label_y = slots[1].bottom + 55  # ~1917
        # Bottom row labels: pushed down with more breathing room
        bottom_label_y = slots[0].bottom + 80  # ~3524

        for idx, (_, label) in enumerate(psd4_colors):
            slot = slots[slot_order[idx]]
            bbox = draw.textbbox((0, 0), label, font=label_font)
            label_w = bbox[2] - bbox[0]
            label_h = bbox[3] - bbox[1]
            label_x = slot.left + (slot.width - label_w) // 2

            # Top row (idx 0,1) → just under frames; Bottom row (idx 2,3) → below frames
            if idx < 2:
                label_y = top_label_y
            else:
                label_y = bottom_label_y

            draw.text((label_x, label_y), label, fill="#333333", font=label_font)

        result.save(out_path, "JPEG", quality=95)
        print(f"    PSD4 labeled (city-specific): {out_path}")
    else:
        # Use shared showcase PSD4
        import shutil
        if os.path.exists(shared_path):
            shutil.copy(shared_path, out_path)
            print(f"    PSD4 labeled (shared showcase): {out_path}")
        else:
            print(f"    PSD4: shared showcase not found at {shared_path}")
            return None

    return out_path


def generate_detail_crop(city: CityListing, style: StyleConfig, out_dir: str) -> str | None:
    """Generate detail crop with 'EVERY STREET. EVERY DETAIL.' badge.

    Crops center 40% of map area, scales to 2000x2000, applies the dark
    badge overlay — matching the production pattern used for all published
    Classic and Florence listings (see image_composer._draw_detail_badge).
    """
    from PIL import Image
    from etsy.image_composer import _draw_detail_badge, LISTING_IMAGE_WIDTH, LISTING_IMAGE_HEIGHT

    # Find the 16x20 render in our output directory
    src = os.path.join(out_dir, f"{city.slug}_16x20.png")
    if not os.path.exists(src):
        print(f"    No 16x20 render found for detail crop")
        return None

    out_path = os.path.join(out_dir, f"{city.slug}_detail_crop.jpg")
    if os.path.exists(out_path):
        return out_path

    img = Image.open(src)
    w, h = img.size

    # Map area is top ~76% of poster (bottom ~24% is text/swatch bar)
    # Blueprint has text at TOP (~22%), so adjust for that
    if style.name == "blueprint":
        map_top = int(h * 0.22)
        map_bottom = h
    else:
        map_top = 0
        map_bottom = int(h * 0.76)

    map_h = map_bottom - map_top
    crop_size = int(min(w, map_h) * 0.4)
    cx = w // 2
    cy = map_top + map_h // 2
    left = cx - crop_size // 2
    top = cy - crop_size // 2

    cropped = img.crop((left, top, left + crop_size, top + crop_size))
    result = cropped.resize((LISTING_IMAGE_WIDTH, LISTING_IMAGE_HEIGHT), Image.LANCZOS)
    result = _draw_detail_badge(result)

    os.makedirs(out_dir, exist_ok=True)
    result.save(out_path, "JPEG", quality=92, dpi=(300, 300))
    print(f"    Detail crop with badge: {out_path}")
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
        from etsy.listing_generator import generate_listing

        text = generate_listing(city, style=style.name)
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
    out_dir = out_dir.replace("\\", "/")  # Normalize for subprocess f-strings
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

    # 2. Generate detail crop (with "EVERY STREET. EVERY DETAIL." badge)
    print(f"  [2/5] Detail crop...")
    detail_path = generate_detail_crop(city, style, out_dir)

    # 3. Generate mockups
    print(f"  [3/5] Mockups...")
    mockup_paths = generate_mockups(city, style, out_dir)
    print(f"    {len(mockup_paths)} mockups generated")

    # 3b. For color-variant styles: generate labeled PSD4 (4 colors with labels)
    psd4_labeled = None
    if style.name in ("blueprint", "monomap"):
        print(f"  [3b/5] Labeled PSD4 (color showcase)...")
        psd4_labeled = create_labeled_psd4(city, style, out_dir)

    # 4. Collect images for upload — strategic order (max 10)
    #
    # For Blueprint (4-color):
    #   1. Labeled PSD4 — 4 frames showing all color options with names
    #   2. Color swatch grid (flat square crops with labels)
    #   3. Primary single-frame mockup (Main.psd)
    #   4-7. Single-frame mockups (lifestyle + flat)
    #   8. Detail crop with badge
    #   9-10. More mockups
    #
    # For MonoMap (6-color):
    #   1. Primary mockup
    #   2. Color swatch grid
    #   3-8. Mockups
    #   9. Detail crop
    #   10. Mockup
    #
    # For single-style (classic, florence):
    #   1-8. City mockups
    #   9. Detail crop
    #   10. Another mockup

    image_paths: list[str] = []
    color_assets = SHARED_COLOR_ASSETS.get(style.name, {})

    if style.name in ("blueprint", "monomap") and psd4_labeled:
        # Color-variant style: labeled PSD4 as primary (shows color options with names)
        image_paths.append(psd4_labeled)

        # Color swatch grid (flat reference)
        swatch = color_assets.get("color_swatch", "")
        if os.path.exists(swatch):
            image_paths.append(swatch)

        # Single-frame mockups (skip multi-frame — PSD4 already serves that role)
        for p in mockup_paths:
            if "_psd4." in p or "_cls4." in p or "_2frames." in p:
                continue
            image_paths.append(p)
            if len(image_paths) >= 8:
                break

        # Detail crop with badge
        if detail_path and len(image_paths) < 10:
            image_paths.append(detail_path)

        # Fill remaining slots with any leftover mockups
        for p in mockup_paths:
            if p not in image_paths and len(image_paths) < 10:
                image_paths.append(p)

    elif color_assets:
        # Other color-variant style without PSD4 — fallback
        main_mockup = next((p for p in mockup_paths if "_main." in p), None)
        if main_mockup:
            image_paths.append(main_mockup)

        swatch = color_assets.get("color_swatch", "")
        if os.path.exists(swatch):
            image_paths.append(swatch)

        for p in mockup_paths:
            if p == main_mockup:
                continue
            image_paths.append(p)
            if len(image_paths) >= 9:
                break

        if detail_path and len(image_paths) < 10:
            image_paths.append(detail_path)
    else:
        # Single-style (classic, florence): city mockups + detail
        image_paths = mockup_paths[:9]
        if detail_path:
            image_paths.append(detail_path)

    image_paths = image_paths[:10]  # Hard cap at 10

    # 5. Generate listing text (style-specific generators)
    print(f"  [4/5] Listing text...")
    if style.name == "blueprint":
        from etsy.blueprint_listing import generate_blueprint_listing_text
        listing_txt = generate_blueprint_listing_text(slug, output_dir=out_dir)
    else:
        from etsy.listing_generator import export_listing_text, export_variations_text
        listing_txt = export_listing_text(city, style=style.name, output_dir=out_dir)
        variations_txt = export_variations_text(city, style=style.name, output_dir=out_dir)
    print(f"    Listing text: {listing_txt}")
    if variations_txt:
        print(f"    Variations: {variations_txt}")

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
                if not args.dry_run:
                    progress[key] = "done"
                    save_progress(progress)
            else:
                failed += 1
                if not args.dry_run:
                    progress[key] = "failed"
                    save_progress(progress)

    print(f"\n{'='*60}")
    print(f"  Complete: {done}/{total} done, {failed} failed")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
