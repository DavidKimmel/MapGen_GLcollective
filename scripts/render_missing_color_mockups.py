"""Render missing MonoMap colors (black, charcoal, dusty_rose) and compose
one single-frame mockup per color for each city.

Each color gets a different mockup template for visual variety:
  - black     -> frame25  (gold frame + fiddle leaf fig)
  - charcoal  -> frame33  (oak frame + boho shelf)
  - dusty_rose -> frame21 (wood frame + boho plants)

Usage:
    python scripts/render_missing_color_mockups.py                 # All 64 cities
    python scripts/render_missing_color_mockups.py --city austin   # Single city
    python scripts/render_missing_color_mockups.py --mockups-only  # Skip rendering, just compose mockups
"""

from __future__ import annotations

import argparse
import gc
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from PIL import Image

from etsy.city_list import ALL_CITIES, CityListing
from etsy.style_config import get_city_extent, MONOMAP
from etsy.mockup_composer import (
    compose_mockup,
    EXTENDED_LIFESTYLE_MOCKUPS,
    RENDER_DIR,
)

PYTHON = sys.executable
RENDERS_DIR = Path("etsy/renders")

# Colors to render + their hex codes
NEW_COLORS: dict[str, str] = {
    "black": "#1A1A1A",
    "charcoal": "#4A4A4A",
    "dusty_rose": "#A35580",
}

# Each color maps to a different single-frame mockup for variety
# These are lifestyle mockups from the extended set
COLOR_MOCKUP_MAP: dict[str, str] = {
    "black": "frame25",       # gold frame + fiddle leaf fig
    "charcoal": "frame33",    # oak frame + boho shelf
    "dusty_rose": "frame21",  # wood frame + boho plants room
}

# Build lookup from short_name -> MockupDef
MOCKUP_LOOKUP = {m.short_name: m for m in EXTENDED_LIFESTYLE_MOCKUPS}


def get_monomap_cities() -> list[CityListing]:
    """Get all cities that have a monomap folder."""
    slugs: set[str] = set()
    for d in RENDERS_DIR.iterdir():
        if d.is_dir() and d.name.endswith("_monomap"):
            slugs.add(d.name.replace("_monomap", ""))
    return [c for c in ALL_CITIES if c.slug in slugs]


def render_color(city: CityListing, color_name: str, color_hex: str) -> bool:
    """Render one city in one color at 24x36 via subprocess (memory-safe)."""
    out_dir = RENDERS_DIR / f"{city.slug}_monomap"
    out_path = out_dir / f"{city.slug}_{color_name}_24x36.png"

    if out_path.exists():
        print(f"    render exists, skipping")
        return True

    radius = get_city_extent(city.slug, MONOMAP)
    display_city = city.display_city or city.city
    display_state = city.display_subtitle or city.state
    out_dir_str = str(out_dir).replace("\\", "/")

    script = f"""
import sys, os, gc
sys.path.insert(0, os.getcwd())
from engine.florence_renderer import render_florence_all_sizes

theme = {{
    "palette": ["{color_hex}"],
    "bg_color": "#FFFFFF",
    "water_color": "#FFFFFF",
    "street_color": "#FFFFFF",
    "poster_bg": "#FFFFFF",
    "text_color": "{color_hex}",
    "font": "Switzer-Bold.ttf",
}}

render_florence_all_sizes(
    location="{city.lat},{city.lon}",
    theme_data=theme,
    sizes=["24x36"],
    dpi=300,
    output_dir="{out_dir_str}",
    distance={radius},
    city_name="{display_city}",
    state_name="{display_state}",
    city_slug="{city.slug}_{color_name}",
    force=False,
)
gc.collect()
print("DONE")
"""
    result = subprocess.run(
        [PYTHON, "-c", script],
        cwd=PROJECT_ROOT,
        timeout=7200,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    if result.returncode != 0:
        stderr_tail = result.stderr[-300:] if result.stderr else "no stderr"
        print(f"    RENDER ERROR: {stderr_tail}")
        return False
    return True


def compose_color_mockup(city: CityListing, color_name: str) -> bool:
    """Compose a mockup for a specific color render."""
    city_dir = RENDERS_DIR / f"{city.slug}_monomap"
    render_path = city_dir / f"{city.slug}_{color_name}_24x36.png"

    if not render_path.exists():
        print(f"    no 24x36 render for {color_name}, skipping mockup")
        return False

    mockup_name = COLOR_MOCKUP_MAP[color_name]
    mockup_def = MOCKUP_LOOKUP.get(mockup_name)
    if not mockup_def:
        print(f"    mockup template {mockup_name} not found!")
        return False

    out_path = city_dir / f"{city.slug}_{color_name}_{mockup_name}.jpg"
    if out_path.exists():
        print(f"    mockup exists, skipping")
        return True

    try:
        render_img = Image.open(str(render_path)).convert("RGBA")
        # compose_mockup saves to {city_slug}_{mockup_name}.jpg in RENDER_DIR/{city_slug}/
        # But we need it in the _monomap folder with the color prefix
        # So we compose manually using the same logic
        result_path = compose_mockup(mockup_def, f"{city.slug}_monomap", render_img)

        # The composer saves as {slug}_monomap_{mockup_name}.jpg — rename to include color
        expected_name = f"{city.slug}_monomap_{mockup_name}.jpg"
        expected_path = RENDER_DIR / f"{city.slug}_monomap" / expected_name
        if expected_path.exists():
            os.rename(str(expected_path), str(out_path))
            print(f"    -> {out_path.name}")
        elif result_path.exists():
            os.rename(str(result_path), str(out_path))
            print(f"    -> {out_path.name}")
        else:
            print(f"    WARN: composed file not found at expected location")
            return False

        render_img.close()
        gc.collect()
        return True
    except Exception as e:
        print(f"    MOCKUP ERROR: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Render missing MonoMap colors + mockups")
    parser.add_argument("--city", help="Single city slug")
    parser.add_argument("--mockups-only", action="store_true",
                        help="Skip rendering, just compose mockups from existing renders")
    args = parser.parse_args()

    cities = get_monomap_cities()
    if args.city:
        cities = [c for c in cities if c.slug == args.city]
        if not cities:
            print(f"City not found: {args.city}")
            sys.exit(1)

    total_renders = len(cities) * len(NEW_COLORS)
    total_mockups = total_renders

    print(f"{'=' * 60}")
    print(f"  MonoMap Missing Colors: {len(cities)} cities x {len(NEW_COLORS)} colors")
    print(f"  Colors: {', '.join(NEW_COLORS.keys())}")
    print(f"  Mockup templates: {', '.join(f'{c}->{m}' for c, m in COLOR_MOCKUP_MAP.items())}")
    if args.mockups_only:
        print(f"  MODE: mockups only (skip rendering)")
    print(f"{'=' * 60}\n")

    renders_ok = 0
    renders_fail = 0
    mockups_ok = 0
    mockups_fail = 0
    count = 0

    for city in cities:
        for color_name, color_hex in NEW_COLORS.items():
            count += 1
            print(f"[{count}/{total_renders}] {city.city} — {color_name}")

            # Render
            if not args.mockups_only:
                t0 = time.time()
                if render_color(city, color_name, color_hex):
                    renders_ok += 1
                    print(f"    rendered ({time.time() - t0:.0f}s)")
                else:
                    renders_fail += 1
                    continue  # Skip mockup if render failed

            # Compose mockup
            if compose_color_mockup(city, color_name):
                mockups_ok += 1
            else:
                mockups_fail += 1

    print(f"\n{'=' * 60}")
    if not args.mockups_only:
        print(f"  Renders:  {renders_ok} ok, {renders_fail} failed")
    print(f"  Mockups:  {mockups_ok} ok, {mockups_fail} failed")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
