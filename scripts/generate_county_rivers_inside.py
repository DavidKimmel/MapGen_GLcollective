"""County renderer for order #4058716130:
- Rotation
- Bay visible outside county at full opacity (largest water CC, eroded to break thin river connections)
- Rivers and other water OUTSIDE the county are suppressed (replaced with a no-water ghost)
- Rivers/water INSIDE the county render normally

Three render passes:
    1. ghost_norivers : full theme with water/waterways removed (used for outside-bay fill)
    2. ghost_full     : full theme (used to detect bay pixels)
    3. county         : full theme, county-cropped (used for inside-county content)
"""
import json
import math
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_erosion, binary_dilation, label as cc_label

_SCRIPT = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(_SCRIPT)
if _PROJECT not in sys.path:
    sys.path.insert(0, _PROJECT)

from engine.county_mask import get_county_bounds, get_county_info
from engine.renderer import load_theme, render_poster
from export.output_sizes import PRINT_SIZES

FADE_START = 0.80
GHOST_OPACITY = 0.30
FONTS_DIR = os.path.join(_PROJECT, "fonts")
THEMES_DIR = os.path.join(_PROJECT, "themes")


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
    if abs(rotation_deg) < 0.05:
        return 1.0
    rad = math.radians(abs(rotation_deg))
    w_need = math.cos(rad) + math.sin(rad) / aspect
    h_need = math.cos(rad) + math.sin(rad) * aspect
    return max(w_need, h_need) + 0.03


def _write_no_rivers_theme(base_theme_path: str, dst_slug: str) -> str:
    """Write a temp theme JSON: same as base but with water=bg and no waterway lines."""
    src_full_path = os.path.join(THEMES_DIR, f"{base_theme_path}.json")
    with open(src_full_path, "r", encoding="utf-8") as f:
        theme = json.load(f)
    no_rivers = dict(theme)
    no_rivers["water"] = theme.get("bg", "#FFFFFF")
    no_rivers.pop("waterway_line", None)
    no_rivers.pop("waterway_outline", None)
    no_rivers.pop("coastline_stroke", None)
    no_rivers["name"] = f"{theme.get('name', 'theme')} (no rivers)"
    dst_path = os.path.join(THEMES_DIR, "custom_3map", f"{dst_slug}.json")
    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(no_rivers, f, indent=2)
    return dst_path


def _isolate_bay(water_mask: np.ndarray, outside_mask: np.ndarray,
                 erosion_radius_pct: float = 0.006) -> np.ndarray:
    """Isolate the bay (large open water) from rivers in the water mask.

    Steps:
      1. Restrict to outside-county pixels
      2. Erode aggressively so thin rivers disconnect from broad bay
      3. Find largest connected component (= bay)
      4. Dilate back and intersect with original water mask to recover full bay shape
    """
    h, w = water_mask.shape
    radius = max(1, int(min(h, w) * erosion_radius_pct))
    outside_water = water_mask & outside_mask
    if not outside_water.any():
        return np.zeros_like(water_mask)

    eroded = binary_erosion(outside_water, iterations=radius)
    labels, n = cc_label(eroded)
    if n == 0:
        return np.zeros_like(water_mask)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0  # background
    bay_label = int(np.argmax(sizes))
    bay_eroded = (labels == bay_label)
    bay_dilated = binary_dilation(bay_eroded, iterations=radius + 4)
    bay = bay_dilated & water_mask  # snap back to actual water boundary
    return bay


def generate_county_map_rivers_inside(
    county_name: str, state: str, theme: str,
    target_size: str = "24x36", dpi: int = 300,
    output_path: str | None = None,
    rotation_deg: float = 0.9,
    ghost_opacity: float = GHOST_OPACITY,
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

    temp_size_key = f"_temp_{render_w_in:.3f}x{render_h_in:.3f}"
    PRINT_SIZES[temp_size_key] = {
        "width_in": render_w_in, "height_in": render_h_in,
        "distance_m": distance,
    }

    full_theme_path = f"custom_3map/{theme}" if "/" not in theme else theme

    # Build no-rivers theme alongside
    no_rivers_slug = f"_temp_norivers_{theme}_{int(time.time())}"
    no_rivers_theme_file = _write_no_rivers_theme(full_theme_path, no_rivers_slug)
    no_rivers_theme_path = f"custom_3map/{no_rivers_slug}"

    location = f"{render_lat},{render_lon}"
    if output_path is None:
        slug = f"{county_name.lower().replace(' ', '_')}_{state.lower()}_{theme}_riversInside_{target_size}"
        output_path = os.path.join(_PROJECT, "etsy", "renders", "CountyMap", f"{slug}.png")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    ghost_full_path = output_path.replace(".png", "_ghostfull_tmp.png")
    ghost_norivers_path = output_path.replace(".png", "_ghostnorivers_tmp.png")
    county_path = output_path.replace(".png", "_county_tmp.png")

    common = dict(
        location=location, size=temp_size_key,
        detail_layers=True, distance=distance, dpi=dpi,
        min_zoom_scale=1.0, map_only=True,
    )

    print(f"Pass 1: Ghost full theme (rotation={rotation_deg:+.2f}deg, oversize={oversize:.3f})...")
    render_poster(**common, theme=full_theme_path, crop="full", skip_buildings=True,
                  road_min_tier="primary", output_path=ghost_full_path)

    print("Pass 2: Ghost no-rivers...")
    render_poster(**common, theme=no_rivers_theme_path, crop="full", skip_buildings=True,
                  road_min_tier="primary", output_path=ghost_norivers_path)

    print("Pass 3: County crop (full theme)...")
    render_poster(**common, theme=full_theme_path, crop="county",
                  county_name=county_name, county_state=state,
                  output_path=county_path)

    print("Compositing...")
    theme_data = load_theme(full_theme_path)
    water_rgb = _hex_to_rgb(theme_data.get("water", "#2E4A5F"))

    ghost_full_arr = np.array(Image.open(ghost_full_path).convert("RGB"))
    ghost_norivers_arr = np.array(Image.open(ghost_norivers_path).convert("RGB"))
    county_arr = np.array(Image.open(county_path).convert("RGB"))

    white = np.full_like(ghost_norivers_arr, 255)
    ghost_norivers_faded = (white.astype(np.float32) * (1 - ghost_opacity)
                            + ghost_norivers_arr.astype(np.float32) * ghost_opacity).astype(np.uint8)

    outside_mask = np.all(county_arr == 255, axis=2)
    color_dist = np.linalg.norm(ghost_full_arr.astype(np.float32) - water_rgb, axis=2)
    water_mask = color_dist < 60.0

    bay_mask = _isolate_bay(water_mask, outside_mask)
    print(f"  Water px: {water_mask.sum():,}  Bay px (isolated): {bay_mask.sum():,}")

    # Composite
    use_bay = outside_mask & bay_mask
    use_norivers = outside_mask & ~bay_mask
    county_arr[use_bay] = ghost_full_arr[use_bay]
    county_arr[use_norivers] = ghost_norivers_faded[use_norivers]

    # Rotate
    if abs(rotation_deg) >= 0.05:
        composite_full = Image.fromarray(county_arr)
        rotated = composite_full.rotate(rotation_deg, resample=Image.BICUBIC, fillcolor=(255, 255, 255))
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
    if fade_bottom > fade_top:
        gradient = np.linspace(0.0, 1.0, fade_bottom - fade_top).reshape(-1, 1, 1)
        region = county_arr[fade_top:fade_bottom].astype(np.float64)
        county_arr[fade_top:fade_bottom] = (region * (1.0 - gradient) + 255.0 * gradient).astype(np.uint8)
    county_arr[fade_bottom:] = 255

    composite = Image.fromarray(county_arr)
    draw = ImageDraw.Draw(composite)
    scale = min(target_w_in, target_h_in) / 12.0 * (dpi / 72.0) * 0.5
    title_font = ImageFont.truetype(os.path.join(FONTS_DIR, "CormorantGaramond-Bold.ttf"), size=int(63 * scale))
    state_font = ImageFont.truetype(os.path.join(FONTS_DIR, "CormorantGaramond-Regular.ttf"), size=int(40 * scale))
    coords_font = ImageFont.truetype(os.path.join(FONTS_DIR, "JetBrainsMono-Light.ttf"), size=int(24 * scale))
    text_color = (26, 26, 26); coord_color = (100, 100, 100); line_color = (180, 180, 180)

    title = "   ".join(info["namelsad"].upper())
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]; title_h_px = title_bbox[3] - title_bbox[1]
    title_y = int(h * 0.860)
    draw.text(((w - title_w) // 2, title_y), title, fill=text_color, font=title_font)

    state_text = "   ".join(info["state"].upper())
    state_bbox = draw.textbbox((0, 0), state_text, font=state_font)
    state_w = state_bbox[2] - state_bbox[0]; state_h_px = state_bbox[3] - state_bbox[1]
    state_y = title_y + title_h_px + int(title_h_px * 1.20)
    draw.text(((w - state_w) // 2, state_y), state_text, fill=text_color, font=state_font)

    lat_dir = "N" if center_lat >= 0 else "S"
    lon_dir = "W" if center_lon < 0 else "E"
    coords_text = f"{abs(center_lat):.4f}° {lat_dir}   {abs(center_lon):.4f}° {lon_dir}"
    cb = draw.textbbox((0, 0), coords_text, font=coords_font)
    coords_w = cb[2] - cb[0]; coords_h_px = cb[3] - cb[1]
    coords_y = state_y + state_h_px + int(state_h_px * 2.00)
    draw.text(((w - coords_w) // 2, coords_y), coords_text, fill=coord_color, font=coords_font)

    state_baseline = state_y + int(state_h_px * 0.75)
    coords_baseline = coords_y + int(coords_h_px * 0.75)
    line_center_y = state_baseline + int((coords_baseline - state_baseline) * 0.60)
    line_w_px = int(w * 0.12)
    draw.line([(w // 2 - line_w_px, line_center_y), (w // 2 + line_w_px, line_center_y)],
              fill=line_color, width=2)

    composite.save(output_path, "PNG", dpi=(dpi, dpi))

    # Cleanup
    for p in (ghost_full_path, ghost_norivers_path, county_path):
        try: os.remove(p)
        except: pass
    try: os.remove(no_rivers_theme_file)
    except: pass
    PRINT_SIZES.pop(temp_size_key, None)

    print(f"[OK] {output_path} ({os.path.getsize(output_path)/1e6:.1f}MB, {time.time()-t_start:.0f}s)")
    return output_path


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--county", required=True)
    p.add_argument("--state", required=True)
    p.add_argument("--theme", required=True)
    p.add_argument("--size", default="24x36")
    p.add_argument("--dpi", type=int, default=300)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--rotation", type=float, default=0.9)
    args = p.parse_args()
    generate_county_map_rivers_inside(
        county_name=args.county, state=args.state, theme=args.theme,
        target_size=args.size, dpi=args.dpi, output_path=args.output,
        rotation_deg=args.rotation,
    )
