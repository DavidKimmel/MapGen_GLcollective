#!/usr/bin/env python3
"""Rerun the 8 failed counties from production batch."""

import os
import sys
import time

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from scripts.generate_county_final import generate_county_map

RENDERS = [
    ("Cook", "IL", "dark_teal"),
    ("Davidson", "TN", "sky_blue"),
    ("Fulton", "GA", "noir"),
    ("Travis", "TX", "teal_coral"),
    ("Hennepin", "MN", "nordic_complex"),
    ("Allegheny", "PA", "dark_teal"),
    ("Wake", "NC", "sage_atlas"),
    ("Maui", "HI", "rose_blush"),
]

OUTPUT_DIR = os.path.join(_PROJECT_DIR, "etsy", "renders", "CountyMap", "production")


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    results: list[dict] = []
    total_start = time.time()

    for i, (county, state, theme) in enumerate(RENDERS, 1):
        print(f"\n[{i}/{len(RENDERS)}] {county} County, {state} -- {theme}")
        t0 = time.time()
        try:
            county_slug = county.lower().replace(" ", "_")
            output_path = os.path.join(
                OUTPUT_DIR, f"{county_slug}_{state.lower()}_{theme}.png"
            )
            generate_county_map(
                county_name=county, state=state, theme=theme,
                size="24x36", dpi=200, output_path=output_path,
            )
            elapsed = time.time() - t0
            file_mb = os.path.getsize(output_path) / 1e6
            results.append({"label": f"{county}, {state} ({theme})", "time": elapsed, "size": file_mb, "status": "OK"})
        except Exception as e:
            elapsed = time.time() - t0
            results.append({"label": f"{county}, {state} ({theme})", "time": elapsed, "size": 0, "status": str(e)[:60]})
            import traceback
            traceback.print_exc()

    total = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"{'Render':<40} {'Time':>7} {'Size':>7} Status")
    print(f"{'-'*40} {'-'*7} {'-'*7} {'-'*10}")
    for r in results:
        print(f"{r['label']:<40} {r['time']:>6.0f}s {r['size']:>5.1f}MB {r['status']}")
    print(f"\nTotal: {total:.0f}s ({total/60:.1f}m)")


if __name__ == "__main__":
    main()
