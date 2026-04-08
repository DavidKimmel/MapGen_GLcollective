#!/usr/bin/env python3
"""
MapGen — County Map Production Renderer (Final).

Renders a county map with ghost background, PIL text (Cormorant Garamond +
JetBrains Mono), gradient fade, bbox-centered layout.

Usage:
    python scripts/generate_county_final.py --county "Carroll" --state "MD" --theme dark_teal
    python scripts/generate_county_final.py --county "Union" --state "NJ" --theme nordic_complex --dpi 300
    python scripts/generate_county_final.py --county "Marin" --state "CA" --theme sage_atlas --size 16x20
"""

import argparse
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
from export.output_sizes import PRINT_SIZES

FONTS_DIR = os.path.join(_PROJECT_DIR, "fonts")
OUTPUT_DIR = os.path.join(_PROJECT_DIR, "etsy", "renders", "CountyMap")

# Layout constants
FADE_START = 0.80
GHOST_OPACITY = 0.30

# Available themes (custom_3map)
THEMES = [
    "37th_parallel", "dark_teal", "midnight_blue", "noir",
    "nordic_complex", "rose_blush", "sage_atlas", "sky_blue",
    "sunset", "teal_coral", "vintage",
]


def _parse_size(size: str) -> tuple[int, int]:
    """Parse size string to (width_in, height_in)."""
    if size in PRINT_SIZES:
        cfg = PRINT_SIZES[size]
        return cfg["width_in"], cfg["height_in"]
    w, h = size.lower().split("x")
    return int(w), int(h)


def _fit_county_to_canvas(
    bbox: tuple[float, float, float, float],
    canvas_aspect: float,
) -> tuple[int, float, float]:
    """Calculate distance and render center to visually center county on canvas.

    Uses bbox center (not centroid) and shifts the render center south so
    the county appears centered in the visible area above the fade zone.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    bbox_center_lat = (min_lat + max_lat) / 2.0
    bbox_center_lon = (min_lon + max_lon) / 2.0

    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(bbox_center_lat))

    county_w_m = (max_lon - min_lon) * m_per_deg_lon
    county_h_m = (max_lat - min_lat) * m_per_deg_lat

    pad = 1.15
    needed_for_width = (county_w_m / 2.0 * pad) / canvas_aspect
    needed_for_height = (county_h_m / 2.0 * pad)
    needed_for_vis_height = county_h_m * pad / (2.0 * FADE_START)

    distance = int(max(needed_for_width, needed_for_height, needed_for_vis_height))

    vis_center_pct = 1.0 - (FADE_START / 2.0)
    offset_m = (vis_center_pct - 0.5) * 2.0 * distance

    render_lat = bbox_center_lat - offset_m / m_per_deg_lat
    render_lon = bbox_center_lon

    return distance, render_lat, render_lon


def generate_county_map(
    county_name: str,
    state: str,
    theme: str = "dark_teal",
    size: str = "24x36",
    dpi: int = 200,
    output_path: str | None = None,
    ghost_opacity: float = GHOST_OPACITY,
) -> str:
    """Generate a production county map.

    Returns path to saved image.
    """
    t_start = time.time()

    info = get_county_info(county_name, state)
    center_lat, center_lon, bbox = get_county_bounds(county_name, state)
    w_in, h_in = _parse_size(size)
    canvas_aspect = w_in / h_in

    distance, render_lat, render_lon = _fit_county_to_canvas(bbox, canvas_aspect)
    location = f"{render_lat},{render_lon}"

    theme_path = f"custom_3map/{theme}" if "/" not in theme else theme

    if output_path is None:
        county_slug = county_name.lower().replace(" ", "_")
        state_slug = state.lower()
        output_path = os.path.join(
            OUTPUT_DIR, f"{county_slug}_{state_slug}_{theme}_{size}.png"
        )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    ghost_path = output_path.replace(".png", "_ghost_tmp.png")
    county_path = output_path.replace(".png", "_county_tmp.png")

    common = dict(
        location=location, theme=theme_path, size=size,
        detail_layers=True, distance=distance, dpi=dpi,
        min_zoom_scale=1.0, map_only=True,
    )

    # Pass 1: Ghost background
    print(f"Pass 1: Ghost ({county_name}, {state})...")
    render_poster(**common, crop="full", skip_buildings=True,
                  road_min_tier="primary", output_path=ghost_path)

    # Pass 2: County-cropped
    print(f"Pass 2: County crop...")
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

    # --- PIL text: Cormorant Garamond + JetBrains Mono ---
    draw = ImageDraw.Draw(composite)
    scale = min(w_in, h_in) / 12.0 * (dpi / 72.0) * 0.5

    title_font = ImageFont.truetype(
        os.path.join(FONTS_DIR, "CormorantGaramond-Bold.ttf"), size=int(63 * scale))
    state_font = ImageFont.truetype(
        os.path.join(FONTS_DIR, "CormorantGaramond-Regular.ttf"), size=int(40 * scale))
    coords_font = ImageFont.truetype(
        os.path.join(FONTS_DIR, "JetBrainsMono-Light.ttf"), size=int(24 * scale))

    text_color = (26, 26, 26)
    coord_color = (100, 100, 100)
    line_color = (180, 180, 180)

    # Title
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
    state_h_px = state_bbox[3] - state_bbox[1]
    state_y = title_y + title_h + int(title_h * 1.20)
    draw.text(((w - state_w) // 2, state_y), state_text, fill=text_color, font=state_font)

    # Coords
    lat_dir = "N" if center_lat >= 0 else "S"
    lon_dir = "W" if center_lon < 0 else "E"
    coords_text = f"{abs(center_lat):.4f}\u00b0 {lat_dir}   {abs(center_lon):.4f}\u00b0 {lon_dir}"
    coords_bbox_r = draw.textbbox((0, 0), coords_text, font=coords_font)
    coords_w = coords_bbox_r[2] - coords_bbox_r[0]
    coords_h = coords_bbox_r[3] - coords_bbox_r[1]
    total_gap = int(state_h_px * 2.00)
    coords_y = state_y + state_h_px + total_gap
    draw.text(((w - coords_w) // 2, coords_y), coords_text, fill=coord_color, font=coords_font)

    # Separator line — optically centered (60% toward coords)
    state_baseline = state_y + int(state_h_px * 0.75)
    coords_baseline = coords_y + int(coords_h * 0.75)
    gap = coords_baseline - state_baseline
    line_center_y = state_baseline + int(gap * 0.60)
    line_w = int(w * 0.12)
    draw.line(
        [(w // 2 - line_w, line_center_y), (w // 2 + line_w, line_center_y)],
        fill=line_color, width=2,
    )

    composite.save(output_path, "PNG", dpi=(dpi, dpi))

    # Cleanup
    os.remove(ghost_path)
    os.remove(county_path)

    elapsed = time.time() - t_start
    file_mb = os.path.getsize(output_path) / 1e6
    print(f"\n[OK] {output_path} ({file_mb:.1f}MB, {elapsed:.0f}s)")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MapGen -- County Map Production Renderer",
    )
    parser.add_argument("--county", type=str, required=True,
                        help="County name (e.g., 'Carroll')")
    parser.add_argument("--state", type=str, required=True,
                        help="State abbreviation or name (e.g., 'MD')")
    parser.add_argument("--theme", type=str, default="dark_teal",
                        choices=THEMES,
                        help="Color theme (default: dark_teal)")
    parser.add_argument("--size", type=str, default="24x36",
                        help="Print size (default: 24x36)")
    parser.add_argument("--dpi", type=int, default=200,
                        help="Resolution (default: 200)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output file path")
    parser.add_argument("--ghost-opacity", type=float, default=0.30,
                        help="Ghost background opacity (default: 0.30)")

    args = parser.parse_args()

    generate_county_map(
        county_name=args.county,
        state=args.state,
        theme=args.theme,
        size=args.size,
        dpi=args.dpi,
        output_path=args.output,
        ghost_opacity=args.ghost_opacity,
    )


if __name__ == "__main__":
    main()
