"""Batch render cities with Florence theme — subprocess isolated.

Renders one city at a time in a subprocess to prevent memory leaks.
Florence polygonize() is memory-intensive at 300 DPI.

Usage:
    python scripts/batch_florence_render.py
    python scripts/batch_florence_render.py --start-from "New Orleans"
    python scripts/batch_florence_render.py --city "Chicago"
"""

import argparse
import json
import os
import subprocess
import sys
import time

PYTHON = sys.executable
THEME = "florence"
SIZE = "16x20"
DPI = 300
RENDERS_DIR = os.path.join("etsy", "renders")

# Florence-specific overrides: tighter extents, better centering.
# Keys: city name from city_list.py (or display_name override).
# Values: lat, lon, distance, display_city, display_subtitle, slug
FLORENCE_OVERRIDES: dict[str, dict] = {
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
    "Washington DC": {
        "distance": 6500,
    },
    "New Orleans": {
        "distance": 6000,
    },
    "Nashville": {
        "distance": 6500,
    },
    "Austin": {
        "distance": 6500,
    },
    "Portland": {
        "distance": 6500,
    },
    "Denver": {
        "distance": 6500,
    },
}

# Tier 1 cities — first batch of 10
BATCH_1_CITIES = [
    "Chicago", "New York", "Washington DC", "New Orleans", "Nashville",
    "Austin", "Seattle", "San Francisco", "Portland", "Denver",
]


def render_city_subprocess(city_name: str, force: bool = False) -> tuple[int, float]:
    """Render one city in a subprocess for memory isolation."""
    overrides_json = json.dumps(FLORENCE_OVERRIDES.get(city_name, {}))
    script = f"""
import gc, sys, os, time
sys.path.insert(0, os.getcwd())

from engine.florence_renderer import render_florence_poster
from engine.renderer import load_theme
from etsy.city_list import get_city, ALL_CITIES

city_name = {json.dumps(city_name)}
theme_name = {json.dumps(THEME)}
size = {json.dumps(SIZE)}
dpi = {DPI}
renders_dir = {json.dumps(RENDERS_DIR)}
force = {force}
overrides = {overrides_json}

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
display_city = overrides.get("display_city", city.city)
display_subtitle = overrides.get("display_subtitle", city.state)
lat = overrides.get("lat", city.lat)
lon = overrides.get("lon", city.lon)
distance = overrides.get("distance", city.distance)

city_dir = os.path.join(renders_dir, slug + "_florence")
os.makedirs(city_dir, exist_ok=True)

output_path = os.path.join(city_dir, f"{{slug}}_{{size}}.png")

if os.path.exists(output_path) and not force:
    print(f"  SKIPPED — {{output_path}} already exists")
    print("__CITY_DONE__")
    sys.exit(0)

print(f"  {{display_city}} ({{display_subtitle}})")
print(f"  Center: {{lat}}, {{lon}} | Distance: {{distance}}m | Slug: {{slug}}")
print(f"  Size: {{size}} | DPI: {{dpi}} | Theme: {{theme_name}}")

# Build location string — use coords for precise centering
location = f"{{lat}},{{lon}}"
theme_data = load_theme(theme_name)

t0 = time.time()
result = render_florence_poster(
    location=location,
    theme_data=theme_data,
    size=size,
    dpi=dpi,
    distance=distance,
    output_path=output_path,
    city_name=display_city,
    state_name=display_subtitle,
)
elapsed = time.time() - t0
size_mb = os.path.getsize(result) / 1e6
print(f"\\n  Rendered: {{result}} ({{elapsed:.0f}}s, {{size_mb:.1f}} MB)")

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
        timeout=3600,
    )
    elapsed = time.time() - t0
    return result.returncode, elapsed


def main():
    parser = argparse.ArgumentParser(description="Batch Florence render — memory-safe")
    parser.add_argument("--start-from", default=None,
                        help="Resume from a specific city name")
    parser.add_argument("--city", default=None,
                        help="Render a single city")
    parser.add_argument("--force", action="store_true",
                        help="Re-render even if files exist")
    args = parser.parse_args()

    if args.city:
        print(f"\nRendering: {args.city} (Florence)")
        print(f"{'='*60}")
        rc, elapsed = render_city_subprocess(args.city, force=args.force)
        status = "OK" if rc == 0 else f"FAILED (exit {rc})"
        print(f"\n{status} — {elapsed/60:.1f} minutes")
        return

    cities = BATCH_1_CITIES

    if args.start_from:
        start_lower = args.start_from.lower()
        try:
            idx = [c.lower() for c in cities].index(start_lower)
            cities = cities[idx:]
            print(f"Resuming from {args.start_from} ({len(cities)} cities remaining)\n")
        except ValueError:
            print(f"City '{args.start_from}' not found in batch list")
            sys.exit(1)

    print(f"\nFlorence Batch Render — {len(cities)} cities")
    print(f"Size: {SIZE} | DPI: {DPI} | Theme: {THEME}")
    print(f"Output: {RENDERS_DIR}/{{slug}}_florence/")
    print(f"Mode: subprocess per city (memory-safe)\n")

    total_time = 0
    ok_count = 0
    fail_count = 0

    for i, city_name in enumerate(cities, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(cities)}] {city_name}")
        print(f"{'='*60}")

        rc, elapsed = render_city_subprocess(city_name, force=args.force)
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
