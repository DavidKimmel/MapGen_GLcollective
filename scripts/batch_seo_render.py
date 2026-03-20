"""Batch render cities — all 5 sizes + detail crop + size comparison.

Each city is rendered in a separate subprocess to ensure full memory
release between cities (matplotlib/osmnx graph objects can consume 10GB+
for large cities).

Usage:
    python batch_seo_render.py
    python batch_seo_render.py --start-from "Paris"
    python batch_seo_render.py --city "Barcelona" --force
"""

import argparse
import json
import os
import subprocess
import sys
import time

PYTHON = sys.executable
SIZES = ["8x10", "11x14", "16x20", "18x24", "24x36"]
RENDERS_DIR = os.path.join("etsy", "renders")


def get_cities_to_render():
    """Get cities that need rendering (unrendered Tier 1-3 + all Tier 4-5)."""
    from etsy.city_list import ALL_CITIES, get_cities_by_tier
    cities = []
    for c in ALL_CITIES:
        if c.tier <= 3:
            check = os.path.join(RENDERS_DIR, c.slug, f"{c.slug}_16x20.png")
            if not os.path.exists(check):
                cities.append(c)
    cities.extend(get_cities_by_tier(4))
    cities.extend(get_cities_by_tier(5))
    return cities


def get_all_cities():
    """Get all cities from city_list."""
    from etsy.city_list import ALL_CITIES
    return ALL_CITIES


def render_single_city_subprocess(city_name, force=False):
    """Render one city in a subprocess — full memory isolation.

    Runs a child Python process that renders all 5 sizes + listing images,
    then exits, freeing all memory (graph, matplotlib figures, OSM cache).
    """
    script = f"""
import gc, sys, os, time
sys.path.insert(0, os.getcwd())

from etsy.batch_etsy_render import render_etsy_city, RENDERS_DIR
from etsy.city_list import get_city, ALL_CITIES
from etsy.image_composer import create_detail_crop, create_size_comparison

SIZES = {json.dumps(SIZES)}
force = {"True" if force else "False"}
city_name = {json.dumps(city_name)}

# Find city
city = get_city(city_name)
if not city:
    # Try slug match
    slug = city_name.lower().replace(" ", "_").replace("'", "")
    for c in ALL_CITIES:
        if c.slug == slug:
            city = c
            break
if not city:
    print(f"City not found: {{city_name}}")
    sys.exit(1)

city_dir = os.path.join(RENDERS_DIR, city.slug)
os.makedirs(city_dir, exist_ok=True)

print(f"  {{city.city}}, {{city.state}} ({{city.country}})")
print(f"  Distance: {{city.distance}}m | Slug: {{city.slug}}")

for size in SIZES:
    print(f"\\n  --- {{size}} ---")
    result = render_etsy_city(city, force=force, size=size)
    if result["status"] == "ok":
        print(f"  OK ({{result['time']}}, {{result['size_mb']}} MB)")
    elif result["status"] == "skipped":
        print(f"  SKIPPED — {{result['message']}}")
    else:
        print(f"  ERROR — {{result.get('error', 'unknown')}}")

    # Force garbage collection after each size
    import matplotlib.pyplot as plt
    plt.close("all")
    gc.collect()

# Listing images
print(f"\\n  --- Listing images ---")
create_detail_crop(city.slug)
create_size_comparison(city.slug)

print("\\n__CITY_DONE__")
"""
    t0 = time.time()
    result = subprocess.run(
        [PYTHON, "-c", script],
        cwd=os.getcwd(),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        capture_output=False,
        timeout=3600,  # 1 hour max per city
    )
    elapsed = time.time() - t0
    return result.returncode, elapsed


def main():
    parser = argparse.ArgumentParser(description="Batch SEO render — memory-safe")
    parser.add_argument("--start-from", default=None,
                        help="Resume from a specific city name")
    parser.add_argument("--city", default=None,
                        help="Render a single city")
    parser.add_argument("--force", action="store_true",
                        help="Re-render even if files exist")
    args = parser.parse_args()

    if args.city:
        # Single city mode
        print(f"\nRendering: {args.city}")
        print(f"{'='*60}")
        rc, elapsed = render_single_city_subprocess(args.city, force=args.force)
        status = "OK" if rc == 0 else f"FAILED (exit {rc})"
        print(f"\n{status} — {elapsed/60:.1f} minutes")
        return

    cities = get_cities_to_render()
    print(f"\nSEO Batch Render — {len(cities)} cities x 7 images = {len(cities)*7} files")
    print(f"Sizes: {', '.join(SIZES)}")
    print(f"DPI: 300 | Theme: 37th_parallel")
    print(f"Mode: subprocess per city (memory-safe)\n")

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
    ok_count = 0
    fail_count = 0

    for i, city in enumerate(cities, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(cities)}]")
        print(f"{'='*60}")

        rc, elapsed = render_single_city_subprocess(city.city, force=args.force)
        total_time += elapsed

        if rc == 0:
            ok_count += 1
            print(f"\n  City complete: {elapsed/60:.1f} minutes")
        else:
            fail_count += 1
            print(f"\n  FAILED (exit {rc}) after {elapsed/60:.1f} minutes")

    print(f"\n{'='*60}")
    print(f"ALL DONE! {ok_count} ok, {fail_count} failed")
    print(f"Total time: {total_time/60:.1f} minutes")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
