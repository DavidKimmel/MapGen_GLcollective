"""Create 6-color MonoMap showcase image using 6FRAME.psd.

Populates each frame with a different city in a different color,
then overlays color name labels below each frame.

Output: saved as {city}_6color_labeled.jpg in each city's monomap folder,
plus a shared version for cities without all renders.

Usage:
    python scripts/create_monomap_6color.py                   # Shared showcase
    python scripts/create_monomap_6color.py --city chicago     # City-specific
    python scripts/create_monomap_6color.py --all              # All cities
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from PIL import Image, ImageDraw, ImageFont
from psd_tools import PSDImage

RENDERS_DIR = Path("etsy/renders")
PSD_PATH = Path("etsy/TUR2/Best/6FRAME.psd")
FONTS_DIR = Path("fonts")

# 6 colors in display order (top-left to bottom-right)
COLORS: list[tuple[str, str]] = [
    ("charcoal", "Charcoal"),
    ("navy", "Navy"),
    ("forest", "Forest"),
    ("terracotta", "Terracotta"),
    ("dusty_rose", "Dusty Rose"),
    ("black", "Black"),
]

# 6 different showcase cities — one per color for variety
# Order matches COLORS: charcoal, navy, forest, terracotta, dusty_rose, black
SHOWCASE_CITIES: list[tuple[str, str]] = [
    ("chicago", "charcoal"),
    ("nashville", "navy"),
    ("berlin", "forest"),
    ("paris", "terracotta"),
    ("amsterdam", "dusty_rose"),
    ("rome", "black"),
]

# Manually measured slot positions from 6FRAME.psd (3x2 grid)
SLOTS: list[tuple[int, int, int, int]] = [
    # (left, top, right, bottom)
    (490, 250, 1510, 1735),    # TL
    (1635, 250, 2654, 1735),   # TC
    (2773, 250, 3798, 1735),   # TR
    (490, 1816, 1510, 3300),   # BL
    (1635, 1816, 2654, 3300),  # BC
    (2773, 1816, 3798, 3300),  # BR
]


def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONTS_DIR / name
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def find_render(city_slug: str, color: str, size: str = "18x24") -> Path | None:
    """Find a MonoMap render — try color-suffixed first, then plain (navy)."""
    city_dir = RENDERS_DIR / f"{city_slug}_monomap"

    # Color-suffixed
    p = city_dir / f"{city_slug}_{color}_{size}.png"
    if p.exists():
        return p

    # Navy plain (no suffix)
    if color == "navy":
        p = city_dir / f"{city_slug}_{size}.png"
        if p.exists():
            return p

    # Shared MonoMap folder
    p = RENDERS_DIR / "MonoMap" / color / f"{city_slug}_{size}.png"
    if p.exists():
        return p

    return None


def fit_to_slot(render: Image.Image, slot: tuple[int, int, int, int]) -> Image.Image:
    """Fit render to slot preserving aspect ratio, white fill."""
    l, t, r, b = slot
    sw, sh = r - l, b - t
    rw, rh = render.size
    scale = min(sw / rw, sh / rh)
    new_w = round(rw * scale)
    new_h = round(rh * scale)
    resized = render.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGBA", (sw, sh), (255, 255, 255, 255))
    ox = (sw - new_w) // 2
    oy = (sh - new_h) // 2
    canvas.paste(resized, (ox, oy))
    return canvas


def create_6color_showcase(output_path: str, title: str = "Choose Your Color") -> str | None:
    """Create the labeled 6-color showcase image.

    Uses SHOWCASE_CITIES for variety — each frame shows a different city.
    """
    if not PSD_PATH.exists():
        print(f"  PSD not found: {PSD_PATH}")
        return None

    # Load PSD background
    psd = PSDImage.open(str(PSD_PATH))
    base = psd.composite().convert("RGBA")

    # Place renders in slots
    for i, ((city_slug, color), slot) in enumerate(zip(SHOWCASE_CITIES, SLOTS)):
        render_path = find_render(city_slug, color, "18x24")
        if not render_path:
            # Fallback: try 16x20
            render_path = find_render(city_slug, color, "16x20")
        if not render_path:
            print(f"  Missing render: {city_slug} {color}")
            continue

        render = Image.open(str(render_path)).convert("RGBA")
        fitted = fit_to_slot(render, slot)
        l, t, r, b = slot
        base.paste(fitted, (l, t), fitted)

    # Convert to RGB for drawing
    result = base.convert("RGB")
    draw = ImageDraw.Draw(result)

    # Title across top
    title_font = _load_font("Montserrat-Bold.ttf", 90)
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    canvas_w = result.width
    # Draw title centered, just above the bottom gap between rows
    # Actually put it at the very top of the image
    # But the frames start at y=250, so not much room. Put between rows instead.
    # Gap between rows: y=1735 to y=1816 — only 81px, too tight.
    # Put labels BELOW each frame instead.

    # Color labels below each frame
    label_font = _load_font("Montserrat-Bold.ttf", 72)

    for i, ((_city, _color), (color_key, color_display), slot) in enumerate(
        zip(SHOWCASE_CITIES, COLORS, SLOTS)
    ):
        l, t, r, b = slot
        slot_center_x = (l + r) // 2

        lbbox = draw.textbbox((0, 0), color_display, font=label_font)
        lw = lbbox[2] - lbbox[0]
        lh = lbbox[3] - lbbox[1]

        # Position label just below the frame bottom
        label_x = slot_center_x - lw // 2
        if i < 3:
            # Top row — label between rows
            label_y = b + 15
        else:
            # Bottom row — label below frames
            label_y = b + 15

        # Semi-transparent dark background for readability
        pad_x, pad_y = 20, 8
        draw.rounded_rectangle(
            [label_x - pad_x, label_y - pad_y,
             label_x + lw + pad_x, label_y + lh + pad_y],
            radius=10,
            fill=(30, 30, 30, 220),
        )
        draw.text((label_x, label_y), color_display, font=label_font, fill=(255, 255, 255))

    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path, "JPEG", quality=92)
    print(f"  Saved: {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create MonoMap 6-color showcase")
    parser.add_argument("--city", help="Generate for specific city folder")
    parser.add_argument("--all", "-a", action="store_true", help="Copy to all city folders")
    args = parser.parse_args()

    # Always generate the shared showcase first
    shared_path = str(RENDERS_DIR / "MonoMap" / "shared_6color_labeled.jpg")
    print("Generating shared 6-color showcase...")
    result = create_6color_showcase(shared_path)

    if not result:
        print("Failed to generate showcase!")
        return

    if args.city:
        # Copy to specific city folder
        import shutil
        dest = RENDERS_DIR / f"{args.city}_monomap" / f"{args.city}_6color_labeled.jpg"
        shutil.copy2(shared_path, str(dest))
        print(f"  Copied to: {dest}")

    elif args.all:
        # Copy to all monomap city folders
        import shutil
        from etsy.city_list import ALL_CITIES
        copied = 0
        for city in ALL_CITIES:
            city_dir = RENDERS_DIR / f"{city.slug}_monomap"
            if city_dir.exists():
                dest = city_dir / f"{city.slug}_6color_labeled.jpg"
                shutil.copy2(shared_path, str(dest))
                copied += 1
        print(f"\nCopied to {copied} city folders")


if __name__ == "__main__":
    main()
