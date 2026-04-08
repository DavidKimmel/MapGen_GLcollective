#!/usr/bin/env python3
"""
Render a county in all 12 custom_3map themes with:
- Ghost background (map_only, composited)
- Correct fonts via PIL (Cormorant Garamond + JetBrains Mono)
- Gradient fade to text zone
"""

import math
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from engine.county_mask import get_county_bounds, get_county_info
from engine.renderer import render_poster

FONTS_DIR = os.path.join(_PROJECT_DIR, "fonts")
THEMES_DIR = os.path.join(_PROJECT_DIR, "themes", "custom_3map")
OUTPUT_DIR = os.path.join(_PROJECT_DIR, "etsy", "renders", "CountyMap", "theme_test_v2")

COUNTY = "Arlington"
STATE = "VA"
DPI = 150
SIZE = "16x20"
GHOST_OPACITY = 0.30


def _distance_from_bbox(bbox: tuple[float, float, float, float]) -> int:
    min_lon, min_lat, max_lon, max_lat = bbox
    center_lat = (min_lat + max_lat) / 2.0
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(center_lat))
    width_m = (max_lon - min_lon) * m_per_deg_lon
    height_m = (max_lat - min_lat) * m_per_deg_lat
    return int(max(width_m, height_m) / 2.0 * 1.15)


def render_county_themed(
    theme_path: str, theme_id: str, location: str, distance: int,
    info: dict, center_lat: float, center_lon: float,
) -> str:
    """Render one county map with ghost + PIL text for a given theme."""
    output_path = os.path.join(OUTPUT_DIR, f"{theme_id}.png")
    ghost_path = os.path.join(OUTPUT_DIR, f"{theme_id}_ghost_tmp.png")
    county_path = os.path.join(OUTPUT_DIR, f"{theme_id}_county_tmp.png")

    common = dict(
        location=location, theme=theme_path, size=SIZE,
        detail_layers=True, distance=distance, dpi=DPI,
        min_zoom_scale=1.0, map_only=True,
    )

    # Pass 1: Ghost
    render_poster(**common, crop="full", skip_buildings=True,
                  road_min_tier="primary", output_path=ghost_path)

    # Pass 2: County
    render_poster(**common, crop="county", county_name=COUNTY,
                  county_state=STATE, output_path=county_path)

    # Composite
    ghost_img = Image.open(ghost_path).convert("RGB")
    county_img = Image.open(county_path).convert("RGB")

    white = Image.new("RGB", ghost_img.size, (255, 255, 255))
    ghost_faded = Image.blend(white, ghost_img, GHOST_OPACITY)

    county_arr = np.array(county_img)
    ghost_arr = np.array(ghost_faded)
    white_mask = np.all(county_arr == 255, axis=2)
    county_arr[white_mask] = ghost_arr[white_mask]

    # Gradient fade
    h, w = county_arr.shape[:2]
    fade_top = int(h * 0.75)
    fade_bottom = int(h * 0.82)
    fade_height = fade_bottom - fade_top
    if fade_height > 0:
        gradient = np.linspace(0.0, 1.0, fade_height).reshape(-1, 1, 1)
        region = county_arr[fade_top:fade_bottom].astype(np.float64)
        blended = region * (1.0 - gradient) + 255.0 * gradient
        county_arr[fade_top:fade_bottom] = blended.astype(np.uint8)
    county_arr[fade_bottom:] = 255

    composite = Image.fromarray(county_arr)

    # PIL text
    draw = ImageDraw.Draw(composite)
    scale = min(16, 20) / 12.0 * (DPI / 72.0) * 0.5
    title_font = ImageFont.truetype(os.path.join(FONTS_DIR, "CormorantGaramond-Bold.ttf"), size=int(63 * scale))
    state_font = ImageFont.truetype(os.path.join(FONTS_DIR, "CormorantGaramond-Light.ttf"), size=int(22 * scale))
    coords_font = ImageFont.truetype(os.path.join(FONTS_DIR, "JetBrainsMono-Light.ttf"), size=int(14 * scale))

    text_color = (26, 26, 26)
    coord_color = (120, 120, 120)

    title = "   ".join(info["namelsad"].upper())
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    title_y = int(h * 0.845)
    draw.text(((w - title_w) // 2, title_y), title, fill=text_color, font=title_font)

    state_text = "   ".join(info["state"].upper())
    state_bbox = draw.textbbox((0, 0), state_text, font=state_font)
    state_w = state_bbox[2] - state_bbox[0]
    state_y = title_y + int((title_bbox[3] - title_bbox[1]) * 1.6)
    draw.text(((w - state_w) // 2, state_y), state_text, fill=text_color, font=state_font)

    lat_dir = "N" if center_lat >= 0 else "S"
    lon_dir = "W" if center_lon < 0 else "E"
    coords_text = f"{abs(center_lat):.4f}\u00b0 {lat_dir}   {abs(center_lon):.4f}\u00b0 {lon_dir}"
    coords_bbox = draw.textbbox((0, 0), coords_text, font=coords_font)
    coords_w = coords_bbox[2] - coords_bbox[0]
    coords_y = state_y + int((state_bbox[3] - state_bbox[1]) * 2.0)
    draw.text(((w - coords_w) // 2, coords_y), coords_text, fill=coord_color, font=coords_font)

    composite.save(output_path, "PNG", dpi=(DPI, DPI))

    os.remove(ghost_path)
    os.remove(county_path)

    return output_path


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    info = get_county_info(COUNTY, STATE)
    center_lat, center_lon, bbox = get_county_bounds(COUNTY, STATE)
    distance = _distance_from_bbox(bbox)
    location = f"{center_lat},{center_lon}"

    themes = sorted(f[:-5] for f in os.listdir(THEMES_DIR) if f.endswith(".json"))
    results: list[dict] = []
    total_start = time.time()

    for i, theme_id in enumerate(themes, 1):
        theme_path = f"custom_3map/{theme_id}"
        print(f"\n{'#'*60}")
        print(f"  [{i}/{len(themes)}] {theme_id}")
        print(f"{'#'*60}")

        t0 = time.time()
        try:
            path = render_county_themed(
                theme_path, theme_id, location, distance,
                info, center_lat, center_lon,
            )
            elapsed = time.time() - t0
            file_mb = os.path.getsize(path) / 1e6
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
