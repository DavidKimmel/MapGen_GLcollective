"""Regenerate MonoMap mockups with color variety.

Rotates hero colors across cities (navy/terracotta/forest) so the shop
page has visual diversity. Single-frame mockups use the hero color,
multi-frame mockups mix all 3 colors.

Requires: batch_monomap_colors.py to have completed (terracotta + forest
renders at 24x36 and 18x24 for each city).

Usage:
    python scripts/regenerate_monomap_mockups.py                # All cities
    python scripts/regenerate_monomap_mockups.py --city chicago  # One city
    python scripts/regenerate_monomap_mockups.py --dry-run       # Preview assignments
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from PIL import Image
from psd_tools import PSDImage

from etsy.city_list import ALL_CITIES, CityListing
from etsy.mockup_composer import (
    ALL_MOCKUPS, LIFESTYLE_MOCKUPS, EXTENDED_LIFESTYLE_MOCKUPS,
    MOCKUP_DIR, MockupDef,
    get_smart_object_slots, fit_to_slot,
)

RENDERS_DIR = Path("etsy/renders")

# Hero color rotation — cycle through 3 colors
HERO_COLORS = ["navy", "terracotta", "forest"]

# All MonoMap colors with hex values (for filler lookup)
MONO_COLORS = {
    "navy": "#1C3D6E",
    "terracotta": "#B5553A",
    "forest": "#2A5A2A",
    "charcoal": "#4A4A4A",
    "dusty_rose": "#A35580",
    "black": "#1A1A1A",
}

# Filler cities for multi-frame mockups — each in a DIFFERENT color
# These must have all 3 color renders available
FILLER_POOL = [
    ("chicago", "navy"),
    ("nashville", "terracotta"),
    ("berlin", "forest"),
    ("paris", "navy"),
    ("pittsburgh", "terracotta"),
    ("amsterdam", "forest"),
    ("washington_dc", "navy"),
    ("rome", "terracotta"),
]


def get_hero_color(city_slug: str) -> str:
    """Deterministic hero color based on alphabetical position."""
    # Sort all city slugs, find index, rotate through colors
    all_slugs = sorted(c.slug for c in ALL_CITIES)
    try:
        idx = all_slugs.index(city_slug)
    except ValueError:
        idx = 0
    return HERO_COLORS[idx % len(HERO_COLORS)]


def find_mono_render(city_slug: str, color: str, size: str) -> Path | None:
    """Find a MonoMap render for a city at a specific color and size."""
    city_dir = RENDERS_DIR / f"{city_slug}_monomap"

    # Color-suffixed render (from extra colors batch)
    color_path = city_dir / f"{city_slug}_{color}_{size}.png"
    if color_path.exists():
        return color_path

    # Navy renders from main batch have no color suffix
    if color == "navy":
        navy_path = city_dir / f"{city_slug}_{size}.png"
        if navy_path.exists():
            return navy_path

    # Check shared MonoMap folder (from earlier sample renders)
    shared_path = RENDERS_DIR / "MonoMap" / color / f"{city_slug}_{size}.png"
    if shared_path.exists():
        return shared_path

    return None


def get_fillers(featured_slug: str, featured_color: str,
                render_size: str, count: int) -> list[tuple[str, Path]]:
    """Get filler city renders in different colors from the featured city."""
    fillers: list[tuple[str, Path]] = []
    used_slugs = {featured_slug}

    for filler_slug, filler_color in FILLER_POOL:
        if filler_slug in used_slugs:
            continue
        # Try to use a DIFFERENT color than the featured
        if filler_color == featured_color:
            # Swap to a different color
            alt_colors = [c for c in HERO_COLORS if c != featured_color]
            found = False
            for alt in alt_colors:
                path = find_mono_render(filler_slug, alt, render_size)
                if path:
                    fillers.append((filler_slug, path))
                    used_slugs.add(filler_slug)
                    found = True
                    break
            if not found:
                # Fall back to whatever color is available
                path = find_mono_render(filler_slug, filler_color, render_size)
                if path:
                    fillers.append((filler_slug, path))
                    used_slugs.add(filler_slug)
        else:
            path = find_mono_render(filler_slug, filler_color, render_size)
            if path:
                fillers.append((filler_slug, path))
                used_slugs.add(filler_slug)

        if len(fillers) >= count:
            break

    return fillers


def compose_mockup(
    mockup_def: MockupDef,
    featured_render: Image.Image,
    filler_renders: list[Image.Image],
    output_path: Path,
) -> bool:
    """Compose a single mockup with featured + filler renders."""
    if Path(mockup_def.filename).is_absolute():
        psd_path = Path(mockup_def.filename)
    else:
        psd_path = MOCKUP_DIR / mockup_def.filename

    if not psd_path.exists():
        return False

    psd = PSDImage.open(str(psd_path))
    base = psd.composite().convert("RGBA")

    if mockup_def.use_smart_object_bounds:
        slots = get_smart_object_slots(psd)
    else:
        slots = list(mockup_def.slots)

    if not slots:
        return False

    filler_idx = 0
    for i, slot in enumerate(slots):
        if i == mockup_def.featured_slot:
            fitted = fit_to_slot(featured_render, slot)
        else:
            if filler_idx < len(filler_renders):
                fitted = fit_to_slot(filler_renders[filler_idx], slot)
                filler_idx += 1
            else:
                fitted = fit_to_slot(featured_render, slot)
        base.paste(fitted, (slot.left, slot.top), fitted)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(str(output_path), "JPEG", quality=95)
    return True


def regenerate_city(city: CityListing, dry_run: bool = False) -> bool:
    """Regenerate all mockups for one city with color-varied hero."""
    slug = city.slug
    hero_color = get_hero_color(slug)
    out_dir = RENDERS_DIR / f"{slug}_monomap"

    if not out_dir.exists():
        print(f"  No render dir: {out_dir}")
        return False

    # Find hero renders
    hero_24 = find_mono_render(slug, hero_color, "24x36")
    hero_18 = find_mono_render(slug, hero_color, "18x24")

    if not hero_24:
        # Fall back to navy if hero color not yet rendered
        hero_24 = find_mono_render(slug, "navy", "24x36")
        hero_color_actual = "navy"
    else:
        hero_color_actual = hero_color

    if not hero_18:
        hero_18 = find_mono_render(slug, "navy", "18x24")

    if not hero_24 or not hero_18:
        print(f"  Missing renders for {slug} (hero={hero_color})")
        return False

    if dry_run:
        print(f"  Hero: {hero_color_actual}")
        return True

    # Load ALL 3 color renders for this city (for single-frame variety)
    color_renders: dict[str, dict[str, Image.Image]] = {}
    for color in ["navy", "terracotta", "forest"]:
        r24 = find_mono_render(slug, color, "24x36")
        r18 = find_mono_render(slug, color, "18x24")
        if r24 and r18:
            color_renders[color] = {
                "24x36": Image.open(str(r24)).convert("RGBA"),
                "18x24": Image.open(str(r18)).convert("RGBA"),
            }
    available_colors = list(color_renders.keys())
    print(f"  Colors loaded: {available_colors}")

    if not available_colors:
        print(f"  No color renders found for {slug}")
        return False

    # Get fillers for multi-frame mockups
    fillers_24 = get_fillers(slug, hero_color_actual, "24x36", 3)
    fillers_18 = get_fillers(slug, hero_color_actual, "18x24", 3)
    filler_24_imgs = [Image.open(str(p)).convert("RGBA") for _, p in fillers_24]
    filler_18_imgs = [Image.open(str(p)).convert("RGBA") for _, p in fillers_18]

    # Separate single-frame vs multi-frame mockups
    all_mockups = ALL_MOCKUPS + LIFESTYLE_MOCKUPS + EXTENDED_LIFESTYLE_MOCKUPS
    single_frame = [m for m in all_mockups if len(m.slots) <= 1 and m.featured_slot == 0
                    and m.short_name not in ("2frames", "cls4", "framepsd")]
    multi_frame = [m for m in all_mockups if m not in single_frame]

    generated = 0

    # Single-frame mockups: CYCLE through colors so each shows a different one
    for i, mockup_def in enumerate(single_frame):
        color = available_colors[i % len(available_colors)]
        size_key = mockup_def.render_size if mockup_def.render_size in ("24x36", "18x24") else "24x36"
        hero_img = color_renders[color].get(size_key, color_renders[color]["24x36"])

        out_path = out_dir / f"{slug}_{mockup_def.short_name}.jpg"
        ok = compose_mockup(mockup_def, hero_img, [], out_path)
        if ok:
            generated += 1

    # Multi-frame mockups: use hero color for featured slot, fillers for others
    hero_24_img = color_renders.get(hero_color_actual, color_renders[available_colors[0]])["24x36"]
    hero_18_img = color_renders.get(hero_color_actual, color_renders[available_colors[0]])["18x24"]

    for mockup_def in multi_frame:
        if mockup_def.render_size == "18x24":
            hero_img = hero_18_img
            filler_imgs = filler_18_imgs
        else:
            hero_img = hero_24_img
            filler_imgs = filler_24_imgs

        out_path = out_dir / f"{slug}_{mockup_def.short_name}.jpg"
        ok = compose_mockup(mockup_def, hero_img, filler_imgs, out_path)
        if ok:
            generated += 1

    print(f"  Generated {generated} mockups ({len(single_frame)} single, {len(multi_frame)} multi)")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate MonoMap mockups with color variety")
    parser.add_argument("--city", help="Single city slug")
    parser.add_argument("--dry-run", action="store_true", help="Preview color assignments")
    args = parser.parse_args()

    cities = ALL_CITIES
    if args.city:
        cities = [c for c in ALL_CITIES if c.slug == args.city]
        if not cities:
            print(f"City not found: {args.city}")
            return

    if args.dry_run:
        print(f"{'City':<25} {'Hero Color':<15}")
        print("-" * 40)
        color_counts: dict[str, int] = {}
        for city in sorted(cities, key=lambda c: c.slug):
            hero = get_hero_color(city.slug)
            color_counts[hero] = color_counts.get(hero, 0) + 1
            print(f"{city.slug:<25} {hero:<15}")
        print(f"\nDistribution: {color_counts}")
        return

    total = len(cities)
    done = 0
    failed = 0

    print(f"{'=' * 60}")
    print(f"  Regenerating MonoMap mockups: {total} cities")
    print(f"  Hero rotation: {HERO_COLORS}")
    print(f"{'=' * 60}\n")

    for city in cities:
        done += 1
        print(f"\n[{done}/{total}] {city.city} ({city.slug})")
        ok = regenerate_city(city, dry_run=False)
        if not ok:
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"  Complete: {done - failed}/{total} done, {failed} failed")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
