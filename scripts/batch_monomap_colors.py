"""Render MonoMap cities in additional colors for mockup variety.

Each city gets terracotta + forest at 24x36 and 18x24 (mockup sizes).
Navy already exists from the main batch. Saves alongside existing renders
with color-suffixed filenames.

Usage:
    python scripts/batch_monomap_colors.py                    # All cities
    python scripts/batch_monomap_colors.py --city chicago     # One city
    python scripts/batch_monomap_colors.py --color terracotta # One color only
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from etsy.city_list import ALL_CITIES, CityListing
from etsy.style_config import get_city_extent, MONOMAP

PYTHON = sys.executable
RENDERS_DIR = Path("etsy/renders")

# Colors to render (navy already exists from main batch)
EXTRA_COLORS: dict[str, str] = {
    "terracotta": "#B5553A",
    "forest": "#2A5A2A",
}

# Sizes needed for mockups
MOCKUP_SIZES = ["24x36", "18x24"]


def render_city_color(city: CityListing, color_name: str, color_hex: str) -> bool:
    """Render one city in one color at mockup sizes via subprocess."""
    out_dir = RENDERS_DIR / f"{city.slug}_monomap"
    out_dir.mkdir(parents=True, exist_ok=True)

    radius = get_city_extent(city.slug, MONOMAP)
    display_city = city.display_city or city.city
    display_state = city.display_subtitle or city.state

    # Check which sizes still need rendering
    sizes_needed = []
    for size in MOCKUP_SIZES:
        out_path = out_dir / f"{city.slug}_{color_name}_{size}.png"
        if out_path.exists():
            print(f"    {color_name} {size} exists, skipping")
        else:
            sizes_needed.append(size)

    if not sizes_needed:
        return True

    # Use forward slashes for subprocess path safety on Windows
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
    sizes={sizes_needed},
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
    stdout = result.stdout.strip()
    if stdout:
        # Print last few lines
        for line in stdout.split("\n")[-3:]:
            print(f"    {line}")
    if result.returncode != 0:
        print(f"    ERROR: {result.stderr[-300:]}")
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Render MonoMap extra colors")
    parser.add_argument("--city", help="Single city slug")
    parser.add_argument("--color", choices=list(EXTRA_COLORS.keys()),
                        help="Single color only")
    args = parser.parse_args()

    # Filter cities
    cities = ALL_CITIES
    if args.city:
        cities = [c for c in ALL_CITIES if c.slug == args.city]
        if not cities:
            print(f"City not found: {args.city}")
            return

    # Filter colors
    colors = EXTRA_COLORS
    if args.color:
        colors = {args.color: EXTRA_COLORS[args.color]}

    total = len(cities) * len(colors)
    done = 0
    failed = 0

    print(f"{'=' * 60}")
    print(f"  MonoMap Extra Colors: {len(cities)} cities × {len(colors)} colors = {total} jobs")
    print(f"  Sizes per job: {MOCKUP_SIZES}")
    print(f"{'=' * 60}\n")

    for city in cities:
        for color_name, color_hex in colors.items():
            done += 1
            print(f"[{done}/{total}] {city.city} — {color_name}")
            start = time.time()
            ok = render_city_color(city, color_name, color_hex)
            elapsed = time.time() - start
            if ok:
                print(f"    Done ({elapsed:.0f}s)")
            else:
                failed += 1
                print(f"    FAILED ({elapsed:.0f}s)")

    print(f"\n{'=' * 60}")
    print(f"  Complete: {done - failed}/{total} done, {failed} failed")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
