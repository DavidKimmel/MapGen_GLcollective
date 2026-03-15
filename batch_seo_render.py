"""Batch render 20 cities — all 5 sizes + detail crop + size comparison.

Renders unfinished Tier 1-3 cities + new Tier 4 SEO expansion cities.
7 images per city: 5 poster sizes (300 DPI) + detail crop + size comparison.

Usage:
    python batch_seo_render.py
    python batch_seo_render.py --start-from "Paris"   # Resume from a specific city
"""

import argparse
import os
import sys
import time

from etsy.batch_etsy_render import render_etsy_city, RENDERS_DIR
from etsy.city_list import ALL_CITIES, get_cities_by_tier
from etsy.image_composer import create_detail_crop, create_size_comparison

SIZES = ["8x10", "11x14", "16x20", "18x24", "24x36"]


def get_cities_to_render():
    """Get the 20 cities that need rendering."""
    cities = []

    # Unrendered Tier 1-3 cities
    for c in ALL_CITIES:
        if c.tier <= 3:
            check = os.path.join(RENDERS_DIR, c.slug, f"{c.slug}_16x20.png")
            if not os.path.exists(check):
                cities.append(c)

    # All Tier 4 cities
    cities.extend(get_cities_by_tier(4))

    return cities


def render_city_full(city, force=False):
    """Render all 5 sizes + detail crop + size comparison for a city."""
    t0 = time.time()
    city_dir = os.path.join(RENDERS_DIR, city.slug)
    os.makedirs(city_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  {city.city}, {city.state} ({city.country})")
    print(f"  Distance: {city.distance}m | Slug: {city.slug}")
    print(f"{'='*60}")

    # Render all 5 sizes
    for size in SIZES:
        print(f"\n  --- {size} ---")
        result = render_etsy_city(city, force=force, size=size)
        if result["status"] == "ok":
            print(f"  OK ({result['time']}, {result['size_mb']} MB)")
        elif result["status"] == "skipped":
            print(f"  SKIPPED — {result['message']}")
        else:
            print(f"  ERROR — {result.get('error', 'unknown')}")

    # Generate listing images (needs 16x20 render)
    print(f"\n  --- Listing images ---")
    create_detail_crop(city.slug)
    create_size_comparison(city.slug)

    elapsed = time.time() - t0
    print(f"\n  City complete: {elapsed:.0f}s total")
    return elapsed


def main():
    parser = argparse.ArgumentParser(description="Batch SEO render — 20 cities x 7 images")
    parser.add_argument("--start-from", default=None,
                        help="Resume from a specific city name")
    parser.add_argument("--force", action="store_true",
                        help="Re-render even if files exist")
    args = parser.parse_args()

    cities = get_cities_to_render()
    print(f"\nSEO Batch Render — {len(cities)} cities x 7 images = {len(cities)*7} files")
    print(f"Sizes: {', '.join(SIZES)}")
    print(f"DPI: 300 | Theme: 37th_parallel\n")

    # Optional resume point
    if args.start_from:
        start_lower = args.start_from.lower()
        skip_until = True
        filtered = []
        for c in cities:
            if c.city.lower() == start_lower:
                skip_until = False
            if not skip_until:
                filtered.append(c)
        if not filtered:
            print(f"City '{args.start_from}' not found in render list")
            sys.exit(1)
        print(f"Resuming from {args.start_from} ({len(filtered)} cities remaining)\n")
        cities = filtered

    total_time = 0
    for i, city in enumerate(cities, 1):
        print(f"\n[{i}/{len(cities)}]", end="")
        elapsed = render_city_full(city, force=args.force)
        total_time += elapsed

    print(f"\n{'='*60}")
    print(f"ALL DONE! {len(cities)} cities, {len(cities)*7} images")
    print(f"Total time: {total_time/60:.1f} minutes")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
