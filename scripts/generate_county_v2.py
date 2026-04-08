#!/usr/bin/env python3
"""
MapGen — County Map Generator v2.

Two-pass render: faint "ghost" full map as background, county-cropped
map composited on top. Gives context to surrounding geography.

Usage:
    python scripts/generate_county_v2.py --county "Arlington" --state "VA" --size 16x20 --dpi 72
"""

import argparse
import math
import os
import sys
import time

import numpy as np
from PIL import Image

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from engine.county_mask import get_county_bounds, get_county_info
from engine.renderer import render_poster
from export.output_sizes import PRINT_SIZES


def _distance_from_bbox(
    bbox: tuple[float, float, float, float],
    padding_factor: float = 1.15,
) -> int:
    """Calculate suitable distance (meters) from county bounding box."""
    min_lon, min_lat, max_lon, max_lat = bbox
    center_lat = (min_lat + max_lat) / 2.0
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(center_lat))
    width_m = (max_lon - min_lon) * m_per_deg_lon
    height_m = (max_lat - min_lat) * m_per_deg_lat
    half_extent = max(width_m, height_m) / 2.0
    return int(half_extent * padding_factor)


def generate_county_map_v2(
    county_name: str,
    state: str,
    theme: str = "37th_parallel",
    size: str = "16x20",
    output_path: str | None = None,
    dpi: int = 300,
    font_preset: int = 7,
    ghost_opacity: float = 0.15,
) -> str:
    """Generate county map with ghost background.

    Two-pass render:
      1. Full rectangular map (no mask) → faded to ghost
      2. County-cropped map → composited on top

    Args:
        ghost_opacity: How visible the background map is (0.0=invisible, 1.0=full).
    """
    info = get_county_info(county_name, state)
    center_lat, center_lon, bbox = get_county_bounds(county_name, state)
    distance = _distance_from_bbox(bbox, padding_factor=1.15)
    location = f"{center_lat},{center_lon}"

    # Text lines
    text_line_1 = info["namelsad"]
    text_line_2 = info["state"]
    lat_dir = "N" if center_lat >= 0 else "S"
    lon_dir = "W" if center_lon < 0 else "E"
    text_line_3 = (
        f"{abs(center_lat):.4f}\u00b0 {lat_dir}  "
        f"{abs(center_lon):.4f}\u00b0 {lon_dir}"
    )

    # Output path
    if output_path is None:
        county_slug = county_name.lower().replace(" ", "_")
        state_slug = state.lower().replace(" ", "_")
        output_dir = os.path.join(_PROJECT_DIR, "etsy", "renders", "CountyMap")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(
            output_dir,
            f"{county_slug}_{state_slug}_{theme}_{size}_v2.png",
        )

    # Shared render params
    common = dict(
        location=location,
        theme=theme,
        size=size,
        detail_layers=True,
        distance=distance,
        font_preset=font_preset,
        dpi=dpi,
        min_zoom_scale=1.0,
    )

    # Temp paths
    base = output_path.rsplit(".", 1)[0]
    ghost_path = base + "_ghost_tmp.png"
    county_path = base + "_county_tmp.png"

    # --- Pass 1: Full map (no mask, no buildings, primary roads only) ---
    # Uses same text-zone layout as Pass 2 so map areas align pixel-for-pixel.
    print(f"\n{'='*60}")
    print("PASS 1: Rendering ghost background (no buildings, primary+ roads)...")
    print(f"{'='*60}")
    render_poster(
        **common,
        crop="full",
        skip_buildings=True,
        road_min_tier="primary",
        text_line_1=text_line_1,
        text_line_2=text_line_2,
        text_line_3=text_line_3,
        output_path=ghost_path,
    )

    # --- Pass 2: County-cropped map ---
    print(f"\n{'='*60}")
    print("PASS 2: Rendering county-cropped map...")
    print(f"{'='*60}")
    render_poster(
        **common,
        crop="county",
        county_name=county_name,
        county_state=state,
        text_line_1=text_line_1,
        text_line_2=text_line_2,
        text_line_3=text_line_3,
        output_path=county_path,
    )

    # --- Composite ---
    print(f"\n{'='*60}")
    print("Compositing ghost + county...")
    print(f"{'='*60}")

    ghost_img = Image.open(ghost_path).convert("RGB")
    county_img = Image.open(county_path).convert("RGB")

    # Fade the full map toward white
    white = Image.new("RGB", ghost_img.size, (255, 255, 255))
    ghost_faded = Image.blend(white, ghost_img, ghost_opacity)

    # Replace pure-white pixels in county image with ghost pixels.
    # The county mask fills outside with #FFFFFF. Map bg is #FCFCFA,
    # so exact (255,255,255) reliably identifies masked-out areas.
    county_arr = np.array(county_img)
    ghost_arr = np.array(ghost_faded)
    white_mask = np.all(county_arr == 255, axis=2)

    print(f"  White pixels (outside county): {white_mask.sum():,} / {white_mask.size:,}")
    print(f"  Content pixels (inside county): {(~white_mask).sum():,}")

    # Save the text zone before compositing (we'll paste it back after gradient)
    h, w = county_arr.shape[:2]
    text_zone_top = int(h * (1.0 - 0.196))  # map_bottom = 0.196 from figure bottom
    text_zone = county_arr[text_zone_top:].copy()

    county_arr[white_mask] = ghost_arr[white_mask]

    # Apply gradient fade at bottom of map zone into white.
    fade_top = int(h * (1.0 - 0.28))     # start fading
    fade_bottom = int(h * (1.0 - 0.196))  # fully white at text zone boundary
    fade_height = fade_bottom - fade_top

    if fade_height > 0:
        gradient = np.linspace(0.0, 1.0, fade_height).reshape(-1, 1, 1)
        region = county_arr[fade_top:fade_bottom].astype(np.float64)
        blended = region * (1.0 - gradient) + 255.0 * gradient
        county_arr[fade_top:fade_bottom] = blended.astype(np.uint8)

    # Restore text zone on clean white, preserving rendered text
    county_arr[text_zone_top:] = text_zone

    result = Image.fromarray(county_arr)
    result.save(output_path, "PNG", dpi=(dpi, dpi))

    # Clean up temp files
    os.remove(ghost_path)
    os.remove(county_path)

    file_size_mb = os.path.getsize(output_path) / 1e6
    print(f"\n[OK] Composite saved: {output_path} ({file_size_mb:.1f} MB)")

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MapGen — County Map Generator v2 (ghost background)",
    )
    parser.add_argument("--county", type=str, required=True)
    parser.add_argument("--state", type=str, required=True)
    parser.add_argument("--theme", type=str, default="37th_parallel")
    parser.add_argument("--size", type=str, default="16x20",
                        choices=list(PRINT_SIZES.keys()))
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--output", "-o", type=str, default=None)
    parser.add_argument("--font-preset", type=int, default=7,
                        choices=[1, 2, 3, 4, 5, 6, 7])
    parser.add_argument("--ghost-opacity", type=float, default=0.30,
                        help="Ghost map opacity (0.0-1.0, default: 0.30)")

    args = parser.parse_args()

    t_start = time.time()
    path = generate_county_map_v2(
        county_name=args.county,
        state=args.state,
        theme=args.theme,
        size=args.size,
        output_path=args.output,
        dpi=args.dpi,
        font_preset=args.font_preset,
        ghost_opacity=args.ghost_opacity,
    )
    elapsed = time.time() - t_start
    print(f"Total time: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
