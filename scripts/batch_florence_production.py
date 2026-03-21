"""Full Florence production pipeline — all cities, all sizes, one at a time.

Renders all 5 sizes per city in a subprocess, then generates detail crops
and size comparisons. One city at a time for memory safety.

Usage:
    python scripts/batch_florence_production.py
    python scripts/batch_florence_production.py --start-from "Boston"
    python scripts/batch_florence_production.py --city "Chicago"
    python scripts/batch_florence_production.py --tier 1
"""

import argparse
import json
import os
import subprocess
import sys
import time

PYTHON = sys.executable
THEME = "florence"
SIZES = ["8x10", "11x14", "16x20", "18x24", "24x36"]
DPI = 300
RENDERS_DIR = os.path.join("etsy", "renders")

# Florence-specific overrides: tighter extents, better centering.
# Cities not listed here use default coords from city_list with distance * 0.75.
FLORENCE_OVERRIDES: dict[str, dict] = {
    # --- Tier 1 ---
    "New York": {
        "lat": 40.7580, "lon": -73.9770, "distance": 5500,
        "display_city": "Manhattan", "display_subtitle": "New York",
        "slug": "manhattan",
    },
    "Chicago": {
        "lat": 41.8827, "lon": -87.6353, "distance": 7000,
    },
    "Seattle": {
        "lat": 47.6135, "lon": -122.3420, "distance": 5500,
    },
    "San Francisco": {
        "lat": 37.7749, "lon": -122.4294, "distance": 5500,
    },
    "Washington DC": {"distance": 6500},
    "New Orleans": {"distance": 6000},
    "Nashville": {"distance": 6500},
    "Austin": {"distance": 6500},
    "Portland": {"distance": 6500},
    "Denver": {"distance": 6500},
    # --- Tier 2 ---
    "Boston": {"distance": 6000},
    "Miami": {"distance": 7500},
    "Atlanta": {"distance": 7500},
    "Minneapolis": {"distance": 6000},
    "Pittsburgh": {"distance": 6000},
    "Savannah": {"distance": 5000},
    "Charleston": {"distance": 5000},
    "Asheville": {"distance": 5000},
    "Salt Lake City": {"distance": 6000},
    "Honolulu": {"lat": 21.3069, "lon": -157.8583, "distance": 5000},
    # --- Tier 3 ---
    "Richmond": {"distance": 6000},
    "Chattanooga": {"distance": 5000},
    "Boise": {"distance": 6000},
    "Raleigh": {"distance": 6000},
    "Charlotte": {"distance": 6000},
    # --- Tier 4 (international) ---
    "London": {"distance": 7500},
    "Paris": {"distance": 6000},
    "Tokyo": {"distance": 7500},
    "Rome": {"distance": 6000},
    "Barcelona": {"distance": 6000},
    "Amsterdam": {"distance": 6000},
    "Lisbon": {"distance": 6000},
    "Philadelphia": {"distance": 6000},
    "San Diego": {"distance": 6000},
    "Baltimore": {"distance": 6000},
    # --- Tier 5 (expansion) ---
    "Los Angeles": {"distance": 9000},
    "Houston": {"distance": 7500},
    "San Antonio": {"distance": 6000},
    "Detroit": {"distance": 6000},
    "St. Louis": {"distance": 6000},
    "Cincinnati": {"distance": 5500},
    "Tampa": {"distance": 7500},
    "Milwaukee": {"distance": 6000},
    "Kansas City": {"distance": 6000},
    "Cleveland": {"distance": 6000},
    "Berlin": {"distance": 7500},
    "Dublin": {"distance": 6000},
    "Edinburgh": {"distance": 5500},
    "Prague": {"distance": 6000},
    "Vienna": {"distance": 7500},
    "Copenhagen": {"distance": 6000},
    "Istanbul": {"distance": 9000},
    "Sydney": {"distance": 7500},
    "Florence": {"distance": 4500},
    "Stockholm": {"distance": 6000},
}

# Default distance multiplier for cities without explicit overrides
DEFAULT_DISTANCE_SCALE = 0.75


def render_city_subprocess(city_name: str, force: bool = False) -> tuple[int, float]:
    """Render all 5 sizes for one city in a subprocess."""
    overrides_json = json.dumps(FLORENCE_OVERRIDES.get(city_name, {}))
    sizes_json = json.dumps(SIZES)

    script = f"""
import gc, sys, os, time
sys.path.insert(0, os.getcwd())

from engine.florence_renderer import render_florence_poster
from engine.renderer import load_theme
from etsy.city_list import get_city, ALL_CITIES
from export.output_sizes import get_size_config

city_name = {json.dumps(city_name)}
theme_name = {json.dumps(THEME)}
sizes = {sizes_json}
dpi = {DPI}
renders_dir = {json.dumps(RENDERS_DIR)}
force = {force}
overrides = {overrides_json}
default_scale = {DEFAULT_DISTANCE_SCALE}

# Find city
city = get_city(city_name)
if not city:
    slug = city_name.lower().replace(" ", "_").replace("'", "").replace(".", "")
    for c in ALL_CITIES:
        if c.slug == slug:
            city = c
            break
if not city:
    print(f"City not found: {{city_name}}")
    sys.exit(1)

# Apply overrides
slug = overrides.get("slug", city.slug)
display_city = overrides.get("display_city", city.display_city or city.city)
display_subtitle = overrides.get("display_subtitle", city.display_subtitle or city.state)
lat = overrides.get("lat", city.lat)
lon = overrides.get("lon", city.lon)
base_distance = overrides.get("distance", int(city.distance * default_scale))

city_dir = os.path.join(renders_dir, slug + "_florence")
os.makedirs(city_dir, exist_ok=True)

print(f"  {{display_city}} ({{display_subtitle}})")
print(f"  Center: {{lat}}, {{lon}} | Base distance: {{base_distance}}m | Slug: {{slug}}")

theme_data = load_theme(theme_name)

for size in sizes:
    output_path = os.path.join(city_dir, f"{{slug}}_{{size}}.png")
    if os.path.exists(output_path) and not force:
        print(f"  {{size}} — SKIPPED (exists)")
        continue

    # Scale distance per size (smaller prints = tighter crop)
    size_config = get_size_config(size)
    size_distance = base_distance
    # Keep consistent distance across sizes for Florence (mosaic looks best consistent)

    print(f"  {{size}} — rendering (distance={{size_distance}}m)...")
    t0 = time.time()
    try:
        result = render_florence_poster(
            location=f"{{lat}},{{lon}}",
            theme_data=theme_data,
            size=size,
            dpi=dpi,
            distance=size_distance,
            output_path=output_path,
            city_name=display_city,
            state_name=display_subtitle,
        )
        elapsed = time.time() - t0
        size_mb = os.path.getsize(result) / 1e6
        print(f"  {{size}} — OK ({{elapsed:.0f}}s, {{size_mb:.1f}} MB)")
    except Exception as e:
        print(f"  {{size}} — ERROR: {{e}}")

    # Memory cleanup between sizes
    import matplotlib.pyplot as plt
    plt.close("all")
    gc.collect()

print("\\n__CITY_DONE__")
"""
    t0 = time.time()
    result = subprocess.run(
        [PYTHON, "-c", script],
        cwd=os.getcwd(),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        capture_output=False,
        timeout=7200,  # 2 hours max per city (5 sizes at 300 DPI)
    )
    elapsed = time.time() - t0
    return result.returncode, elapsed


def get_cities(tier: int | None = None) -> list:
    """Get cities from city_list, optionally filtered by tier."""
    from etsy.city_list import ALL_CITIES, get_cities_by_tier
    if tier is not None:
        return get_cities_by_tier(tier)
    return list(ALL_CITIES)


def main():
    parser = argparse.ArgumentParser(description="Florence full production pipeline")
    parser.add_argument("--start-from", default=None,
                        help="Resume from a specific city name")
    parser.add_argument("--city", default=None,
                        help="Render a single city")
    parser.add_argument("--tier", type=int, default=None,
                        help="Render only a specific tier (1-5)")
    parser.add_argument("--force", action="store_true",
                        help="Re-render even if files exist")
    args = parser.parse_args()

    if args.city:
        print(f"\nRendering: {args.city} (Florence, all sizes)")
        print(f"{'='*60}")
        rc, elapsed = render_city_subprocess(args.city, force=args.force)
        status = "OK" if rc == 0 else f"FAILED (exit {rc})"
        print(f"\n{status} — {elapsed/60:.1f} minutes")
        return

    cities = get_cities(args.tier)

    if args.start_from:
        start_lower = args.start_from.lower()
        found = False
        filtered = []
        for c in cities:
            if c.city.lower() == start_lower:
                found = True
            if found:
                filtered.append(c)
        if not filtered:
            print(f"City '{args.start_from}' not found")
            sys.exit(1)
        print(f"Resuming from {args.start_from} ({len(filtered)} cities remaining)\n")
        cities = filtered

    tier_label = f"Tier {args.tier}" if args.tier else "All tiers"
    print(f"\nFlorence Production Run — {len(cities)} cities x {len(SIZES)} sizes")
    print(f"Filter: {tier_label} | DPI: {DPI} | Theme: {THEME}")
    print(f"Output: {RENDERS_DIR}/{{slug}}_florence/")
    print(f"Mode: subprocess per city (memory-safe)\n")

    total_time = 0
    ok_count = 0
    fail_count = 0

    for i, city in enumerate(cities, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(cities)}] {city.city}")
        print(f"{'='*60}")

        rc, elapsed = render_city_subprocess(city.city, force=args.force)
        total_time += elapsed

        if rc == 0:
            ok_count += 1
            print(f"\n  City complete: {elapsed/60:.1f} minutes")
        else:
            fail_count += 1
            print(f"\n  FAILED (exit {rc}) after {elapsed/60:.1f} minutes")

    print(f"\n{'='*60}")
    print(f"ALL DONE! {ok_count} ok, {fail_count} failed")
    print(f"Total time: {total_time/60:.1f} minutes ({total_time/3600:.1f} hours)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
