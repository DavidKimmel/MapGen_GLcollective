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
