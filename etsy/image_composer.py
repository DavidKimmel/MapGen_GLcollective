"""GeoLine Collective — Automated Etsy Listing Image Composer.

Generates listing images from rendered posters:
  - Detail crop: zoomed center section showing cartographic quality
  - Style grid: all 5 brand styles in a single comparison image
  - Size comparison: 3 sizes side-by-side with labels

Usage:
    python -m etsy.image_composer --city Chicago --detail-crop
    python -m etsy.image_composer --city Chicago --style-grid
    python -m etsy.image_composer --city Chicago --all
"""

import argparse
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RENDERS_DIR = os.path.join(os.path.dirname(__file__), "renders")
FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")

# Brand style names mapped to theme file basenames
BRAND_STYLES = {
    "Classic": "37th_parallel",
    "Midnight": "midnight_blue",
    "Sepia": "warm_beige",
    "Minimal": "minimalist",
    "Terracotta": "terracotta",
}

# Standard Etsy listing image size (2000x2000 recommended, 4:3 or 1:1)
LISTING_IMAGE_WIDTH = 2000
LISTING_IMAGE_HEIGHT = 2000


def _get_font(size: int = 36) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Get a clean sans-serif font for labels."""
    # Try Montserrat first (matches brand), fall back to Arial, then default
    for name in ("Montserrat-Medium.ttf", "Montserrat-Regular.ttf"):
        path = os.path.join(FONTS_DIR, name)
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _find_render(city_slug: str, theme: str = "37th_parallel",
                 size: str = "16x20") -> str | None:
    """Find a rendered poster PNG for a city."""
    path = os.path.join(RENDERS_DIR, city_slug, f"{city_slug}_{theme}_{size}.png")
    if os.path.exists(path):
        return path
    return None


def create_detail_crop(city_slug: str, output_dir: str | None = None) -> str | None:
    """Create a zoomed detail crop showing cartographic quality.

    Crops the center ~25% of the map area (excluding text zone) and
    scales to 2000x2000 for Etsy listing image.
    """
    poster_path = _find_render(city_slug)
    if not poster_path:
        print(f"  [!] No render found for {city_slug}")
        return None

    img = Image.open(poster_path)
    w, h = img.size

    # The map area is roughly the top 76% of the poster (bottom 24% is text)
    map_bottom = int(h * 0.76)

    # Crop center 40% of the map area
    crop_size = int(min(w, map_bottom) * 0.4)
    cx = w // 2
    cy = map_bottom // 2
    left = cx - crop_size // 2
    top = cy - crop_size // 2
    right = left + crop_size
    bottom = top + crop_size

    cropped = img.crop((left, top, right, bottom))
    result = cropped.resize((LISTING_IMAGE_WIDTH, LISTING_IMAGE_HEIGHT), Image.LANCZOS)

    out_dir = output_dir or os.path.join(RENDERS_DIR, city_slug)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{city_slug}_detail_crop.png")
    result.save(out_path, "PNG", dpi=(300, 300))
    print(f"  [OK] Detail crop: {out_path}")
    return out_path


def create_style_grid(city_slug: str, output_dir: str | None = None) -> str | None:
    """Create a grid showing all 5 brand styles for a city.

    Layout: 2 rows x 3 columns (5 styles + label in 6th cell).
    Each cell shows a scaled-down poster with the style name below.
    """
    # For now, only 37th_parallel is rendered for bulk cities.
    # This function is ready for when multiple styles are rendered.
    available: list[tuple[str, str, Image.Image]] = []
    for style_name, theme in BRAND_STYLES.items():
        path = _find_render(city_slug, theme=theme)
        if path:
            available.append((style_name, path, Image.open(path)))

    if not available:
        print(f"  [!] No renders found for {city_slug}")
        return None

    if len(available) == 1:
        print(f"  [!] Only 1 style found for {city_slug} — need 2+ for a grid")
        return None

    # Layout calculation
    cols = min(3, len(available))
    rows = (len(available) + cols - 1) // cols

    padding = 40
    label_height = 60
    cell_w = (LISTING_IMAGE_WIDTH - padding * (cols + 1)) // cols
    cell_h = int(cell_w / 0.8)  # 16x20 aspect ratio = 0.8

    canvas_w = LISTING_IMAGE_WIDTH
    canvas_h = padding + rows * (cell_h + label_height + padding)

    canvas = Image.new("RGB", (canvas_w, canvas_h), "#FFFFFF")
    draw = ImageDraw.Draw(canvas)
    font = _get_font(32)

    for i, (style_name, path, img) in enumerate(available):
        col = i % cols
        row = i // cols
        x = padding + col * (cell_w + padding)
        y = padding + row * (cell_h + label_height + padding)

        # Scale poster to fit cell
        thumb = img.resize((cell_w, cell_h), Image.LANCZOS)
        canvas.paste(thumb, (x, y))

        # Draw label centered below
        label_y = y + cell_h + 8
        bbox = draw.textbbox((0, 0), style_name, font=font)
        text_w = bbox[2] - bbox[0]
        draw.text((x + (cell_w - text_w) // 2, label_y), style_name,
                  fill="#333333", font=font)

    out_dir = output_dir or os.path.join(RENDERS_DIR, city_slug)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{city_slug}_style_grid.png")
    canvas.save(out_path, "PNG", dpi=(150, 150))
    print(f"  [OK] Style grid ({len(available)} styles): {out_path}")
    return out_path


def create_size_comparison(city_slug: str, output_dir: str | None = None) -> str | None:
    """Create a size comparison image showing 3 sizes side by side.

    Shows 8x10, 16x20, and 24x36 at relative scale with labels.
    """
    poster_path = _find_render(city_slug)
    if not poster_path:
        print(f"  [!] No render found for {city_slug}")
        return None

    img = Image.open(poster_path)

    # Define sizes to show (relative proportions based on actual inches)
    sizes = [
        ('8×10"', 8, 10),
        ('16×20"', 16, 20),
        ('24×36"', 24, 36),
    ]

    # Scale so the largest fits ~60% of canvas height
    canvas_w = LISTING_IMAGE_WIDTH
    canvas_h = LISTING_IMAGE_HEIGHT
    max_h = int(canvas_h * 0.60)
    scale = max_h / sizes[-1][2]  # pixels per inch based on largest

    padding = 60
    label_height = 80
    font = _get_font(36)
    small_font = _get_font(24)

    canvas = Image.new("RGB", (canvas_w, canvas_h), "#F8F6F2")
    draw = ImageDraw.Draw(canvas)

    # Calculate total width of all posters + gaps
    total_w = sum(int(w * scale) for _, w, _ in sizes) + padding * (len(sizes) - 1)
    start_x = (canvas_w - total_w) // 2

    x = start_x
    baseline_y = canvas_h - 200  # Align bottoms

    for label, w_in, h_in in sizes:
        pw = int(w_in * scale)
        ph = int(h_in * scale)
        y = baseline_y - ph

        # Draw shadow
        shadow_offset = 4
        draw.rectangle(
            [x + shadow_offset, y + shadow_offset, x + pw + shadow_offset, y + ph + shadow_offset],
            fill="#E0E0E0",
        )

        # Scale poster to this size
        thumb = img.resize((pw, ph), Image.LANCZOS)
        canvas.paste(thumb, (x, y))

        # Draw thin border
        draw.rectangle([x, y, x + pw, y + ph], outline="#CCCCCC", width=2)

        # Label below
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        draw.text(
            (x + (pw - text_w) // 2, baseline_y + 20),
            label, fill="#333333", font=font,
        )

        x += pw + padding

    # Title at top
    title = "Available Sizes"
    bbox = draw.textbbox((0, 0), title, font=_get_font(48))
    tw = bbox[2] - bbox[0]
    draw.text(((canvas_w - tw) // 2, 60), title, fill="#1A1A1A", font=_get_font(48))

    out_dir = output_dir or os.path.join(RENDERS_DIR, city_slug)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{city_slug}_size_comparison.png")
    canvas.save(out_path, "PNG", dpi=(150, 150))
    print(f"  [OK] Size comparison: {out_path}")
    return out_path


def generate_all_images(city_slug: str, output_dir: str | None = None) -> dict:
    """Generate all automated listing images for a city.

    Returns dict of image type -> file path (or None if failed).
    """
    print(f"\nGenerating listing images for: {city_slug}")
    return {
        "detail_crop": create_detail_crop(city_slug, output_dir),
        "style_grid": create_style_grid(city_slug, output_dir),
        "size_comparison": create_size_comparison(city_slug, output_dir),
    }


def main():
    parser = argparse.ArgumentParser(description="Generate Etsy listing images")
    parser.add_argument("--city", required=True, help="City name")
    parser.add_argument("--detail-crop", action="store_true", help="Generate detail crop")
    parser.add_argument("--style-grid", action="store_true", help="Generate style grid")
    parser.add_argument("--size-comparison", action="store_true", help="Generate size comparison")
    parser.add_argument("--all", action="store_true", help="Generate all image types")
    parser.add_argument("--output-dir", default=None, help="Output directory override")
    args = parser.parse_args()

    from etsy.city_list import get_city
    city = get_city(args.city)
    if not city:
        print(f"City not found: {args.city}")
        sys.exit(1)

    slug = city.slug

    if args.all or not (args.detail_crop or args.style_grid or args.size_comparison):
        generate_all_images(slug, args.output_dir)
    else:
        if args.detail_crop:
            create_detail_crop(slug, args.output_dir)
        if args.style_grid:
            create_style_grid(slug, args.output_dir)
        if args.size_comparison:
            create_size_comparison(slug, args.output_dir)


if __name__ == "__main__":
    main()
