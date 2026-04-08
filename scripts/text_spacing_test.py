#!/usr/bin/env python3
"""
Print 5 text spacing variants on blank canvases for quick comparison.
No map rendering — just the text zone layout.
"""

import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = os.path.join(_PROJECT_DIR, "fonts")
OUTPUT_DIR = os.path.join(_PROJECT_DIR, "etsy", "renders", "CountyMap")

# Simulate 16x20 at 150 DPI
W = int(16 * 150)  # 2400
H = int(20 * 150)  # 3000
SCALE = min(16, 20) / 12.0 * (150 / 72.0) * 0.5

COUNTY = "CARROLL COUNTY"
STATE = "MARYLAND"
COORDS = "39.5629° N   77.0225° W"

# 5 spacing variants: (label, title_y_pct, title_to_state_mult, state_to_line_mult, line_to_coords_mult)
VARIANTS = [
    ("D — Generous (centered line)", 0.860, 1.20, 1.00, 1.00),
]


def render_variant(label: str, title_y_pct: float,
                   title_gap: float, state_gap: float, coord_gap: float) -> str:
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    title_font = ImageFont.truetype(
        os.path.join(FONTS_DIR, "CormorantGaramond-Bold.ttf"), size=int(63 * SCALE))
    state_font = ImageFont.truetype(
        os.path.join(FONTS_DIR, "CormorantGaramond-Regular.ttf"), size=int(40 * SCALE))
    coords_font = ImageFont.truetype(
        os.path.join(FONTS_DIR, "JetBrainsMono-Light.ttf"), size=int(24 * SCALE))
    label_font = ImageFont.truetype(
        os.path.join(FONTS_DIR, "JetBrainsMono-Light.ttf"), size=int(14 * SCALE))

    text_color = (26, 26, 26)
    coord_color = (100, 100, 100)
    line_color = (180, 180, 180)
    guide_color = (230, 230, 230)

    # Draw a light gray box where the fade zone would be
    fade_top = int(H * 0.80)
    draw.rectangle([(0, fade_top), (W, H)], fill=(245, 245, 245))
    draw.line([(0, fade_top), (W, fade_top)], fill=guide_color, width=1)

    # Label
    draw.text((30, 30), label, fill=(150, 150, 150), font=label_font)
    draw.text((30, 55), f"title_y={title_y_pct}  gaps={title_gap}/{state_gap}/{coord_gap}",
              fill=(180, 180, 180), font=label_font)

    # Title
    title = "   ".join(COUNTY)
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    title_h = title_bbox[3] - title_bbox[1]
    title_y = int(H * title_y_pct)
    draw.text(((W - title_w) // 2, title_y), title, fill=text_color, font=title_font)

    # State
    state_text = "   ".join(STATE)
    state_bbox = draw.textbbox((0, 0), state_text, font=state_font)
    state_w = state_bbox[2] - state_bbox[0]
    state_h = state_bbox[3] - state_bbox[1]
    state_y = title_y + title_h + int(title_h * title_gap)
    draw.text(((W - state_w) // 2, state_y), state_text, fill=text_color, font=state_font)

    # Coords position
    total_gap = int(state_h * (state_gap + coord_gap))
    coords_bbox = draw.textbbox((0, 0), COORDS, font=coords_font)
    coords_w = coords_bbox[2] - coords_bbox[0]
    coords_h = coords_bbox[3] - coords_bbox[1]
    coords_y = state_y + state_h + total_gap

    # Separator line — pushed 60% toward coords for optical centering
    # (larger state text makes 50% look too close to state)
    state_baseline = state_y + int(state_h * 0.75)
    coords_baseline = coords_y + int(coords_h * 0.75)
    gap = coords_baseline - state_baseline
    line_center_y = state_baseline + int(gap * 0.60)
    line_w = int(W * 0.12)
    draw.line(
        [(W // 2 - line_w, line_center_y), (W // 2 + line_w, line_center_y)],
        fill=line_color, width=2,
    )
    draw.text(((W - coords_w) // 2, coords_y), COORDS, fill=coord_color, font=coords_font)

    # Crop to just the text zone area for comparison (bottom 25%)
    crop_top = int(H * 0.76)
    cropped = img.crop((0, crop_top, W, H))

    slug = label.split("—")[0].strip().replace(" ", "")
    path = os.path.join(OUTPUT_DIR, f"text_spacing_{slug}.png")
    cropped.save(path, "PNG")
    return path


def main() -> None:
    paths = []
    for label, ty, tg, sg, cg in VARIANTS:
        p = render_variant(label, ty, tg, sg, cg)
        paths.append(p)
        print(f"  {label} -> {p}")

    # Also make a combined strip
    imgs = [Image.open(p) for p in paths]
    total_h = sum(img.height for img in imgs)
    combined = Image.new("RGB", (imgs[0].width, total_h), (255, 255, 255))
    y = 0
    for img in imgs:
        combined.paste(img, (0, y))
        y += img.height
    combined_path = os.path.join(OUTPUT_DIR, "text_spacing_combined.png")
    combined.save(combined_path, "PNG")
    print(f"\n  Combined -> {combined_path}")


if __name__ == "__main__":
    main()
