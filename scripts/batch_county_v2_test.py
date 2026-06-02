#!/usr/bin/env python3
"""
Batch render 5 county maps using v2 (ghost background) for testing.
Tracks and reports timing for each.
"""

import os
import sys
import time

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from scripts.generate_county_v2 import generate_county_map_v2

COUNTIES = [
    ("Carroll", "MD"),
    ("Fairfax", "VA"),
    ("Montgomery", "MD"),
    ("Loudoun", "VA"),
    ("Howard", "MD"),
]

SETTINGS = dict(
    theme="37th_parallel",
    size="16x20",
    dpi=72,
    font_preset=1,
    ghost_opacity=0.20,
)


def main() -> None:
    results: list[dict] = []
    total_start = time.time()

    for i, (county, state) in enumerate(COUNTIES, 1):
        print(f"\n{'#'*60}")
        print(f"  [{i}/{len(COUNTIES)}] {county} County, {state}")
        print(f"{'#'*60}")

        t0 = time.time()
        try:
            path = generate_county_map_v2(
                county_name=county,
                state=state,
                **SETTINGS,
            )
            elapsed = time.time() - t0
            file_mb = os.path.getsize(path) / 1e6
            results.append({
                "county": f"{county}, {state}",
                "time_s": elapsed,
                "file_mb": file_mb,
                "path": path,
                "status": "OK",
            })
        except Exception as e:
            elapsed = time.time() - t0
            results.append({
                "county": f"{county}, {state}",
                "time_s": elapsed,
                "file_mb": 0,
                "path": "",
                "status": f"FAIL: {e}",
            })

    total_elapsed = time.time() - total_start

    # Summary
    print(f"\n\n{'='*60}")
    print("BATCH RESULTS")
    print(f"{'='*60}")
    print(f"{'County':<25} {'Time':>8} {'Size':>8} {'Status'}")
    print(f"{'-'*25} {'-'*8} {'-'*8} {'-'*20}")
    for r in results:
        print(
            f"{r['county']:<25} "
            f"{r['time_s']:>7.1f}s "
            f"{r['file_mb']:>6.1f}MB "
            f"{r['status']}"
        )
    print(f"\nTotal: {total_elapsed:.1f}s ({total_elapsed/60:.1f}m)")


if __name__ == "__main__":
    main()
