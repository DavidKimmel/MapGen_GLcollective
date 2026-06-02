"""Generate a size comparison graphic for Florence custom listing.

Matches competitor layout: 3 rows grouped by US/EU, detail circle
top-right, printing info mid-right, faded map background.

Layout (left ~60% of canvas):
  Row 1 (US large):  24x36, 18x24, 16x20
  Row 2 (US small):  11x14, 8x10
  Row 3 (EU/ISO):    A1, 50x70cm, A2, A3

Right side:
  Detail crop circle (top), Printing Information (middle)
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

FONTS_DIR = os.path.join(PROJECT_ROOT, "fonts")

# Canvas
CANVAS_W = 2000
CANVAS_H = 2000
BG_COLOR = "#F0EBE1"

# ─── SIZE DEFINITIONS: (label, subtitle, width_in, height_in) ───────────────
# US sizes
ROW1 = [
    ("24x36", "Ratio 2:3", 24, 36),
    ("18x24", "Ratio 3:4", 18, 24),
    ("16x20", "Ratio 4:5", 16, 20),
]
ROW2 = [
    ("11x14", "Ratio ~4:5", 11, 14),
    ("8x10", "Ratio 4:5", 8, 10),
]
# EU/ISO sizes
ROW3 = [
    ("A1", "59.4×84.1 cm", 23.4, 33.1),
    ("50x70cm", "50×70 cm", 19.7, 27.6),
    ("A2", "42×59.4 cm", 16.5, 23.4),
    ("A3", "29.7×42 cm", 11.7, 16.5),
]


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a font, trying project fonts first."""
    if bold:
        candidates = [os.path.join(FONTS_DIR, "Switzer-Bold.ttf"),
                      "georgiab.ttf", "arialbd.ttf"]
    else:
        candidates = ["georgia.ttf", "arial.ttf", "calibri.ttf"]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _load_italic_font(size: int) -> ImageFont.FreeTypeFont:
    """Load an italic font for the Printing Information title."""
    candidates = ["georgiai.ttf", "ITCKRIST.TTF", "ariali.ttf", "calibrii.ttf"]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except OSError:
            continue
    return _load_font(size, bold=True)


def _add_shadow(poster_img: Image.Image, offset: int = 10) -> Image.Image:
    """Add a subtle drop shadow behind a poster thumbnail."""
    shadow_color = (160, 155, 145, 140)
    w, h = poster_img.size
    pad = offset * 3
    result = Image.new("RGBA", (w + pad, h + pad), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (w, h), shadow_color)
    result.paste(shadow, (offset * 2, offset * 2))
    result = result.filter(ImageFilter.GaussianBlur(radius=offset + 2))
    result.paste(poster_img, (0, 0))
    return result


def _make_bg_detail(poster_path: str, canvas_size: tuple[int, int]) -> Image.Image:
    """Create a faded zoomed-in map background."""
    poster = Image.open(poster_path).convert("RGBA")
    pw, ph = poster.size
    map_crop = poster.crop((0, 0, pw, int(ph * 0.75)))
    cw, ch = canvas_size
    sc = max(cw / map_crop.width, ch / map_crop.height) * 1.3
    scaled = map_crop.resize((int(map_crop.width * sc), int(map_crop.height * sc)),
                             Image.LANCZOS)
    sx = (scaled.width - cw) // 2
    sy = (scaled.height - ch) // 2
    bg = scaled.crop((sx, sy, sx + cw, sy + ch))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=30))
    cream = Image.new("RGBA", canvas_size, (240, 235, 225, 210))
    bg = Image.alpha_composite(bg, cream)
    return bg.convert("RGB")


def _make_detail_circle(poster_path: str, diameter: int = 380) -> Image.Image:
    """Create a circular detail crop from the poster map area."""
    poster = Image.open(poster_path).convert("RGBA")
    pw, ph = poster.size
    cx, cy = int(pw * 0.45), int(ph * 0.30)
    crop_r = int(diameter * 1.8)
    detail = poster.crop((cx - crop_r, cy - crop_r, cx + crop_r, cy + crop_r))
    detail = detail.resize((diameter, diameter), Image.LANCZOS)

    mask = Image.new("L", (diameter, diameter), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse([0, 0, diameter - 1, diameter - 1], fill=255)

    border_w = 8
    total = diameter + border_w * 2
    result = Image.new("RGBA", (total, total), (0, 0, 0, 0))
    bd = ImageDraw.Draw(result)
    bd.ellipse([0, 0, total - 1, total - 1], fill=(255, 255, 255, 255))

    circle = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    circle.paste(detail, (0, 0), mask)
    result.paste(circle, (border_w, border_w), circle)

    return result


def create_size_graphic(
    poster_path: str,
    output_path: str,
) -> str:
    """Create the full size comparison graphic."""

    # Scale: 24x36 (tallest) should be about 560px tall
    max_display_h = 560
    scale = max_display_h / 36  # ~15.6 px per inch

    poster_full = Image.open(poster_path).convert("RGB")

    canvas = _make_bg_detail(poster_path, (CANVAS_W, CANVAS_H))
    draw = ImageDraw.Draw(canvas)

    # Fonts
    size_font = _load_font(38, bold=True)
    sub_font = _load_font(24, bold=False)
    info_title_font = _load_italic_font(42)
    info_font = _load_font(32, bold=False)
    text_color = "#2C3E50"
    sub_color = "#7A7A6A"

    # Poster area = left 60% of canvas
    POSTER_AREA_W = int(CANVAS_W * 0.60)

    def draw_poster(x: int, y: int, w_in: float, h_in: float,
                    label: str, subtitle: str) -> None:
        """Draw a scaled poster thumbnail with shadow and label."""
        pw = int(w_in * scale)
        ph = int(h_in * scale)
        thumb = poster_full.resize((pw, ph), Image.LANCZOS)

        shadowed = _add_shadow(thumb, offset=8)
        sx, sy = x - 8, y - 8
        canvas.paste(shadowed.convert("RGB"), (sx, sy),
                     shadowed.split()[3] if shadowed.mode == "RGBA" else None)

        # Bold size label centered below poster
        label_y = y + ph + 18
        bbox = draw.textbbox((0, 0), label, font=size_font)
        lw = bbox[2] - bbox[0]
        draw.text((x + pw // 2 - lw // 2, label_y), label,
                  fill=text_color, font=size_font)

        # Lighter subtitle
        sub_y = label_y + 44
        bbox2 = draw.textbbox((0, 0), subtitle, font=sub_font)
        sw = bbox2[2] - bbox2[0]
        draw.text((x + pw // 2 - sw // 2, sub_y), subtitle,
                  fill=sub_color, font=sub_font)

    def draw_row(row_data: list, y_top: int, tallest_h_in: float,
                 gap: int = 50) -> None:
        """Draw a row of posters, bottom-aligned, centered in poster area."""
        widths = [int(s[2] * scale) for s in row_data]
        total_w = sum(widths) + gap * (len(row_data) - 1)
        x_start = (POSTER_AREA_W - total_w) // 2
        draw_row_aligned(row_data, y_top, tallest_h_in, x_start, gap)

    def draw_row_aligned(row_data: list, y_top: int, tallest_h_in: float,
                         x_start: int, gap: int = 50) -> None:
        """Draw a row of posters, bottom-aligned, starting at x_start."""
        x_cursor = x_start
        tallest_ph = int(tallest_h_in * scale)
        for label, subtitle, w_in, h_in in row_data:
            ph = int(h_in * scale)
            y_offset = tallest_ph - ph  # bottom-align
            draw_poster(x_cursor, y_top + y_offset, w_in, h_in, label, subtitle)
            x_cursor += int(w_in * scale) + gap

    # ─── Compute row 1 left edge so we can align row 3 to it ──────────
    row1_widths = [int(s[2] * scale) for s in ROW1]
    row1_total = sum(row1_widths) + 45 * (len(ROW1) - 1)
    row1_x_start = (POSTER_AREA_W - row1_total) // 2

    # ─── ROW 1: US LARGE (24x36, 18x24, 16x20) ────────────────────────
    row1_y = 100  # more headroom — push everything down
    draw_row(ROW1, row1_y, ROW1[0][3], gap=45)

    # ─── ROW 2: US SMALL (11x14, 8x10) ─────────────────────────────────
    row1_bottom = row1_y + int(ROW1[0][3] * scale) + 90
    draw_row(ROW2, row1_bottom, ROW2[0][3], gap=50)

    # ─── ROW 3: EU/ISO (A1, 50x70, A2, A3) ─────────────────────────────
    # Left-align with row 1's left edge instead of centering
    row2_bottom = row1_bottom + int(ROW2[0][3] * scale) + 140
    draw_row_aligned(ROW3, row2_bottom, ROW3[0][3], x_start=row1_x_start, gap=40)

    # ─── DETAIL CROP CIRCLE (top right) ─────────────────────────────────
    circle_diam = 380
    circle = _make_detail_circle(poster_path, diameter=circle_diam)
    circle_x = CANVAS_W - circle.width - 80
    circle_y = 60
    canvas.paste(circle.convert("RGB"), (circle_x, circle_y),
                 circle.split()[3] if circle.mode == "RGBA" else None)

    # ─── PRINTING INFO (right side, below circle) ───────────────────────
    info_center_x = circle_x + circle.width // 2
    info_y = circle_y + circle.height + 60

    # Title — italic, centered
    title_text = "Printing Information"
    bbox = draw.textbbox((0, 0), title_text, font=info_title_font)
    tw = bbox[2] - bbox[0]
    title_x = info_center_x - tw // 2
    draw.text((title_x, info_y), title_text, fill=text_color, font=info_title_font)

    # Underline
    draw.line([(title_x, info_y + 52), (title_x + tw, info_y + 52)],
              fill=text_color, width=2)

    info_lines = [
        "-175 gsm fine art paper",
        "-Matte finish",
        "-For indoor use",
        "-Unframed",
        "-300+ DPI print quality",
    ]
    for i, line in enumerate(info_lines):
        bbox = draw.textbbox((0, 0), line, font=info_font)
        lw = bbox[2] - bbox[0]
        lx = info_center_x - lw // 2
        draw.text((lx, info_y + 80 + i * 48), line,
                  fill=text_color, font=info_font)

    # ─── SAVE ────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    canvas.save(output_path, quality=95)
    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"Size graphic saved: {output_path} ({size_mb:.1f} MB)")
    return output_path


if __name__ == "__main__":
    poster = os.path.join(
        PROJECT_ROOT,
        "etsy", "renders", "CustomArtFlorenceMap",
        "your_city_florence_nola_24x36.png",
    )
    output = os.path.join(
        PROJECT_ROOT,
        "etsy", "renders", "CustomArtFlorenceMap",
        "size_comparison.jpg",
    )
    create_size_graphic(poster, output)
