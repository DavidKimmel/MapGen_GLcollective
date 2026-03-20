"""Florence-style poster composer — swatch bar + typography.

Layout (top to bottom):
- Top margin (5% of width, matches sides)
- Map image (fills top ~83%)
- Color swatch bar (horizontal strip showing palette)
- City name (large lowercase, right-aligned)
- State/country (smaller, right-aligned)
- Bottom margin
"""

import os
import random
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from export.output_sizes import get_size_config

_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_ENGINE_DIR)
FONTS_DIR = os.path.join(_PROJECT_DIR, "fonts")


def compose_florence_poster(
    map_image_path: str,
    city_name: str,
    state_or_region: str,
    lat: float,
    lon: float,
    palette: list[str],
    size_name: str = "16x20",
    dpi: int = 200,
    bg_color: str = "#F0EBE1",
    text_color: str = "#2C3E50",
    font_path: Optional[str] = None,
    output_path: Optional[str] = None,
) -> str:
    """Compose a Florence-style poster. Returns output path as str."""
    ps = get_size_config(size_name)
    total_w = int(ps["width_in"] * dpi)
    total_h = int(ps["height_in"] * dpi)

    # ─── Layout proportions ──────────────────────────────────────────────
    margin_x = int(total_w * 0.05)
    top_margin = margin_x
    bottom_block_height = int(total_h * 0.17)

    # Text sizing
    city_font_size = int(total_h * 0.075)
    region_font_size = int(total_h * 0.018)

    # Swatch bar
    swatch_height = int(total_h * 0.012)

    # Map fills top area
    map_x = margin_x
    map_y = top_margin
    map_w = total_w - (2 * margin_x)
    map_h = total_h - top_margin - bottom_block_height

    # ─── Load fonts ──────────────────────────────────────────────────────
    city_font = _load_font(font_path, city_font_size, prefer_serif=True)
    region_font = _load_font(font_path, region_font_size, prefer_serif=False)

    # ─── Create canvas ───────────────────────────────────────────────────
    canvas = Image.new("RGB", (total_w, total_h), bg_color)
    draw = ImageDraw.Draw(canvas)

    # ─── Bottom text block ──────────────────────────────────────────────
    right_edge = total_w - margin_x
    text_block_top = map_y + map_h + int(total_h * 0.015)

    # Color swatch bar (full width, above title)
    swatch_y = text_block_top
    swatch_total_w = total_w - (2 * margin_x)
    swatch_gap = int(total_w * 0.003)

    # Vary widths — some blocks wider than others for organic feel
    random.seed(len(city_name))  # deterministic per city
    raw_widths = [random.uniform(0.6, 1.8) for _ in palette]
    total_raw = sum(raw_widths)
    usable_w = swatch_total_w - (swatch_gap * (len(palette) - 1))
    widths = [int((w / total_raw) * usable_w) for w in raw_widths]

    x_cursor = margin_x
    for i, color in enumerate(palette):
        x0 = x_cursor
        x1 = x_cursor + widths[i]
        draw.rectangle([x0, swatch_y, x1, swatch_y + swatch_height], fill=color)
        x_cursor = x1 + swatch_gap

    # City name (large lowercase, right-aligned, below swatch)
    city_text = city_name.lower()
    city_y = swatch_y + swatch_height + int(total_h * 0.012)
    bbox = draw.textbbox((0, 0), city_text, font=city_font)
    city_text_w = bbox[2] - bbox[0]
    draw.text((right_edge - city_text_w, city_y), city_text, fill=text_color, font=city_font)

    # State/country (smaller, right-aligned, below city name)
    if state_or_region:
        state_text = state_or_region.lower()
        state_y = city_y + city_font_size + int(total_h * 0.012)
        bbox = draw.textbbox((0, 0), state_text, font=region_font)
        state_text_w = bbox[2] - bbox[0]
        draw.text((right_edge - state_text_w, state_y), state_text, fill=text_color, font=region_font)

    # ─── Map image ───────────────────────────────────────────────────────
    map_img = Image.open(map_image_path).convert("RGB")
    map_img = map_img.resize((map_w, map_h), Image.LANCZOS)
    canvas.paste(map_img, (map_x, map_y))

    # ─── Save ────────────────────────────────────────────────────────────
    if output_path is None:
        slug = city_name.lower().replace(" ", "_")
        output_path = f"posters/{slug}_florence_poster.png"

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    canvas.save(output_path, dpi=(dpi, dpi))
    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"  Poster saved: {output_path} ({size_mb:.1f} MB)")
    return output_path


def _load_font(
    font_path: Optional[str], size: int, prefer_serif: bool = True,
) -> ImageFont.FreeTypeFont:
    """Try to load a font, falling back through options."""
    if font_path:
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            pass

    if prefer_serif:
        candidates = [
            "georgia.ttf", "georgiab.ttf", "CENTURY.TTF",
            "times.ttf", "timesbd.ttf", "cambriab.ttf",
        ]
    else:
        candidates = [
            "calibri.ttf", "arial.ttf", "CenturyGothic.ttf",
            "segoeui.ttf", "verdana.ttf",
        ]

    for fname in candidates:
        try:
            return ImageFont.truetype(fname, size)
        except OSError:
            continue

    return ImageFont.load_default()
