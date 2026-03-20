"""Full pipeline batch processor — render + mockups + listing text per city.

Processes each city sequentially for RAM safety:
  1. Render 5 sizes + detail crop + size comparison (subprocess)
  2. Generate mockups (subprocess)
  3. Generate listing text (in-process, lightweight)

Usage:
    python scripts/batch_full_pipeline.py --tier 5
    python scripts/batch_full_pipeline.py --city "Los Angeles"
    python scripts/batch_full_pipeline.py --tier 5 --start-from "Detroit"
    python scripts/batch_full_pipeline.py --tier 5 --mockups-only
"""

import argparse
import json
import os
import subprocess
import sys
import time

PYTHON = sys.executable
RENDERS_DIR = os.path.join("etsy", "renders")
SIZES = ["8x10", "11x14", "16x20", "18x24", "24x36"]


def run_render(city_name: str, force: bool = False) -> tuple[int, float]:
    """Render all 5 sizes + detail crop + size comparison in subprocess."""
    script = f"""
import gc, sys, os
sys.path.insert(0, os.getcwd())

from etsy.batch_etsy_render import render_etsy_city, RENDERS_DIR
from etsy.city_list import get_city, ALL_CITIES
from etsy.image_composer import create_detail_crop, create_size_comparison

SIZES = {json.dumps(SIZES)}
force = {"True" if force else "False"}
city_name = {json.dumps(city_name)}

city = get_city(city_name)
if not city:
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

    import matplotlib.pyplot as plt
    plt.close("all")
    gc.collect()

print(f"\\n  --- Listing images ---")
create_detail_crop(city.slug)
create_size_comparison(city.slug)

print("\\n__RENDER_DONE__")
"""
    t0 = time.time()
    result = subprocess.run(
        [PYTHON, "-c", script],
        cwd=os.getcwd(),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        capture_output=False,
        timeout=3600,
    )
    return result.returncode, time.time() - t0


def run_mockups(city_slug: str) -> tuple[int, float]:
    """Generate all mockups for a city in subprocess."""
    t0 = time.time()
    result = subprocess.run(
        [PYTHON, "-m", "etsy.mockup_composer", "--city", city_slug],
        cwd=os.getcwd(),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        capture_output=False,
        timeout=600,
    )
    return result.returncode, time.time() - t0


def run_listing_text(city_name: str) -> tuple[int, float]:
    """Generate listing text for a single city in subprocess."""
    script = f"""
import sys, os
sys.path.insert(0, os.getcwd())
sys.stdout.reconfigure(encoding="utf-8")

from etsy.city_list import get_city, ALL_CITIES
from etsy.listing_generator import export_listing_text, export_variations_text

city_name = {json.dumps(city_name)}
city = get_city(city_name)
if not city:
    slug = city_name.lower().replace(" ", "_").replace("'", "")
    for c in ALL_CITIES:
        if c.slug == slug:
            city = c
            break
if not city:
    print(f"City not found: {{city_name}}")
    sys.exit(1)

# Use the city's index in ALL_CITIES for variant rotation
idx = ALL_CITIES.index(city)
export_listing_text(city, variant_idx=idx)
export_variations_text(city, variant_idx=idx)
print(f"  {{city.city}}: listing + variations")
print("__LISTING_DONE__")
"""
    t0 = time.time()
    result = subprocess.run(
        [PYTHON, "-c", script],
        cwd=os.getcwd(),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        capture_output=False,
        timeout=120,
    )
    return result.returncode, time.time() - t0


def process_city(city, force: bool = False, mockups_only: bool = False) -> dict:
    """Run the full pipeline for one city."""
    slug = city.slug
    city_dir = os.path.join(RENDERS_DIR, slug)
    results = {"city": city.city, "slug": slug, "steps": {}}

    if not mockups_only:
        # Step 1: Render
        has_render = os.path.exists(os.path.join(city_dir, f"{slug}_16x20.png"))
        if force or not has_render:
            print(f"\n  [1/3] Rendering 5 sizes + listing images...")
            rc, elapsed = run_render(city.city, force=force)
            results["steps"]["render"] = {"rc": rc, "time": f"{elapsed/60:.1f}m"}
            if rc != 0:
                print(f"  RENDER FAILED (exit {rc})")
                return results
        else:
            print(f"\n  [1/3] Render SKIPPED (files exist)")
            results["steps"]["render"] = {"rc": 0, "time": "skipped"}

    # Step 2: Mockups
    has_mockups = os.path.exists(os.path.join(city_dir, f"{slug}_main.jpg"))
    if force or not has_mockups or mockups_only:
        print(f"  [2/3] Generating mockups...")
        rc, elapsed = run_mockups(slug)
        results["steps"]["mockups"] = {"rc": rc, "time": f"{elapsed:.0f}s"}
        if rc != 0:
            print(f"  MOCKUPS FAILED (exit {rc})")
    else:
        print(f"  [2/3] Mockups SKIPPED (files exist)")
        results["steps"]["mockups"] = {"rc": 0, "time": "skipped"}

    if not mockups_only:
        # Step 3: Listing text
        has_listing = os.path.exists(os.path.join(city_dir, f"{slug}_listing.txt"))
        if force or not has_listing:
            print(f"  [3/3] Generating listing text...")
            rc, elapsed = run_listing_text(city.city)
            results["steps"]["listing"] = {"rc": rc, "time": f"{elapsed:.0f}s"}
        else:
            print(f"  [3/3] Listing text SKIPPED (files exist)")
            results["steps"]["listing"] = {"rc": 0, "time": "skipped"}

    return results


def main():
    parser = argparse.ArgumentParser(description="Full pipeline: render + mockups + listing text")
    parser.add_argument("--tier", type=int, default=None, help="Process cities in this tier")
    parser.add_argument("--city", default=None, help="Process a single city")
    parser.add_argument("--start-from", default=None, help="Resume from a specific city")
    parser.add_argument("--force", action="store_true", help="Re-process even if files exist")
    parser.add_argument("--mockups-only", action="store_true", help="Only generate mockups")
    args = parser.parse_args()

    sys.path.insert(0, os.getcwd())
    from etsy.city_list import ALL_CITIES, get_city, get_cities_by_tier

    if args.city:
        city = get_city(args.city)
        if not city:
            print(f"City not found: {args.city}")
            sys.exit(1)
        cities = [city]
    elif args.tier:
        cities = get_cities_by_tier(args.tier)
    else:
        cities = ALL_CITIES

    if args.start_from:
        start_lower = args.start_from.lower()
        found = False
        filtered = []
        for c in cities:
            if c.city.lower() == start_lower or c.slug == start_lower.replace(" ", "_"):
                found = True
            if found:
                filtered.append(c)
        if not filtered:
            print(f"City '{args.start_from}' not found in list")
            sys.exit(1)
        cities = filtered

    mode = "mockups only" if args.mockups_only else "render + mockups + listing text"
    print(f"\nFull Pipeline Batch — {len(cities)} cities")
    print(f"Mode: {mode}")
    print(f"Force: {args.force}")
    print(f"{'='*60}\n")

    total_time = 0
    ok_count = 0
    fail_count = 0
    all_results = []

    for i, city in enumerate(cities, 1):
        t0 = time.time()
        print(f"{'='*60}")
        print(f"[{i}/{len(cities)}] {city.city}, {city.state} ({city.country})")
        print(f"{'='*60}")

        result = process_city(city, force=args.force, mockups_only=args.mockups_only)
        elapsed = time.time() - t0
        total_time += elapsed
        all_results.append(result)

        failed_steps = [k for k, v in result["steps"].items() if v["rc"] != 0]
        if failed_steps:
            fail_count += 1
            print(f"\n  FAILED steps: {', '.join(failed_steps)} — {elapsed/60:.1f} min")
        else:
            ok_count += 1
            print(f"\n  COMPLETE — {elapsed/60:.1f} min")

        # Estimate remaining
        avg = total_time / i
        remaining = avg * (len(cities) - i)
        print(f"  ETA remaining: ~{remaining/60:.0f} min")

    print(f"\n{'='*60}")
    print(f"ALL DONE! {ok_count} ok, {fail_count} failed")
    print(f"Total time: {total_time/60:.1f} minutes")
    print(f"{'='*60}")

    # Summary
    if fail_count > 0:
        print("\nFailed cities:")
        for r in all_results:
            failed = [k for k, v in r["steps"].items() if v["rc"] != 0]
            if failed:
                print(f"  {r['city']}: {', '.join(failed)}")


if __name__ == "__main__":
    main()
