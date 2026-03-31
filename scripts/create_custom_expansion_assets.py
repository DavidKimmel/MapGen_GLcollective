"""Generate mockups, detail crops, and hero images for custom expansion listings.

Requires sample renders to already exist in etsy/renders/CustomExpansion/{slug}/.
Run render_custom_expansion_samples.py first.

Usage:
    python scripts/create_custom_expansion_assets.py --listing where_we_met
    python scripts/create_custom_expansion_assets.py --all
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path("etsy/renders/CustomExpansion")
FONTS_DIR = Path("fonts")


def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a font from the fonts directory, fall back to default."""
    path = FONTS_DIR / name
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def create_detail_crop(listing_slug: str, source_16x20: str) -> str | None:
    """Create a detail crop with 'EVERY STREET. EVERY DETAIL.' badge.

    Uses the same approach as etsy/image_composer.py._draw_detail_badge().
    """
    source = Path(source_16x20)
    if not source.exists():
        print(f"  Source not found for detail crop: {source}")
        return None

    img = Image.open(source)
    w, h = img.size

    # Determine map area based on style
    # Blueprint: map starts at 22% from top; Classic/date_night: map is top 76%
    if "blueprint" in listing_slug:
        map_top = int(h * 0.22)
        map_bottom = h
    else:
        map_top = 0
        map_bottom = int(h * 0.76)

    map_h = map_bottom - map_top
    # Center 40% crop
    crop_size = int(min(w, map_h) * 0.6)
    cx = w // 2
    cy = map_top + map_h // 2
    left = cx - crop_size // 2
    top = cy - crop_size // 2
    right = left + crop_size
    bottom = top + crop_size

    # Clamp to image bounds
    left = max(0, left)
    top = max(0, top)
    right = min(w, right)
    bottom = min(h, bottom)

    cropped = img.crop((left, top, right, bottom))
    cropped = cropped.resize((2000, 2000), Image.LANCZOS)

    # Draw badge
    draw = ImageDraw.Draw(cropped)
    badge_font = _load_font("CenturyGothic-Bold.ttf", 42)
    badge_text = "EVERY STREET. EVERY DETAIL."
    margin = int(2000 * 0.04)

    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 24, 16

    rx = margin
    ry = margin
    rw = tw + pad_x * 2
    rh = th + pad_y * 2

    draw.rounded_rectangle(
        [rx, ry, rx + rw, ry + rh],
        radius=12,
        fill=(30, 30, 30, 200),
    )
    draw.text(
        (rx + pad_x, ry + pad_y),
        badge_text,
        font=badge_font,
        fill=(255, 255, 255),
    )

    out_path = BASE_DIR / listing_slug / "detail_crop.jpg"
    cropped.save(str(out_path), "JPEG", quality=92, dpi=(300, 300))
    print(f"  Detail crop: {out_path}")
    return str(out_path)


def create_style_showcase(listing_slug: str) -> str | None:
    """Create a 3x2 grid showing the same city in 6 themes (multi_style_map only).

    Each cell shows the 16x20 render with a label below.
    """
    if listing_slug != "multi_style_map":
        return None

    themes = [
        ("style_nashville_classic_16x20.png", "Classic B&W"),
        ("style_nashville_midnight_16x20.png", "Midnight Blue"),
        ("style_nashville_clay_16x20.png", "Clay & Sage"),
        ("style_nashville_beige_16x20.png", "Warm Beige"),
        ("style_nashville_watercolor_16x20.png", "Watercolor"),
        ("style_nashville_vintage_16x20.png", "Vintage"),
    ]

    src_dir = BASE_DIR / listing_slug
    images = []
    for filename, label in themes:
        path = src_dir / filename
        if not path.exists():
            print(f"  Missing for showcase: {path}")
            return None
        images.append((Image.open(path), label))

    # Layout: 3 columns x 2 rows
    cell_w, cell_h = 800, 1000
    label_h = 80
    padding = 30
    cols, rows = 3, 2
    canvas_w = cols * cell_w + (cols + 1) * padding
    canvas_h = rows * (cell_h + label_h) + (rows + 1) * padding + 100  # +100 for title

    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    # Title
    title_font = _load_font("Montserrat-Bold.ttf", 64)
    title = "Choose Your Style"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    draw.text(((canvas_w - title_w) // 2, 30), title, font=title_font, fill=(40, 40, 40))

    label_font = _load_font("Montserrat-Bold.ttf", 48)

    for i, (img, label) in enumerate(images):
        col = i % cols
        row = i // cols
        x = padding + col * (cell_w + padding)
        y = 100 + padding + row * (cell_h + label_h + padding)

        # Resize render to fit cell
        img_resized = img.copy()
        img_resized.thumbnail((cell_w, cell_h), Image.LANCZOS)
        # Center in cell
        ox = x + (cell_w - img_resized.width) // 2
        oy = y + (cell_h - img_resized.height) // 2
        canvas.paste(img_resized, (ox, oy))

        # Label
        lbbox = draw.textbbox((0, 0), label, font=label_font)
        lw = lbbox[2] - lbbox[0]
        lx = x + (cell_w - lw) // 2
        ly = y + cell_h + 10
        draw.text((lx, ly), label, font=label_font, fill=(60, 60, 60))

    out_path = src_dir / "style_showcase.jpg"
    canvas.save(str(out_path), "JPEG", quality=92)
    print(f"  Style showcase: {out_path}")
    return str(out_path)


def generate_assets(listing_slug: str) -> None:
    """Generate all assets for one listing."""
    src_dir = BASE_DIR / listing_slug
    if not src_dir.exists():
        print(f"  Directory not found: {src_dir}")
        return

    # Find the first 16x20 render for detail crop
    renders_16x20 = sorted(src_dir.glob("*_16x20.png"))
    if renders_16x20:
        create_detail_crop(listing_slug, str(renders_16x20[0]))
    else:
        print(f"  No 16x20 render found for detail crop in {src_dir}")

    # Style showcase (multi_style_map only)
    if listing_slug == "multi_style_map":
        create_style_showcase(listing_slug)

    # Note: Full PSD mockups use etsy/mockup_composer.py which requires
    # the renders to be in the expected directory structure. For custom
    # expansion listings, mockups can be generated by running:
    #   python -m etsy.mockup_composer --city <slug> --source-dir <path>
    # This is done manually after renders are ready.
    print(f"  Assets complete for {listing_slug}")
    print(f"  For mockups, run: python -m etsy.mockup_composer with renders from {src_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate custom expansion assets")
    parser.add_argument("--listing", "-l", help="Generate assets for one listing")
    parser.add_argument("--all", "-a", action="store_true", help="Generate all")
    args = parser.parse_args()

    if args.all:
        for slug in ["where_we_met", "graduation_map", "multi_style_map",
                      "born_in_map", "custom_blueprint"]:
            print(f"\n=== {slug} ===")
            generate_assets(slug)
    elif args.listing:
        print(f"=== {args.listing} ===")
        generate_assets(args.listing)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
