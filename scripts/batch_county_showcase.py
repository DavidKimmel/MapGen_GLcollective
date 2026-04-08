#!/usr/bin/env python3
"""
Render 5 counties × 1 theme each for showcase.
Uses fixed layout: ghost bg, PIL fonts, smart county centering.
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
OUTPUT_DIR = os.path.join(_PROJECT_DIR, "etsy", "renders", "CountyMap", "showcase")

DPI = 150
SIZE = "16x20"
GHOST_OPACITY = 0.30

# Canvas layout constants
CANVAS_W_IN = 16
CANVAS_H_IN = 20
CANVAS_ASPECT = CANVAS_W_IN / CANVAS_H_IN  # 0.8
FADE_START = 0.80   # fade begins at 80% from top
COUNTY_PAD = 1.20   # 20% padding around county within visible area

# 5 counties × 5 themes
RENDERS = [
    ("Bucks", "PA", "custom_3map/sage_atlas"),
    ("Charleston", "SC", "custom_3map/teal_coral"),
    ("Loudoun", "VA", "custom_3map/rose_blush"),
    ("Hamilton", "OH", "custom_3map/nordic_complex"),
    ("Carroll", "MD", "custom_3map/dark_teal"),
]


def _fit_county_to_canvas(
    bbox: tuple[float, float, float, float],
) -> tuple[int, float, float]:
    """Calculate distance and render center to visually center county on canvas.

    The visible map area is the top portion of the canvas (above fade zone).
    We reverse-engineer the render center so the county bbox lands centered
    in that visible area, regardless of county shape.

    Canvas: 16x20 portrait. get_crop_limits maps distance as:
        half_y = distance (full canvas height)
        half_x = distance * 0.8 (canvas width)

    Visible area: top FADE_START (80%) of canvas.
        visible center = 0.5 + (1.0 - FADE_START) / 2 = 0.6 from bottom
        (i.e., 60% up from bottom, 40% down from top)

    Returns:
        (distance_m, render_lat, render_lon)
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    bbox_center_lat = (min_lat + max_lat) / 2.0
    bbox_center_lon = (min_lon + max_lon) / 2.0

    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(bbox_center_lat))

    county_w_m = (max_lon - min_lon) * m_per_deg_lon
    county_h_m = (max_lat - min_lat) * m_per_deg_lat

    # Determine distance so county fits with padding.
    # Canvas half-extents: half_x = dist * 0.8, half_y = dist
    # County must fit within visible area with 15% padding on each side.
    pad = 1.15  # 15% padding
    needed_for_width = (county_w_m / 2.0 * pad) / CANVAS_ASPECT  # dist >= this
    needed_for_height = (county_h_m / 2.0 * pad)                 # dist >= this

    # But the county only has the top 80% of the canvas vertically.
    # The visible area spans from canvas center upward fully, but only
    # partially downward. To be safe, fit within FADE_START of full height:
    #   county_h_m * pad <= distance * 2 * FADE_START
    #   distance >= county_h_m * pad / (2 * FADE_START)
    needed_for_vis_height = county_h_m * pad / (2.0 * FADE_START)

    distance = int(max(needed_for_width, needed_for_height, needed_for_vis_height))

    # Now compute the render center so the county bbox center lands at
    # the visual center of the visible area (not the canvas center).
    #
    # Canvas center is at 50% height. Visible area center is at:
    #   vis_center_pct = 1.0 - (FADE_START / 2.0) = 0.60 from bottom
    # So the visible center is 10% above the canvas center.
    #
    # In map coordinates, canvas center = render_lat.
    # Full canvas height = 2 * distance meters.
    # We need to shift the county bbox center UP by 10% of canvas height:
    #   offset = (vis_center_pct - 0.5) * 2 * distance
    #          = 0.10 * 2 * distance = 0.20 * distance

    vis_center_pct = 1.0 - (FADE_START / 2.0)  # 0.60
    offset_m = (vis_center_pct - 0.5) * 2.0 * distance  # shift in meters

    # The render center must be BELOW the county bbox center so the county
    # appears higher on the canvas. (Moving render center south = county moves up)
    render_lat = bbox_center_lat - offset_m / m_per_deg_lat
    render_lon = bbox_center_lon  # horizontal centering uses bbox center directly

    return distance, render_lat, render_lon


def render_one(county: str, state: str, theme: str) -> tuple[str, float]:
    """Render a single county with ghost + PIL text. Returns (path, file_mb)."""
    info = get_county_info(county, state)
    center_lat, center_lon, bbox = get_county_bounds(county, state)
    distance, render_lat, render_lon = _fit_county_to_canvas(bbox)

    location = f"{render_lat},{render_lon}"

    county_slug = county.lower().replace(" ", "_")
    state_slug = state.lower()
    theme_slug = theme.split("/")[-1]
    output_path = os.path.join(OUTPUT_DIR, f"{county_slug}_{state_slug}_{theme_slug}.png")
    ghost_path = output_path.replace(".png", "_ghost_tmp.png")
    county_path = output_path.replace(".png", "_county_tmp.png")

    common = dict(
        location=location, theme=theme, size=SIZE,
        detail_layers=True, distance=distance, dpi=DPI,
        min_zoom_scale=1.0, map_only=True,
    )

    # Pass 1: Ghost
    render_poster(**common, crop="full", skip_buildings=True,
                  road_min_tier="primary", output_path=ghost_path)

    # Pass 2: County
    render_poster(**common, crop="county", county_name=county,
                  county_state=state, output_path=county_path)

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
    fade_top = int(h * FADE_START)
    fade_bottom = int(h * 0.86)
    fade_height = fade_bottom - fade_top
    if fade_height > 0:
        gradient = np.linspace(0.0, 1.0, fade_height).reshape(-1, 1, 1)
        region = county_arr[fade_top:fade_bottom].astype(np.float64)
        blended = region * (1.0 - gradient) + 255.0 * gradient
        county_arr[fade_top:fade_bottom] = blended.astype(np.uint8)
    county_arr[fade_bottom:] = 255

    composite = Image.fromarray(county_arr)

    # --- PIL text with separator line ---
    draw = ImageDraw.Draw(composite)
    scale = min(16, 20) / 12.0 * (DPI / 72.0) * 0.5

    title_font = ImageFont.truetype(
        os.path.join(FONTS_DIR, "CormorantGaramond-Bold.ttf"), size=int(63 * scale))
    state_font = ImageFont.truetype(
        os.path.join(FONTS_DIR, "CormorantGaramond-Regular.ttf"), size=int(40 * scale))
    coords_font = ImageFont.truetype(
        os.path.join(FONTS_DIR, "JetBrainsMono-Light.ttf"), size=int(24 * scale))

    text_color = (26, 26, 26)
    coord_color = (100, 100, 100)
    line_color = (180, 180, 180)

    # Title — variant D spacing
    title = "   ".join(info["namelsad"].upper())
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    title_h = title_bbox[3] - title_bbox[1]
    title_y = int(h * 0.860)
    draw.text(((w - title_w) // 2, title_y), title, fill=text_color, font=title_font)

    # State
    state_text = "   ".join(info["state"].upper())
    state_bbox = draw.textbbox((0, 0), state_text, font=state_font)
    state_w = state_bbox[2] - state_bbox[0]
    state_h = state_bbox[3] - state_bbox[1]
    state_y = title_y + title_h + int(title_h * 1.20)
    draw.text(((w - state_w) // 2, state_y), state_text, fill=text_color, font=state_font)

    # Coords
    lat_dir = "N" if center_lat >= 0 else "S"
    lon_dir = "W" if center_lon < 0 else "E"
    coords_text = f"{abs(center_lat):.4f}\u00b0 {lat_dir}   {abs(center_lon):.4f}\u00b0 {lon_dir}"
    coords_bbox = draw.textbbox((0, 0), coords_text, font=coords_font)
    coords_w = coords_bbox[2] - coords_bbox[0]
    coords_h = coords_bbox[3] - coords_bbox[1]
    total_gap = int(state_h * (1.00 + 1.00))
    coords_y = state_y + state_h + total_gap
    draw.text(((w - coords_w) // 2, coords_y), coords_text, fill=coord_color, font=coords_font)

    # Separator line — optically centered (60% toward coords)
    state_baseline = state_y + int(state_h * 0.75)
    coords_baseline = coords_y + int(coords_h * 0.75)
    gap = coords_baseline - state_baseline
    line_center_y = state_baseline + int(gap * 0.60)
    line_w = int(w * 0.12)
    draw.line(
        [(w // 2 - line_w, line_center_y), (w // 2 + line_w, line_center_y)],
        fill=line_color, width=2,
    )

    composite.save(output_path, "PNG", dpi=(DPI, DPI))

    os.remove(ghost_path)
    os.remove(county_path)

    return output_path, os.path.getsize(output_path) / 1e6


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    results: list[dict] = []
    total_start = time.time()

    for i, (county, state, theme) in enumerate(RENDERS, 1):
        theme_name = theme.split("/")[-1]
        print(f"\n{'#'*60}")
        print(f"  [{i}/{len(RENDERS)}] {county} County, {state} — {theme_name}")
        print(f"{'#'*60}")

        t0 = time.time()
        try:
            path, file_mb = render_one(county, state, theme)
            elapsed = time.time() - t0
            results.append({
                "label": f"{county}, {state} ({theme_name})",
                "time": elapsed, "size": file_mb, "status": "OK",
            })
            print(f"  Done: {elapsed:.0f}s, {file_mb:.1f}MB")
        except Exception as e:
            elapsed = time.time() - t0
            results.append({
                "label": f"{county}, {state} ({theme_name})",
                "time": elapsed, "size": 0, "status": str(e)[:60],
            })
            import traceback
            traceback.print_exc()
            print(f"  FAIL: {e}")

    total = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"{'Render':<45} {'Time':>7} {'Size':>7} Status")
    print(f"{'-'*45} {'-'*7} {'-'*7} {'-'*10}")
    for r in results:
        print(f"{r['label']:<45} {r['time']:>6.0f}s {r['size']:>5.1f}MB {r['status']}")
    print(f"\nTotal: {total:.0f}s ({total/60:.1f}m)")


if __name__ == "__main__":
    main()
