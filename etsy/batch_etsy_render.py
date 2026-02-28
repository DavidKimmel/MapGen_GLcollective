"""GeoLine Collective — Batch Etsy Poster Renderer.

Renders the 25 priority cities in the 37th_parallel theme at 300 DPI
for use as Etsy listing images.

Usage:
    python -m etsy.batch_etsy_render                    # Render all Tier 1
    python -m etsy.batch_etsy_render --tier 2           # Render Tier 2
    python -m etsy.batch_etsy_render --city Chicago     # Render one city
    python -m etsy.batch_etsy_render --all              # Render all 25
    python -m etsy.batch_etsy_render --workers 2        # Parallel rendering
"""

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from engine.renderer import render_poster
from etsy.city_list import ALL_CITIES, CityListing, get_cities_by_tier, get_city

# Default render settings
THEME = "37th_parallel"
SIZE = "16x20"
DPI = 300
FONT_PRESET = 1    # sans — clean, modern, widest appeal
RENDERS_DIR = os.path.join(os.path.dirname(__file__), "renders")


def render_etsy_city(city: CityListing, output_dir: str = RENDERS_DIR) -> dict:
    """Render a single city poster for Etsy.

    Returns a status dict with city, status, path/error, and timing.
    """
    city_dir = os.path.join(output_dir, city.slug)
    os.makedirs(city_dir, exist_ok=True)

    output_path = os.path.join(city_dir, f"{city.slug}_{THEME}_{SIZE}.png")

    # Skip if already rendered
    if os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / 1e6
        return {
            "city": city.city,
            "status": "skipped",
            "path": output_path,
            "message": f"Already exists ({size_mb:.1f} MB)",
        }

    location = f"{city.lat},{city.lon}"
    display_city = city.display_city or city.city
    display_subtitle = city.display_subtitle or city.state if city.country == "USA" else city.country

    # Format coordinates for the 3rd text line
    lat_dir = "N" if city.lat >= 0 else "S"
    lon_dir = "W" if city.lon <= 0 else "E"
    coordinates = f"{abs(city.lat):.4f}\u00b0{lat_dir} / {abs(city.lon):.4f}\u00b0{lon_dir}"

    t0 = time.time()
    try:
        render_poster(
            location=location,
            theme=THEME,
            size=SIZE,
            detail_layers=True,
            distance=city.distance,
            text_line_1=display_city,
            text_line_2=display_subtitle,
            text_line_3=coordinates,
            dpi=DPI,
            font_preset=FONT_PRESET,
            output_path=output_path,
        )
        elapsed = time.time() - t0
        size_mb = os.path.getsize(output_path) / 1e6
        return {
            "city": city.city,
            "status": "ok",
            "path": output_path,
            "time": f"{elapsed:.1f}s",
            "size_mb": f"{size_mb:.1f}",
        }
    except Exception as e:
        elapsed = time.time() - t0
        return {
            "city": city.city,
            "status": "error",
            "error": str(e),
            "time": f"{elapsed:.1f}s",
        }


def batch_render(
    cities: list[CityListing],
    output_dir: str = RENDERS_DIR,
    workers: int = 1,
) -> list[dict]:
    """Render multiple cities, optionally in parallel."""
    print(f"\n{'=' * 60}")
    print(f"GeoLine Etsy Batch Renderer")
    print(f"  Cities: {len(cities)}")
    print(f"  Theme: {THEME}")
    print(f"  Size: {SIZE} @ {DPI} DPI")
    print(f"  Output: {output_dir}")
    print(f"  Workers: {workers}")
    print(f"{'=' * 60}\n")

    results: list[dict] = []

    if workers <= 1:
        for i, city in enumerate(cities, 1):
            print(f"[{i}/{len(cities)}] {city.city}, {city.state}...")
            result = render_etsy_city(city, output_dir)
            results.append(result)
            status = result["status"]
            if status == "ok":
                print(f"  OK — {result['path']} ({result['size_mb']} MB, {result['time']})")
            elif status == "skipped":
                print(f"  SKIPPED — {result['message']}")
            else:
                print(f"  ERROR — {result['error']}")
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(render_etsy_city, city, output_dir): city
                for city in cities
            }
            for i, future in enumerate(as_completed(futures), 1):
                city = futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    result = {"city": city.city, "status": "error", "error": str(e)}
                results.append(result)
                print(f"[{i}/{len(cities)}] {result['city']}: {result['status']}")

    # Summary
    ok = sum(1 for r in results if r["status"] == "ok")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    errors = sum(1 for r in results if r["status"] == "error")
    print(f"\n{'=' * 60}")
    print(f"Done! {ok} rendered, {skipped} skipped, {errors} errors")
    print(f"{'=' * 60}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Render Etsy listing posters")
    parser.add_argument("--tier", type=int, default=1,
                        help="Tier to render (1/2/3, default: 1)")
    parser.add_argument("--all", action="store_true",
                        help="Render all 25 cities")
    parser.add_argument("--city", type=str, default=None,
                        help="Render a single city by name")
    parser.add_argument("--output-dir", default=RENDERS_DIR,
                        help="Output directory")
    parser.add_argument("--workers", type=int, default=1,
                        help="Parallel workers (default: 1)")
    args = parser.parse_args()

    if args.city:
        city = get_city(args.city)
        if not city:
            print(f"City not found: {args.city}")
            sys.exit(1)
        cities = [city]
    elif args.all:
        cities = ALL_CITIES
    else:
        cities = get_cities_by_tier(args.tier)

    if not cities:
        print(f"No cities found for tier {args.tier}")
        sys.exit(1)

    batch_render(cities, output_dir=args.output_dir, workers=args.workers)


if __name__ == "__main__":
    main()
