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


def _get_font(size: int = 36, weight: str = "regular") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Get a clean sans-serif font for labels.

    Args:
        size: Font size in points.
        weight: "regular", "light", or "bold".
    """
    if weight == "light":
        candidates = ["Roboto-Light.ttf", "Montserrat-Variable.ttf"]
    elif weight == "bold":
        candidates = ["Roboto-Bold.ttf", "Montserrat-Variable.ttf"]
    else:
        candidates = ["Montserrat-Variable.ttf", "Roboto-Regular.ttf"]
    for name in candidates:
        path = os.path.join(FONTS_DIR, name)
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _find_render(city_slug: str, theme: str = "37th_parallel",
                 size: str = "16x20") -> str | None:
    """Find a rendered poster PNG for a city.

    For the default theme (37th_parallel), filenames omit the theme name.
    Other themes include it.
    """
    if theme == "37th_parallel":
        path = os.path.join(RENDERS_DIR, city_slug, f"{city_slug}_{size}.png")
    else:
        path = os.path.join(RENDERS_DIR, city_slug, f"{city_slug}_{theme}_{size}.png")
    if os.path.exists(path):
        return path
    return None


def _draw_detail_badge(img: Image.Image) -> Image.Image:
    """Draw a corner badge overlay showing detail/quality text.

    Places a semi-transparent badge in the top-left corner with
    headline and subtitle text.
    """
    result = img.convert("RGBA")
    w, h = result.size

    # Badge dimensions relative to image size
    margin = int(w * 0.04)
    pad_x = int(w * 0.025)
    pad_y = int(w * 0.018)

    # Fonts
    headline_font = _get_font(int(w * 0.032), weight="bold")
    subtitle_font = _get_font(int(w * 0.018), weight="light")

    # Text content — two lines drawn as a single block
    full_text = "EVERY STREET.\nEVERY DETAIL."

    # Measure the full text block
    dummy = ImageDraw.Draw(result)
    bb = dummy.multiline_textbbox((0, 0), full_text, font=headline_font, align="center")
    text_w = bb[2] - bb[0]
    text_h = bb[3] - bb[1]

    badge_w = int(text_w + pad_x * 2)
    badge_h = int(text_h + pad_y * 2)

    # Draw semi-transparent badge background
    badge = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
    badge_draw = ImageDraw.Draw(badge)

    # Rounded rectangle background (dark, semi-transparent)
    radius = int(min(badge_w, badge_h) * 0.06)
    badge_draw.rounded_rectangle(
        [0, 0, badge_w - 1, badge_h - 1],
        radius=radius,
        fill=(26, 26, 26, 185),
    )

    # Draw text centered both horizontally and vertically using anchor
    cx = badge_w // 2
    cy = badge_h // 2
    badge_draw.multiline_text(
        (cx, cy), full_text,
        fill=(255, 255, 255, 240), font=headline_font,
        anchor="mm", align="center",
    )

    # Paste badge onto image
    result.paste(badge, (margin, margin), badge)
    return result.convert("RGB")


def create_detail_crop(city_slug: str, output_dir: str | None = None,
                       with_badge: bool = True) -> str | None:
    """Create a zoomed detail crop showing cartographic quality.

    Crops the center ~25% of the map area (excluding text zone) and
    scales to 2000x2000 for Etsy listing image. Optionally adds a
    corner badge with detail/quality text.
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

    if with_badge:
        result = _draw_detail_badge(result)

    out_dir = output_dir or os.path.join(RENDERS_DIR, city_slug)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{city_slug}_detail_crop.jpg")
    result.save(out_path, "JPEG", quality=92, dpi=(300, 300))
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
    Uses Montserrat title, Roboto Light labels, dark frame outlines.
    """
    poster_path = _find_render(city_slug)
    if not poster_path:
        print(f"  [!] No render found for {city_slug}")
        return None

    img = Image.open(poster_path)

    sizes = [
        ('8×10"', 8, 10),
        ('16×20"', 16, 20),
        ('24×36"', 24, 36),
    ]

    canvas_w = LISTING_IMAGE_WIDTH
    canvas_h = LISTING_IMAGE_HEIGHT

    # Scale so the largest fits ~65% of canvas height
    max_h = int(canvas_h * 0.65)
    scale = max_h / sizes[-1][2]

    title_font = _get_font(56)
    label_font = _get_font(32, weight="light")

    canvas = Image.new("RGB", (canvas_w, canvas_h), "#F8F6F2")
    draw = ImageDraw.Draw(canvas)

    # Title — "AVAILABLE SIZES" with letter spacing
    title = "AVAILABLE SIZES"
    spaced_title = "  ".join(title)
    bbox = draw.textbbox((0, 0), spaced_title, font=title_font)
    tw = bbox[2] - bbox[0]
    draw.text(((canvas_w - tw) // 2, 70), spaced_title, fill="#1A1A1A", font=title_font)

    # Calculate layout
    padding = 50
    total_w = sum(int(w * scale) for _, w, _ in sizes) + padding * (len(sizes) - 1)
    start_x = (canvas_w - total_w) // 2
    baseline_y = canvas_h - 160

    x = start_x
    for label, w_in, h_in in sizes:
        pw = int(w_in * scale)
        ph = int(h_in * scale)
        y = baseline_y - ph

        # Subtle shadow — offset and blurred look
        shadow_offset = 6
        for s in range(3, 0, -1):
            alpha_color = "#E8E4E0" if s == 3 else ("#E0DCDA" if s == 2 else "#D8D4D0")
            draw.rectangle(
                [x + shadow_offset + s, y + shadow_offset + s,
                 x + pw + shadow_offset + s, y + ph + shadow_offset + s],
                fill=alpha_color,
            )

        # Scale poster to this size
        thumb = img.resize((pw, ph), Image.LANCZOS)
        canvas.paste(thumb, (x, y))

        # Dark frame outline (thin)
        frame_color = "#2C2C2C"
        draw.rectangle([x, y, x + pw, y + ph], outline=frame_color, width=2)

        # Size label below — centered
        bbox = draw.textbbox((0, 0), label, font=label_font)
        text_w = bbox[2] - bbox[0]
        draw.text(
            (x + (pw - text_w) // 2, baseline_y + 16),
            label, fill="#444444", font=label_font,
        )

        x += pw + padding

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
    parser.add_argument("--city", default=None, help="City name")
    parser.add_argument("--detail-crop", action="store_true", help="Generate detail crop")
    parser.add_argument("--style-grid", action="store_true", help="Generate style grid")
    parser.add_argument("--size-comparison", action="store_true", help="Generate size comparison")
    parser.add_argument("--all", action="store_true", help="Generate all image types")
    parser.add_argument("--batch-all", action="store_true",
                        help="Generate images for all rendered cities")
    parser.add_argument("--output-dir", default=None, help="Output directory override")
    args = parser.parse_args()

    if args.batch_all:
        # Find all city dirs that have a rendered poster
        for city_dir in sorted(Path(RENDERS_DIR).iterdir()):
            if not city_dir.is_dir():
                continue
            slug = city_dir.name
            poster = city_dir / f"{slug}_16x20.png"
            if poster.exists():
                generate_all_images(slug, args.output_dir)
        return

    if not args.city:
        parser.error("--city is required (or use --batch-all)")

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
