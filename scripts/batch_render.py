#!/usr/bin/env python3
"""
MapGen — Batch Poster Renderer.

Renders multiple cities from a CSV file with parallel support.

CSV format: city,country,lat,lon,dist,display_city,display_country
"""

import argparse
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

from engine.renderer import render_poster


def render_city(row: dict, theme: str, size: str, detail_layers: bool,
                output_dir: str) -> dict:
    """Render a single city from CSV row. Returns status dict."""
    city = row.get("city", "Unknown")
    country = row.get("country", "")

    lat = row.get("lat")
    lon = row.get("lon")
    dist = int(row.get("dist", 0)) if row.get("dist") else None

    display_city = row.get("display_city") or city
    display_country = row.get("display_country") or country

    if lat and lon:
        location = f"{lat},{lon}"
    else:
        location = f"{city}, {country}"

    city_slug = city.lower().replace(" ", "_").replace(",", "")
    output_path = os.path.join(output_dir, f"{city_slug}_{theme}_{size}.png")

    t0 = time.time()
    try:
        render_poster(
            location=location,
            theme=theme,
            size=size,
            detail_layers=detail_layers,
            distance=dist,
            text_line_1=display_city,
            text_line_2=display_country,
            output_path=output_path,
        )
        elapsed = time.time() - t0
        return {"city": city, "status": "ok", "time": elapsed, "path": output_path}
    except Exception as e:
        elapsed = time.time() - t0
        return {"city": city, "status": "error", "time": elapsed, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Batch render map posters from CSV")
    parser.add_argument("--csv", required=True, help="CSV file with cities")
    parser.add_argument("--theme", default="37th_parallel", help="Theme name")
    parser.add_argument("--size", default="16x20", help="Print size")
    parser.add_argument("--detail-layers", action="store_true", default=True)
    parser.add_argument("--no-detail-layers", action="store_true")
    parser.add_argument("--workers", type=int, default=1, help="Parallel workers")
    parser.add_argument("--city", default=None, help="Render only this city")
    parser.add_argument("--output-dir", default="posters", help="Output directory")

    args = parser.parse_args()
    detail_layers = not args.no_detail_layers

    if not os.path.exists(args.csv):
        print(f"Error: CSV file not found: {args.csv}")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    with open(args.csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if args.city:
        rows = [r for r in rows if r.get("city", "").lower() == args.city.lower()]
        if not rows:
            print(f"City '{args.city}' not found in CSV")
            sys.exit(1)

    print(f"Batch rendering {len(rows)} cities with theme '{args.theme}' at {args.size}")
    print(f"Workers: {args.workers}")
    print()

    t_start = time.time()
    results = []

    if args.workers <= 1:
        for row in rows:
            result = render_city(row, args.theme, args.size, detail_layers, args.output_dir)
            results.append(result)
            status = "[OK]" if result["status"] == "ok" else "[ERR]"
            print(f"  {status} {result['city']} ({result['time']:.1f}s)")
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(render_city, row, args.theme, args.size,
                                detail_layers, args.output_dir): row
                for row in rows
            }
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                status = "[OK]" if result["status"] == "ok" else "[ERR]"
                print(f"  {status} {result['city']} ({result['time']:.1f}s)")

    elapsed = time.time() - t_start
    ok = sum(1 for r in results if r["status"] == "ok")
    err = sum(1 for r in results if r["status"] != "ok")
    print(f"\nBatch complete: {ok} success, {err} errors ({elapsed:.1f}s total)")


if __name__ == "__main__":
    main()
