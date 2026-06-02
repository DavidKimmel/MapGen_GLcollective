"""Create color swatch grid images for MonoMap and Blueprint listings.

MonoMap: 2x3 grid with 6 colors, named
Blueprint: 2x2 grid with 4 colors, named

Uses existing renders from MonoMap/ and GradientMap/ folders cropped to just the map (no text/margins).
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

FONTS_DIR = os.path.join(PROJECT_ROOT, "fonts")
OUT_DIR = os.path.join("etsy", "renders", "CustomMapPack")


def extract_map_content(img_path: str) -> Image.Image:
    """Load a poster image and crop to just the map content (remove white margins + text)."""
    img = Image.open(img_path).convert("RGB")
    arr = np.array(img)
    h, w = arr.shape[:2]

    # Find non-white bounds
    non_white = np.where(np.any(arr < 250, axis=2))
    if len(non_white[0]) == 0:
        return img

    top = non_white[0].min()
    bot = non_white[0].max()
    left = non_white[1].min()
    right = non_white[1].max()

    # For poster images with bottom text, crop more aggressively at bottom
    # Take just the top ~78% of the non-white area (map portion)
    content_h = bot - top
    map_bot = top + int(content_h * 0.82)

    return img.crop((left, top, right + 1, map_bot))


def create_mono_swatch():
    """Create 2x3 grid for MonoMap — 6 colors with names."""
    colors = [
        ("Charcoal", "charcoal"),
        ("Navy", "navy"),
        ("Forest", "forest"),
        ("Terracotta", "terracotta"),
        ("Dusty Rose", "dusty_rose"),
        ("Black", "black"),
    ]

    renders_dir = os.path.join("etsy", "renders", "MonoMap")

    # Load one render per color (Chicago 16x20)
    maps = []
    for display_name, slug in colors:
        path = os.path.join(renders_dir, slug, "chicago_16x20.png")
        if not os.path.exists(path):
            path = os.path.join(renders_dir, slug, "nashville_16x20.png")
        if os.path.exists(path):
            maps.append((display_name, extract_map_content(path)))
        else:
            print(f"  WARNING: no render for {slug}")

    if len(maps) < 6:
        print(f"  Only {len(maps)} colors found, need 6")
        return

    # Grid layout: 2 columns x 3 rows
    cols, rows = 3, 2
    cell_w, cell_h = 800, 1000
    gap = 30
    label_h = 60
    margin = 60

    canvas_w = margin * 2 + cols * cell_w + (cols - 1) * gap
    canvas_h = margin * 2 + rows * (cell_h + label_h) + (rows - 1) * gap + 80  # title space

    canvas = Image.new("RGB", (canvas_w, canvas_h), "#FFFFFF")
    draw = ImageDraw.Draw(canvas)

    title_font = ImageFont.truetype(os.path.join(FONTS_DIR, "Montserrat-Bold.ttf"), 48)
    label_font = ImageFont.truetype(os.path.join(FONTS_DIR, "Montserrat-Bold.ttf"), 32)

    # Title
    draw.text((margin, margin), "choose your color", fill="#333333", font=title_font)

    y_start = margin + 80
    for idx, (name, map_img) in enumerate(maps):
        row = idx // cols
        col = idx % cols
        x = margin + col * (cell_w + gap)
        y = y_start + row * (cell_h + label_h + gap)

        # Resize map to cell
        resized = map_img.resize((cell_w, cell_h), Image.LANCZOS)
        canvas.paste(resized, (x, y))

        # Label below
        bbox = draw.textbbox((0, 0), name, font=label_font)
        tw = bbox[2] - bbox[0]
        draw.text((x + (cell_w - tw) // 2, y + cell_h + 8), name, fill="#333333", font=label_font)

    out = os.path.join(OUT_DIR, "monomap_digital", "color_swatch_grid.jpg")
    canvas.save(out, "JPEG", quality=95)
    print(f"  MonoMap swatch: {out}")

    # Copy to print folder too
    import shutil
    shutil.copy(out, os.path.join(OUT_DIR, "monomap_print", "color_swatch_grid.jpg"))


def create_blueprint_swatch():
    """Create 2x2 grid for Blueprint — 4 colors with names."""
    colors = [
        ("Navy", "navy"),
        ("Forest", "forest"),
        ("Terracotta", "terracotta"),
        ("Charcoal", "charcoal"),
    ]

    renders_dir = os.path.join("etsy", "renders", "GradientMap")

    maps = []
    for display_name, slug in colors:
        path = os.path.join(renders_dir, f"chicago_{slug}_16x20.png")
        if not os.path.exists(path):
            path = os.path.join(renders_dir, f"nashville_{slug}_16x20.png")
        if os.path.exists(path):
            maps.append((display_name, extract_map_content(path)))
        else:
            print(f"  WARNING: no render for {slug}")

    if len(maps) < 4:
        print(f"  Only {len(maps)} colors found, need 4")
        return

    # Grid layout: 2x2
    cols, rows = 2, 2
    cell_w, cell_h = 1000, 1250
    gap = 30
    label_h = 60
    margin = 60

    canvas_w = margin * 2 + cols * cell_w + (cols - 1) * gap
    canvas_h = margin * 2 + rows * (cell_h + label_h) + (rows - 1) * gap + 80

    canvas = Image.new("RGB", (canvas_w, canvas_h), "#FFFFFF")
    draw = ImageDraw.Draw(canvas)

    title_font = ImageFont.truetype(os.path.join(FONTS_DIR, "Montserrat-Bold.ttf"), 48)
    label_font = ImageFont.truetype(os.path.join(FONTS_DIR, "Montserrat-Bold.ttf"), 32)

    draw.text((margin, margin), "choose your color", fill="#333333", font=title_font)

    y_start = margin + 80
    for idx, (name, map_img) in enumerate(maps):
        row = idx // cols
        col = idx % cols
        x = margin + col * (cell_w + gap)
        y = y_start + row * (cell_h + label_h + gap)

        resized = map_img.resize((cell_w, cell_h), Image.LANCZOS)
        canvas.paste(resized, (x, y))

        bbox = draw.textbbox((0, 0), name, font=label_font)
        tw = bbox[2] - bbox[0]
        draw.text((x + (cell_w - tw) // 2, y + cell_h + 8), name, fill="#333333", font=label_font)

    out = os.path.join(OUT_DIR, "blueprint_digital", "color_swatch_grid.jpg")
    canvas.save(out, "JPEG", quality=95)
    print(f"  Blueprint swatch: {out}")

    import shutil
    shutil.copy(out, os.path.join(OUT_DIR, "blueprint_print", "color_swatch_grid.jpg"))


if __name__ == "__main__":
    os.makedirs(os.path.join(OUT_DIR, "monomap_digital"), exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, "monomap_print"), exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, "blueprint_digital"), exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, "blueprint_print"), exist_ok=True)

    print("Creating color swatch grids...")
    create_mono_swatch()
    create_blueprint_swatch()
    print("Done!")
