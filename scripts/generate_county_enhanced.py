"""Enhanced county map renderer — supports rotation and full-opacity bay/water outside the county crop.

Wraps generate_county_final's logic but:
- Renders into an oversized canvas so post-rotation we can center-crop back without exposing corners.
- Optionally keeps water at full opacity beyond the county outline (bay_full_opacity=True).

Used to fulfill order #4058716130 — proof iterations.
"""
import math
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_dilation

_SCRIPT = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(_SCRIPT)
if _PROJECT not in sys.path:
    sys.path.insert(0, _PROJECT)

from engine.county_mask import get_county_bounds, get_county_info
from engine.renderer import load_theme, render_poster
from export.output_sizes import PRINT_SIZES

# Inline copy of the layout constants and helpers from generate_county_final
FADE_START = 0.80
GHOST_OPACITY = 0.30
FONTS_DIR = os.path.join(_PROJECT, "fonts")


def _parse_size(size: str) -> tuple[float, float]:
    if size in PRINT_SIZES:
        cfg = PRINT_SIZES[size]
        return cfg["width_in"], cfg["height_in"]
    w, h = size.lower().split("x")
    return float(w), float(h)


def _fit_county_to_canvas(bbox, canvas_aspect):
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


def _hex_to_rgb(hex_color: str) -> np.ndarray:
    h = hex_color.lstrip("#")
    return np.array([int(h[i:i+2], 16) for i in (0, 2, 4)], dtype=np.float64)


def _compute_oversize(rotation_deg: float, aspect: float) -> float:
    """Min scale factor so a target-aspect crop fits inside the rotated render."""
    if abs(rotation_deg) < 0.05:
        return 1.0
    rad = math.radians(abs(rotation_deg))
    w_need = math.cos(rad) + math.sin(rad) / aspect
    h_need = math.cos(rad) + math.sin(rad) * aspect
    return max(w_need, h_need) + 0.03  # 3% buffer


def generate_county_map_enhanced(
    county_name: str,
    state: str,
    theme: str = "vintage_B_farmland",
    target_size: str = "24x36",
    dpi: int = 200,
    output_path: str | None = None,
    rotation_deg: float = 0.0,
    bay_full_opacity: bool = False,
    ghost_opacity: float = GHOST_OPACITY,
    edge_dilate: int = 4,
    keep_intermediates: bool = False,
) -> str:
    t_start = time.time()

    info = get_county_info(county_name, state)
    center_lat, center_lon, bbox = get_county_bounds(county_name, state)
    target_w_in, target_h_in = _parse_size(target_size)
    canvas_aspect = target_w_in / target_h_in
    target_w_px = int(target_w_in * dpi)
    target_h_px = int(target_h_in * dpi)

    distance_orig, render_lat, render_lon = _fit_county_to_canvas(bbox, canvas_aspect)

    oversize = _compute_oversize(rotation_deg, canvas_aspect)
    render_w_in = target_w_in * oversize
    render_h_in = target_h_in * oversize
    distance = int(distance_orig * oversize)

    # Temp PRINT_SIZES entry so render_poster accepts the oversized canvas
    temp_size_key = f"_temp_{render_w_in:.3f}x{render_h_in:.3f}"
    PRINT_SIZES[temp_size_key] = {
        "width_in": render_w_in,
        "height_in": render_h_in,
        "distance_m": distance,
    }

    location = f"{render_lat},{render_lon}"
    theme_path = f"custom_3map/{theme}" if "/" not in theme else theme

    if output_path is None:
        slug = f"{county_name.lower().replace(' ', '_')}_{state.lower()}_{theme}_{target_size}"
        output_path = os.path.join(_PROJECT, "etsy", "renders", "CountyMap", f"{slug}.png")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    ghost_path = output_path.replace(".png", "_ghost_tmp.png")
    county_path = output_path.replace(".png", "_county_tmp.png")

    common = dict(
        location=location, theme=theme_path, size=temp_size_key,
        detail_layers=True, distance=distance, dpi=dpi,
        min_zoom_scale=1.0, map_only=True,
    )

    print(f"Pass 1: Ghost (rotation={rotation_deg:+.2f}deg, oversize={oversize:.3f})...")
    render_poster(**common, crop="full", skip_buildings=True,
                  road_min_tier="primary", output_path=ghost_path)

    print("Pass 2: County crop...")
    render_poster(**common, crop="county", county_name=county_name,
                  county_state=state, output_path=county_path)

    print("Compositing...")
    ghost_img = Image.open(ghost_path).convert("RGB")
    county_img = Image.open(county_path).convert("RGB")

    ghost_orig = np.array(ghost_img)
    white_pix = np.full_like(ghost_orig, 255)
    ghost_faded = (white_pix.astype(np.float32) * (1 - ghost_opacity)
                   + ghost_orig.astype(np.float32) * ghost_opacity).astype(np.uint8)

    county_arr = np.array(county_img)
    outside_mask = np.all(county_arr == 255, axis=2)

    # Dilate to absorb the antialiased halo at the county-mask boundary.
    # The matplotlib mask renders an anti-aliased edge of partial-white pixels that
    # don't match np.all(== 255), so they survive as a pale ring just inside/outside
    # the black border. Dilating outside_mask catches those edge pixels.
    if edge_dilate > 0:
        outside_mask = binary_dilation(outside_mask, iterations=edge_dilate)
        print(f"  Edge dilation: +{edge_dilate}px to absorb antialias halo")

    if bay_full_opacity:
        theme_data = load_theme(theme_path)
        water_rgb = _hex_to_rgb(theme_data.get("water", "#2E4A5F"))
        color_dist = np.linalg.norm(ghost_orig.astype(np.float32) - water_rgb, axis=2)
        water_mask = color_dist < 60.0  # tolerance for anti-aliased edges
        use_full_water = outside_mask & water_mask
        use_faded = outside_mask & ~water_mask
        county_arr[use_full_water] = ghost_orig[use_full_water]
        county_arr[use_faded] = ghost_faded[use_faded]
        print(f"  Bay-up: {use_full_water.sum():,} px at full opacity")
    else:
        county_arr[outside_mask] = ghost_faded[outside_mask]

    # Rotate before fade — fade and text must stay axis-aligned
    if abs(rotation_deg) >= 0.05:
        composite_full = Image.fromarray(county_arr)
        rotated = composite_full.rotate(
            rotation_deg,  # positive = counter-clockwise (lifts right side up to level a down-right tilt)
            resample=Image.BICUBIC,
            fillcolor=(255, 255, 255),
        )
        w_curr, h_curr = rotated.size
        left = (w_curr - target_w_px) // 2
        top = (h_curr - target_h_px) // 2
        cropped = rotated.crop((left, top, left + target_w_px, top + target_h_px))
        county_arr = np.array(cropped)
        print(f"  Rotated {rotation_deg:+.2f}deg, cropped to {target_w_px}x{target_h_px}")

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

    # PIL text: Cormorant Garamond + JetBrains Mono
    draw = ImageDraw.Draw(composite)
    scale = min(target_w_in, target_h_in) / 12.0 * (dpi / 72.0) * 0.5
    title_font = ImageFont.truetype(os.path.join(FONTS_DIR, "CormorantGaramond-Bold.ttf"), size=int(63 * scale))
    state_font = ImageFont.truetype(os.path.join(FONTS_DIR, "CormorantGaramond-Regular.ttf"), size=int(40 * scale))
    coords_font = ImageFont.truetype(os.path.join(FONTS_DIR, "JetBrainsMono-Light.ttf"), size=int(24 * scale))

    text_color = (26, 26, 26)
    coord_color = (100, 100, 100)
    line_color = (180, 180, 180)

    title = "   ".join(info["namelsad"].upper())
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    title_h = title_bbox[3] - title_bbox[1]
    title_y = int(h * 0.860)
    draw.text(((w - title_w) // 2, title_y), title, fill=text_color, font=title_font)

    state_text = "   ".join(info["state"].upper())
    state_bbox = draw.textbbox((0, 0), state_text, font=state_font)
    state_w = state_bbox[2] - state_bbox[0]
    state_h_px = state_bbox[3] - state_bbox[1]
    state_y = title_y + title_h + int(title_h * 1.20)
    draw.text(((w - state_w) // 2, state_y), state_text, fill=text_color, font=state_font)

    lat_dir = "N" if center_lat >= 0 else "S"
    lon_dir = "W" if center_lon < 0 else "E"
    coords_text = f"{abs(center_lat):.4f}° {lat_dir}   {abs(center_lon):.4f}° {lon_dir}"
    coords_bbox_r = draw.textbbox((0, 0), coords_text, font=coords_font)
    coords_w = coords_bbox_r[2] - coords_bbox_r[0]
    coords_h = coords_bbox_r[3] - coords_bbox_r[1]
    total_gap = int(state_h_px * 2.00)
    coords_y = state_y + state_h_px + total_gap
    draw.text(((w - coords_w) // 2, coords_y), coords_text, fill=coord_color, font=coords_font)

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
    if not keep_intermediates:
        os.remove(ghost_path)
        os.remove(county_path)
    PRINT_SIZES.pop(temp_size_key, None)

    elapsed = time.time() - t_start
    file_mb = os.path.getsize(output_path) / 1e6
    print(f"[OK] {output_path} ({file_mb:.1f}MB, {elapsed:.0f}s)")
    return output_path


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--county", required=True)
    p.add_argument("--state", required=True)
    p.add_argument("--theme", default="vintage_B_farmland")
    p.add_argument("--size", default="24x36")
    p.add_argument("--dpi", type=int, default=200)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--rotation", type=float, default=0.0)
    p.add_argument("--bay-up", action="store_true")
    args = p.parse_args()
    generate_county_map_enhanced(
        county_name=args.county, state=args.state, theme=args.theme,
        target_size=args.size, dpi=args.dpi, output_path=args.output,
        rotation_deg=args.rotation, bay_full_opacity=args.bay_up,
    )
