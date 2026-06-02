"""Clean county renderer for order #4058716130.

Single render pass (no ghost). Outside-county area is filled with the theme's
gradient_color so the county "pops" against a uniform background, matching the
mockup aesthetic the customer asked for. Bottom fade and text colors derive
from the theme automatically so dark themes don't get a white footer.
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

FADE_START = 0.80
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
    if abs(rotation_deg) < 0.05:
        return 1.0
    rad = math.radians(abs(rotation_deg))
    w_need = math.cos(rad) + math.sin(rad) / aspect
    h_need = math.cos(rad) + math.sin(rad) * aspect
    return max(w_need, h_need) + 0.03


def _mix(a: np.ndarray, b: np.ndarray, t: float) -> tuple[int, ...]:
    """Linear blend a*t + b*(1-t), return RGB int tuple."""
    return tuple(int(round(c)) for c in (a * t + b * (1 - t)))


def generate_county_map_clean(
    county_name: str, state: str, theme: str,
    target_size: str = "8x10", dpi: int = 150,
    output_path: str | None = None,
    rotation_deg: float = 0.9,
    edge_dilate: int = 3,
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

    theme_path = f"custom_3map/{theme}" if "/" not in theme else theme
    theme_data = load_theme(theme_path)
    bg_rgb = _hex_to_rgb(theme_data.get("gradient_color",
                                        theme_data.get("bg", "#FFFFFF")))
    text_rgb = _hex_to_rgb(theme_data.get("text", "#1A1A1A"))
    bg_tuple = tuple(int(round(c)) for c in bg_rgb)

    if output_path is None:
        slug = f"{county_name.lower().replace(' ', '_')}_{state.lower()}_{theme}_{target_size}"
        output_path = os.path.join(_PROJECT, "etsy", "renders", "CountyMap", f"{slug}.png")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    county_path = output_path.replace(".png", "_county_tmp.png")

    location = f"{render_lat},{render_lon}"
    print(f"Rendering county (rot={rotation_deg:+.2f}deg, oversize={oversize:.3f})...")
    render_poster(
        location=location, theme=theme_path, size=temp_size_key,
        detail_layers=True, distance=distance, dpi=dpi,
        min_zoom_scale=1.0, map_only=True,
        crop="county", county_name=county_name, county_state=state,
        output_path=county_path,
    )

    county_arr = np.array(Image.open(county_path).convert("RGB"))
    outside_mask = np.all(county_arr == 255, axis=2)
    if edge_dilate > 0:
        outside_mask = binary_dilation(outside_mask, iterations=edge_dilate)
        print(f"  Edge dilation: +{edge_dilate}px")

    # Replace outside-county white pixels with theme gradient color
    bg_arr_u8 = np.array(bg_tuple, dtype=np.uint8)
    county_arr[outside_mask] = bg_arr_u8

    # Rotate
    if abs(rotation_deg) >= 0.05:
        composite_full = Image.fromarray(county_arr)
        rotated = composite_full.rotate(
            rotation_deg, resample=Image.BICUBIC, fillcolor=bg_tuple)
        w_curr, h_curr = rotated.size
        left = (w_curr - target_w_px) // 2
        top = (h_curr - target_h_px) // 2
        cropped = rotated.crop((left, top, left + target_w_px, top + target_h_px))
        county_arr = np.array(cropped)
        print(f"  Rotated {rotation_deg:+.2f}deg, cropped to {target_w_px}x{target_h_px}")

    # Bottom gradient fade — fade map content to theme background color
    h, w = county_arr.shape[:2]
    fade_top = int(h * FADE_START)
    fade_bottom = int(h * 0.86)
    fade_height = fade_bottom - fade_top
    if fade_height > 0:
        gradient = np.linspace(0.0, 1.0, fade_height).reshape(-1, 1, 1)
        region = county_arr[fade_top:fade_bottom].astype(np.float64)
        target = bg_rgb.reshape(1, 1, 3)
        county_arr[fade_top:fade_bottom] = (region * (1.0 - gradient) + target * gradient).astype(np.uint8)
    county_arr[fade_bottom:] = bg_arr_u8

    composite = Image.fromarray(county_arr)

    # Theme-aware text colors
    title_color = tuple(int(c) for c in text_rgb)
    coord_color = _mix(text_rgb, bg_rgb, 0.55)
    line_color = _mix(text_rgb, bg_rgb, 0.30)

    draw = ImageDraw.Draw(composite)
    scale = min(target_w_in, target_h_in) / 12.0 * (dpi / 72.0) * 0.5
    title_font = ImageFont.truetype(os.path.join(FONTS_DIR, "CormorantGaramond-Bold.ttf"), size=int(63 * scale))
    state_font = ImageFont.truetype(os.path.join(FONTS_DIR, "CormorantGaramond-Regular.ttf"), size=int(40 * scale))
    coords_font = ImageFont.truetype(os.path.join(FONTS_DIR, "JetBrainsMono-Light.ttf"), size=int(24 * scale))

    title = "   ".join(info["namelsad"].upper())
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    title_h_px = title_bbox[3] - title_bbox[1]
    title_y = int(h * 0.860)
    draw.text(((w - title_w) // 2, title_y), title, fill=title_color, font=title_font)

    state_text = "   ".join(info["state"].upper())
    state_bbox = draw.textbbox((0, 0), state_text, font=state_font)
    state_w = state_bbox[2] - state_bbox[0]
    state_h_px = state_bbox[3] - state_bbox[1]
    state_y = title_y + title_h_px + int(title_h_px * 1.20)
    draw.text(((w - state_w) // 2, state_y), state_text, fill=title_color, font=state_font)

    lat_dir = "N" if center_lat >= 0 else "S"
    lon_dir = "W" if center_lon < 0 else "E"
    coords_text = f"{abs(center_lat):.4f}° {lat_dir}   {abs(center_lon):.4f}° {lon_dir}"
    cb = draw.textbbox((0, 0), coords_text, font=coords_font)
    coords_w = cb[2] - cb[0]
    coords_h_px = cb[3] - cb[1]
    coords_y = state_y + state_h_px + int(state_h_px * 2.00)
    draw.text(((w - coords_w) // 2, coords_y), coords_text, fill=coord_color, font=coords_font)

    state_baseline = state_y + int(state_h_px * 0.75)
    coords_baseline = coords_y + int(coords_h_px * 0.75)
    line_center_y = state_baseline + int((coords_baseline - state_baseline) * 0.60)
    line_w_px = int(w * 0.12)
    draw.line([(w // 2 - line_w_px, line_center_y), (w // 2 + line_w_px, line_center_y)],
              fill=line_color, width=2)

    composite.save(output_path, "PNG", dpi=(dpi, dpi))
    try: os.remove(county_path)
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
    p.add_argument("--size", default="8x10")
    p.add_argument("--dpi", type=int, default=150)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--rotation", type=float, default=0.9)
    args = p.parse_args()
    generate_county_map_clean(
        county_name=args.county, state=args.state, theme=args.theme,
        target_size=args.size, dpi=args.dpi, output_path=args.output,
        rotation_deg=args.rotation,
    )
