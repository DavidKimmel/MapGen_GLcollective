#!/usr/bin/env python3
"""Quick single render: sky_blue with layout fixes."""

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

COUNTY = "Arlington"
STATE = "VA"
THEME = "custom_3map/sky_blue"
DPI = 150
SIZE = "16x20"
GHOST_OPACITY = 0.30

info = get_county_info(COUNTY, STATE)
center_lat, center_lon, bbox = get_county_bounds(COUNTY, STATE)

# More padding so full county is visible with breathing room
min_lon, min_lat, max_lon, max_lat = bbox
m_per_deg_lat = 111_320.0
m_per_deg_lon = 111_320.0 * math.cos(math.radians(center_lat))
width_m = (max_lon - min_lon) * m_per_deg_lon
height_m = (max_lat - min_lat) * m_per_deg_lat
distance = int(max(width_m, height_m) / 2.0 * 1.30)  # was 1.15

location = f"{center_lat},{center_lon}"

common = dict(
    location=location, theme=THEME, size=SIZE,
    detail_layers=True, distance=distance, dpi=DPI,
    min_zoom_scale=1.0, map_only=True,
)

ghost_path = os.path.join(OUTPUT_DIR, "skyblue_fix_ghost_tmp.png")
county_path = os.path.join(OUTPUT_DIR, "skyblue_fix_county_tmp.png")
output_path = os.path.join(OUTPUT_DIR, "skyblue_fix.png")

t0 = time.time()

print("Pass 1: Ghost...")
render_poster(**common, crop="full", skip_buildings=True,
              road_min_tier="primary", output_path=ghost_path)

print("Pass 2: County...")
render_poster(**common, crop="county", county_name=COUNTY,
              county_state=STATE, output_path=county_path)

print("Compositing...")
ghost_img = Image.open(ghost_path).convert("RGB")
county_img = Image.open(county_path).convert("RGB")

white = Image.new("RGB", ghost_img.size, (255, 255, 255))
ghost_faded = Image.blend(white, ghost_img, GHOST_OPACITY)

county_arr = np.array(county_img)
ghost_arr = np.array(ghost_faded)
white_mask = np.all(county_arr == 255, axis=2)
county_arr[white_mask] = ghost_arr[white_mask]

# Smaller fade zone — starts lower, ends later
h, w = county_arr.shape[:2]
fade_top = int(h * 0.80)     # was 0.75
fade_bottom = int(h * 0.86)  # was 0.82
fade_height = fade_bottom - fade_top
if fade_height > 0:
    gradient = np.linspace(0.0, 1.0, fade_height).reshape(-1, 1, 1)
    region = county_arr[fade_top:fade_bottom].astype(np.float64)
    blended = region * (1.0 - gradient) + 255.0 * gradient
    county_arr[fade_top:fade_bottom] = blended.astype(np.uint8)
county_arr[fade_bottom:] = 255

composite = Image.fromarray(county_arr)

# PIL text — bigger state and coords
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

# Title
title = "   ".join(info["namelsad"].upper())
title_bbox = draw.textbbox((0, 0), title, font=title_font)
title_w = title_bbox[2] - title_bbox[0]
title_h = title_bbox[3] - title_bbox[1]
title_y = int(h * 0.87)
draw.text(((w - title_w) // 2, title_y), title, fill=text_color, font=title_font)

# State — substantial, with padding
state_text = "   ".join(info["state"].upper())
state_bbox = draw.textbbox((0, 0), state_text, font=state_font)
state_w = state_bbox[2] - state_bbox[0]
state_h = state_bbox[3] - state_bbox[1]
state_y = title_y + title_h + int(title_h * 0.7)
draw.text(((w - state_w) // 2, state_y), state_text, fill=text_color, font=state_font)

# Coords — with padding
lat_dir = "N" if center_lat >= 0 else "S"
lon_dir = "W" if center_lon < 0 else "E"
coords_text = f"{abs(center_lat):.4f}\u00b0 {lat_dir}   {abs(center_lon):.4f}\u00b0 {lon_dir}"
coords_bbox = draw.textbbox((0, 0), coords_text, font=coords_font)
coords_w = coords_bbox[2] - coords_bbox[0]
coords_y = state_y + state_h + int(state_h * 0.7)
draw.text(((w - coords_w) // 2, coords_y), coords_text, fill=coord_color, font=coords_font)

composite.save(output_path, "PNG", dpi=(DPI, DPI))

os.remove(ghost_path)
os.remove(county_path)

elapsed = time.time() - t0
file_mb = os.path.getsize(output_path) / 1e6
print(f"\n[OK] {output_path} ({file_mb:.1f}MB, {elapsed:.0f}s)")
