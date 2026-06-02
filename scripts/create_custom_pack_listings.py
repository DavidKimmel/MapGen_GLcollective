"""Generate listing images for CustomMapPack — hero, detail crops, color swatches.

Creates assets for 4 styles × shared between digital/print listings.
Each listing needs:
  1. Hero image — real city map with "YOUR CITY" / "YOUR STATE" text
  2. Detail crop — close-up of map detail
  3. Color swatch (blueprint + monomap only) — labeled cropped map squares

Mockups handled separately via mockup_composer.
"""

import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from export.output_sizes import get_size_config
from engine.florence_renderer import PALETTES as FLORENCE_PALETTES
from engine.florence_text_layout import compose_florence_poster
from engine.blueprint_renderer import (
    compose_blueprint_poster, PALETTES as BLUEPRINT_PALETTES,
)

FONTS_DIR = os.path.join(PROJECT_ROOT, "fonts")
OUT_BASE = os.path.join("etsy", "renders", "CustomMapPack")
RENDERS_DIR = os.path.join("etsy", "renders")
DPI = 200
SIZE = "16x20"

FLORENCE_PALETTE = FLORENCE_PALETTES["florence"]


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def get_canvas_dims() -> tuple[int, int]:
    ps = get_size_config(SIZE)
    return int(ps["width_in"] * DPI), int(ps["height_in"] * DPI)


def extract_map_from_classic(src_path: str) -> Image.Image:
    """Extract map region from a Classic (37th_parallel) poster.

    Classic layout: map fills top ~86%, text in bottom ~14% with white bg.
    """
    img = Image.open(src_path).convert("RGB")
    w, h = img.size
    margin = int(w * 0.04)
    bottom_text = int(h * 0.155)  # crop more to fully remove city name text
    return img.crop((margin, margin, w - margin, h - bottom_text))


def extract_map_from_florence(src_path: str) -> Image.Image:
    """Extract map region from a Florence/MonoMap poster.

    Florence layout: map fills top ~83%, bottom 17% is swatch bar + text.
    """
    img = Image.open(src_path).convert("RGB")
    w, h = img.size
    margin = int(w * 0.05)
    bottom_block = int(h * 0.17)
    return img.crop((margin, margin, w - margin, h - bottom_block))


# ─── CLASSIC HERO ─────────────────────────────────────────────────────────────

def create_classic_hero(output_path: str) -> str:
    """Classic style: white bg, map top, CITY NAME centered bottom."""
    total_w, total_h = get_canvas_dims()
    margin_x = int(total_w * 0.05)

    # Extract map from existing Nashville render
    map_region = extract_map_from_classic(os.path.join(
        RENDERS_DIR, "DefaultMap_Posted", "nashville", "nashville_16x20.png"
    ))

    # Layout dimensions
    bottom_block = int(total_h * 0.14)
    map_h = total_h - margin_x - bottom_block
    map_w = total_w - (2 * margin_x)
    map_region = map_region.resize((map_w, map_h), Image.LANCZOS)

    canvas = Image.new("RGB", (total_w, total_h), "#FFFFFF")
    canvas.paste(map_region, (margin_x, margin_x))

    draw = ImageDraw.Draw(canvas)

    # Classic uses Century Gothic Bold — all caps, centered
    font_path = os.path.join(FONTS_DIR, "GOTHICB.TTF")
    city_font = ImageFont.truetype(font_path, int(total_h * 0.042))
    state_font = ImageFont.truetype(font_path, int(total_h * 0.016))
    coord_font = ImageFont.truetype(font_path, int(total_h * 0.012))

    text_area_top = margin_x + map_h + int(total_h * 0.02)

    # City name — centered
    city_text = "YOUR CITY"
    bbox = draw.textbbox((0, 0), city_text, font=city_font)
    draw.text(
        ((total_w - (bbox[2] - bbox[0])) // 2, text_area_top),
        city_text, fill="#333333", font=city_font,
    )

    # State — centered below
    state_y = text_area_top + int(total_h * 0.042) + int(total_h * 0.008)
    state_text = "YOUR STATE"
    bbox = draw.textbbox((0, 0), state_text, font=state_font)
    draw.text(
        ((total_w - (bbox[2] - bbox[0])) // 2, state_y),
        state_text, fill="#666666", font=state_font,
    )

    # Coords — centered below
    coord_y = state_y + int(total_h * 0.016) + int(total_h * 0.006)
    coord_text = "00.0000°N / 00.0000°W"
    bbox = draw.textbbox((0, 0), coord_text, font=coord_font)
    draw.text(
        ((total_w - (bbox[2] - bbox[0])) // 2, coord_y),
        coord_text, fill="#999999", font=coord_font,
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, dpi=(DPI, DPI))
    print(f"  Classic hero: {output_path} ({os.path.getsize(output_path)/1e6:.1f} MB)")
    return output_path


# ─── FLORENCE HERO ────────────────────────────────────────────────────────────

def create_florence_hero(output_path: str) -> str:
    """Florence style: beige bg, map top, swatch bar + city name bottom right."""
    # Extract raw map from existing Nashville Florence render
    map_region = extract_map_from_florence(os.path.join(
        RENDERS_DIR, "FlorenceMap_Posted", "nashville_florence", "nashville_16x20.png"
    ))

    # Save temp map for compositor
    tmp = output_path + ".tmp_map.png"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    map_region.save(tmp)

    compose_florence_poster(
        map_image_path=tmp,
        city_name="Your City",
        state_or_region="Your State",
        lat=36.1627, lon=-86.7816,
        palette=FLORENCE_PALETTE,
        size_name=SIZE, dpi=DPI,
        bg_color="#F0EBE1",
        text_color="#2C3E50",
        font_path=os.path.join(FONTS_DIR, "Switzer-Bold.ttf"),
        output_path=output_path,
    )

    if os.path.exists(tmp):
        os.remove(tmp)

    print(f"  Florence hero: {output_path} ({os.path.getsize(output_path)/1e6:.1f} MB)")
    return output_path


# ─── MONOMAP HERO ────────────────────────────────────────────────────────────

def create_monomap_hero(output_path: str) -> str:
    """MonoMap style: white bg, single-color map, divider line + city name."""
    navy_hex = "#1C3D6E"

    # Extract raw map from existing Nashville navy MonoMap render
    map_region = extract_map_from_florence(os.path.join(
        RENDERS_DIR, "MonoMap", "navy", "nashville_16x20.png"
    ))

    tmp = output_path + ".tmp_map.png"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    map_region.save(tmp)

    compose_florence_poster(
        map_image_path=tmp,
        city_name="Your City",
        state_or_region="Your State",
        lat=36.1627, lon=-86.7816,
        palette=[navy_hex],
        size_name=SIZE, dpi=DPI,
        bg_color="#FFFFFF",
        text_color=navy_hex,
        font_path=os.path.join(FONTS_DIR, "Switzer-Bold.ttf"),
        output_path=output_path,
    )

    if os.path.exists(tmp):
        os.remove(tmp)

    print(f"  MonoMap hero: {output_path} ({os.path.getsize(output_path)/1e6:.1f} MB)")
    return output_path


# ─── BLUEPRINT HERO ───────────────────────────────────────────────────────────

def create_blueprint_hero(output_path: str) -> str:
    """Blueprint style: top title, blocky swatch bar, shaded mosaic map."""
    compose_blueprint_poster(
        map_image_path=os.path.join(RENDERS_DIR, "GradientMap", "amsterdam_terracotta_16x20.png"),
        city_name="Your City",
        state_or_region="Your State",
        lat=52.3676, lon=4.9041,
        palette=BLUEPRINT_PALETTES["terracotta"]["shades"],
        text_color=BLUEPRINT_PALETTES["terracotta"]["text_color"],
        size_name=SIZE, dpi=DPI,
        output_path=output_path,
        strip_header=True,
    )
    print(f"  Blueprint hero: {output_path} ({os.path.getsize(output_path)/1e6:.1f} MB)")
    return output_path


# ─── DETAIL CROPS ─────────────────────────────────────────────────────────────

def create_detail_crop(src_path: str, output_path: str) -> str:
    """Create a close-up detail crop from the center of a map render."""
    img = Image.open(src_path).convert("RGB")
    w, h = img.size

    # Crop a square from the center area of the map (avoid text)
    crop_size = int(min(w, h) * 0.35)
    cx = int(w * 0.45)
    cy = int(h * 0.38)
    left = max(0, cx - crop_size // 2)
    top = max(0, cy - crop_size // 2)

    detail = img.crop((left, top, left + crop_size, top + crop_size))
    detail = detail.resize((2000, 2000), Image.LANCZOS)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    detail.save(output_path, quality=92)
    print(f"  Detail crop: {output_path} ({os.path.getsize(output_path)/1e6:.1f} MB)")
    return output_path


# ─── COLOR SWATCH GRIDS ──────────────────────────────────────────────────────

def create_color_swatch_grid(
    colors: dict[str, str],
    src_paths: dict[str, str],
    output_path: str,
) -> str:
    """Create labeled color swatch grid — cropped map squares with color names.

    Each swatch is a square crop from the map center, labeled below.
    """
    swatch_size = 600
    label_height = 80
    padding = 50
    cols = min(len(colors), 3)
    rows = (len(colors) + cols - 1) // cols

    grid_w = cols * swatch_size + (cols + 1) * padding
    grid_h = rows * (swatch_size + label_height) + (rows + 1) * padding

    canvas = Image.new("RGB", (grid_w, grid_h), "#FFFFFF")
    draw = ImageDraw.Draw(canvas)
    label_font = ImageFont.truetype(os.path.join(FONTS_DIR, "Montserrat-Bold.ttf"), 32)

    for idx, (color_key, display_name) in enumerate(colors.items()):
        row = idx // cols
        col = idx % cols
        x = padding + col * (swatch_size + padding)
        y = padding + row * (swatch_size + label_height + padding)

        if color_key in src_paths and os.path.exists(src_paths[color_key]):
            src = Image.open(src_paths[color_key]).convert("RGB")
            sw, sh = src.size
            # Crop center square from map area (avoid text at bottom/top)
            cx = sw // 2
            cy = int(sh * 0.38)
            half = min(sw, sh) // 4
            crop = src.crop((
                max(0, cx - half), max(0, cy - half),
                min(sw, cx + half), min(sh, cy + half),
            ))
            crop = crop.resize((swatch_size, swatch_size), Image.LANCZOS)
            canvas.paste(crop, (x, y))
        else:
            draw.rectangle([x, y, x + swatch_size, y + swatch_size], fill="#CCCCCC")
            print(f"    WARNING: missing source for {color_key}")

        # Label centered below swatch
        bbox = draw.textbbox((0, 0), display_name, font=label_font)
        label_w = bbox[2] - bbox[0]
        draw.text(
            (x + (swatch_size - label_w) // 2, y + swatch_size + 15),
            display_name, fill="#333333", font=label_font,
        )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, quality=92)
    print(f"  Color swatch: {output_path} ({os.path.getsize(output_path)/1e6:.1f} MB)")
    return output_path


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("\n=== CustomMapPack Listing Image Generator ===\n")

    # ── 1. Hero images ───────────────────────────────────────────────────
    print("-- Hero Images --")
    create_classic_hero(os.path.join(OUT_BASE, "classic_digital", "hero_your_city.png"))
    create_florence_hero(os.path.join(OUT_BASE, "florence_digital", "hero_your_city.png"))
    create_monomap_hero(os.path.join(OUT_BASE, "monomap_digital", "hero_your_city.png"))
    create_blueprint_hero(os.path.join(OUT_BASE, "blueprint_digital", "hero_your_city.png"))

    # ── 2. Detail crops ──────────────────────────────────────────────────
    print("\n-- Detail Crops --")
    create_detail_crop(
        os.path.join(RENDERS_DIR, "DefaultMap_Posted", "nashville", "nashville_16x20.png"),
        os.path.join(OUT_BASE, "classic_digital", "detail_crop.jpg"),
    )
    create_detail_crop(
        os.path.join(RENDERS_DIR, "FlorenceMap_Posted", "nashville_florence", "nashville_16x20.png"),
        os.path.join(OUT_BASE, "florence_digital", "detail_crop.jpg"),
    )
    create_detail_crop(
        os.path.join(RENDERS_DIR, "MonoMap", "navy", "nashville_16x20.png"),
        os.path.join(OUT_BASE, "monomap_digital", "detail_crop.jpg"),
    )
    create_detail_crop(
        os.path.join(RENDERS_DIR, "GradientMap", "amsterdam_terracotta_16x20.png"),
        os.path.join(OUT_BASE, "blueprint_digital", "detail_crop.jpg"),
    )

    # ── 3. Color swatches (blueprint + monomap only) ─────────────────────
    print("\n-- Color Swatches --")

    # Blueprint — 4 colors using Amsterdam renders
    blueprint_colors = {
        "navy": "Navy",
        "forest": "Forest",
        "terracotta": "Terracotta",
        "charcoal": "Charcoal",
    }
    blueprint_srcs = {
        color: os.path.join(RENDERS_DIR, "GradientMap", f"amsterdam_{color}_16x20.png")
        for color in blueprint_colors
    }
    create_color_swatch_grid(
        blueprint_colors, blueprint_srcs,
        os.path.join(OUT_BASE, "blueprint_digital", "color_options.jpg"),
    )

    # MonoMap — 6 colors using Nashville renders
    mono_colors = {
        "charcoal": "Charcoal",
        "navy": "Navy",
        "forest": "Forest",
        "terracotta": "Terracotta",
        "dusty_rose": "Dusty Rose",
        "black": "Black",
    }
    mono_srcs = {
        color: os.path.join(RENDERS_DIR, "MonoMap", color, "nashville_16x20.png")
        for color in mono_colors
    }
    create_color_swatch_grid(
        mono_colors, mono_srcs,
        os.path.join(OUT_BASE, "monomap_digital", "color_options.jpg"),
    )

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n=== Done! ===")
    for style in ["classic", "florence", "monomap", "blueprint"]:
        d = os.path.join(OUT_BASE, f"{style}_digital")
        if os.path.isdir(d):
            files = [f for f in os.listdir(d) if not f.startswith(".")]
            print(f"  {style}_digital: {len(files)} files — {', '.join(sorted(files))}")


if __name__ == "__main__":
    main()
