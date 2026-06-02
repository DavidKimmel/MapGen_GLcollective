#!/usr/bin/env python3
"""
Render a county in all 12 custom_3map themes for color comparison.
Single-pass (no ghost) at low DPI for speed.
"""

import os
import sys
import time

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from scripts.generate_county_v1_working import generate_county_map

THEMES_DIR = os.path.join(_PROJECT_DIR, "themes", "custom_3map")
OUTPUT_DIR = os.path.join(_PROJECT_DIR, "etsy", "renders", "CountyMap", "theme_test")

COUNTY = "Arlington"
STATE = "VA"
DPI = 72
SIZE = "16x20"


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    themes = sorted(
        f[:-5] for f in os.listdir(THEMES_DIR) if f.endswith(".json")
    )
    print(f"Rendering {COUNTY} County, {STATE} in {len(themes)} themes...")

    results: list[dict] = []
    total_start = time.time()

    for i, theme_id in enumerate(themes, 1):
        # Point to custom_3map theme path
        theme_path = f"custom_3map/{theme_id}"
        output_path = os.path.join(OUTPUT_DIR, f"{theme_id}.png")

        print(f"\n[{i}/{len(themes)}] {theme_id}...")
        t0 = time.time()
        try:
            generate_county_map(
                county_name=COUNTY,
                state=STATE,
                theme=theme_path,
                size=SIZE,
                dpi=DPI,
                output_path=output_path,
            )
            elapsed = time.time() - t0
            file_mb = os.path.getsize(output_path) / 1e6
            results.append({"theme": theme_id, "time": elapsed, "size": file_mb, "status": "OK"})
            print(f"  Done: {elapsed:.0f}s, {file_mb:.1f}MB")
        except Exception as e:
            elapsed = time.time() - t0
            results.append({"theme": theme_id, "time": elapsed, "size": 0, "status": str(e)[:60]})
            print(f"  FAIL: {e}")

    total = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"{'Theme':<20} {'Time':>7} {'Size':>7} Status")
    print(f"{'-'*20} {'-'*7} {'-'*7} {'-'*30}")
    for r in results:
        print(f"{r['theme']:<20} {r['time']:>6.0f}s {r['size']:>5.1f}MB {r['status']}")
    print(f"\nTotal: {total:.0f}s ({total/60:.1f}m)")


if __name__ == "__main__":
    main()
