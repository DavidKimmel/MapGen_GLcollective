#!/usr/bin/env python3
"""
Render a county map with correct fonts via PIL text overlay.
Bypasses matplotlib text to guarantee font accuracy.
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
OUTPUT_DIR = os.path.join(_PROJECT_DIR, "etsy", "renders", "CountyMap")


def main() -> None:
    t_start = time.time()

    county_name = "Arlington"
    state = "VA"
    theme = "37th_parallel"
    size = "16x20"
    dpi = 150  # higher for font clarity
    ghost_opacity = 0.30

    info = get_county_info(county_name, state)
    center_lat, center_lon, bbox = get_county_bounds(county_name, state)

    min_lon, min_lat, max_lon, max_lat = bbox
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(center_lat))
    width_m = (max_lon - min_lon) * m_per_deg_lon
    height_m = (max_lat - min_lat) * m_per_deg_lat
    distance = int(max(width_m, height_m) / 2.0 * 1.15)
    location = f"{center_lat},{center_lon}"

    common = dict(
        location=location,
        theme=theme,
        size=size,
        detail_layers=True,
        distance=distance,
        dpi=dpi,
        min_zoom_scale=1.0,
        map_only=True,  # NO matplotlib text — we'll add text via PIL
    )

    ghost_path = os.path.join(OUTPUT_DIR, "correct_ghost_tmp.png")
    county_path = os.path.join(OUTPUT_DIR, "correct_county_tmp.png")
    output_path = os.path.join(OUTPUT_DIR, "CorrectFontMap.png")

    # Pass 1: Ghost
    print("Pass 1: Ghost (map_only)...")
    render_poster(**common, crop="full", skip_buildings=True,
                  road_min_tier="primary", output_path=ghost_path)

    # Pass 2: County
    print("Pass 2: County (map_only)...")
    render_poster(**common, crop="county", county_name=county_name,
                  county_state=state, output_path=county_path)

    # Composite
    print("Compositing...")
    ghost_img = Image.open(ghost_path).convert("RGB")
    county_img = Image.open(county_path).convert("RGB")

    white = Image.new("RGB", ghost_img.size, (255, 255, 255))
    ghost_faded = Image.blend(white, ghost_img, ghost_opacity)

    county_arr = np.array(county_img)
    ghost_arr = np.array(ghost_faded)
    white_mask = np.all(county_arr == 255, axis=2)
    county_arr[white_mask] = ghost_arr[white_mask]

    # Gradient fade at bottom
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

    # Add text with PIL — guaranteed correct fonts
    draw = ImageDraw.Draw(composite)

    title_font = ImageFont.truetype(
        os.path.join(FONTS_DIR, "CormorantGaramond-Bold.ttf"),
        size=int(63 * (min(16, 20) / 12.0) * (dpi / 72.0) * 0.5),
    )
    state_font = ImageFont.truetype(
        os.path.join(FONTS_DIR, "CormorantGaramond-Light.ttf"),
        size=int(20 * (min(16, 20) / 12.0) * (dpi / 72.0) * 0.5),
    )
    coords_font = ImageFont.truetype(
        os.path.join(FONTS_DIR, "JetBrainsMono-Light.ttf"),
        size=int(14 * (min(16, 20) / 12.0) * (dpi / 72.0) * 0.5),
    )

    text_color = (26, 26, 26)  # #1A1A1A
    coord_color = (120, 120, 120)

    # Title — letter-spaced
    title = "   ".join("ARLINGTON COUNTY")
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    title_x = (w - title_w) // 2
    title_y = int(h * 0.845)
    draw.text((title_x, title_y), title, fill=text_color, font=title_font)

    # State
    state_text = "   ".join("VIRGINIA")
    state_bbox = draw.textbbox((0, 0), state_text, font=state_font)
    state_w = state_bbox[2] - state_bbox[0]
    state_x = (w - state_w) // 2
    state_y = title_y + int((title_bbox[3] - title_bbox[1]) * 1.6)
    draw.text((state_x, state_y), state_text, fill=text_color, font=state_font)

    # Coords
    lat_dir = "N" if center_lat >= 0 else "S"
    lon_dir = "W" if center_lon < 0 else "E"
    coords_text = f"{abs(center_lat):.4f}\u00b0 {lat_dir}   {abs(center_lon):.4f}\u00b0 {lon_dir}"
    coords_bbox = draw.textbbox((0, 0), coords_text, font=coords_font)
    coords_w = coords_bbox[2] - coords_bbox[0]
    coords_x = (w - coords_w) // 2
    coords_y = state_y + int((state_bbox[3] - state_bbox[1]) * 2.0)
    draw.text((coords_x, coords_y), coords_text, fill=coord_color, font=coords_font)

    composite.save(output_path, "PNG", dpi=(dpi, dpi))

    # Cleanup
    os.remove(ghost_path)
    os.remove(county_path)

    elapsed = time.time() - t_start
    file_mb = os.path.getsize(output_path) / 1e6
    print(f"\n[OK] CorrectFontMap saved: {output_path} ({file_mb:.1f}MB, {elapsed:.0f}s)")


if __name__ == "__main__":
    main()
