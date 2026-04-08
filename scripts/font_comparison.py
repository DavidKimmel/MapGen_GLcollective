#!/usr/bin/env python3
"""
Render font combo comparison sheet for CountyMap product.
Shows each combo as it would appear on a poster — county name, state, coords.
All on one canvas for quick visual comparison.
"""

import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = os.path.join(_PROJECT_DIR, "fonts", "county_candidates")
OUTPUT_DIR = os.path.join(_PROJECT_DIR, "etsy", "renders", "CountyMap")

# Sample text matching our poster layout
COUNTY_NAME = "FAIRFAX COUNTY"
STATE = "VIRGINIA"
COORDS = "38.8368° N   77.2770° W"

# Font combos to test: (label, title_font, title_weight, subtitle_font, sub_weight, coord_font, coord_weight)
COMBOS = [
    {
        "label": "A — Space Grotesk + Space Grotesk Light",
        "title": ("SpaceGrotesk-Bold.ttf", 1.0),
        "state": ("SpaceGrotesk-Light.ttf", 0.5),
        "coords": ("SpaceGrotesk-Light.ttf", 0.35),
        "note": "Techy, modern, cartographic",
    },
    {
        "label": "B — Urbanist + JetBrains Mono",
        "title": ("Urbanist-Bold.ttf", 1.0),
        "state": ("Urbanist-Light.ttf", 0.5),
        "coords": ("JetBrainsMono-Light.ttf", 0.35),
        "note": "Clean and city-focused",
    },
    {
        "label": "C — Cormorant Garamond + Space Grotesk",
        "title": ("CormorantGaramond-SemiBold.ttf", 1.0),
        "state": ("SpaceGrotesk-Light.ttf", 0.5),
        "coords": ("SpaceGrotesk-Light.ttf", 0.35),
        "note": "Elegant serif title, modern details",
    },
    {
        "label": "D — Cormorant Garamond + JetBrains Mono",
        "title": ("CormorantGaramond-Bold.ttf", 1.0),
        "state": ("CormorantGaramond-Light.ttf", 0.5),
        "coords": ("JetBrainsMono-Light.ttf", 0.35),
        "note": "Classic serif + techy coords",
    },
    {
        "label": "E — Space Grotesk + JetBrains Mono",
        "title": ("SpaceGrotesk-Bold.ttf", 1.0),
        "state": ("SpaceGrotesk-Light.ttf", 0.5),
        "coords": ("JetBrainsMono-Light.ttf", 0.35),
        "note": "Full techy/cartographic stack",
    },
    {
        "label": "F — Urbanist + Urbanist Light",
        "title": ("Urbanist-Bold.ttf", 1.0),
        "state": ("Urbanist-Light.ttf", 0.5),
        "coords": ("Urbanist-Light.ttf", 0.35),
        "note": "Clean single-family, city-focused",
    },
    {
        "label": "G — Syne + Inconsolata",
        "title": ("Syne-Bold.ttf", 1.0),
        "state": ("Syne-Regular.ttf", 0.5),
        "coords": ("Inconsolata-Light.ttf", 0.38),
        "note": "Artistic/distinctive — your Mosaic pick",
    },
    {
        "label": "H — Syne ExtraBold + Inconsolata",
        "title": ("Syne-ExtraBold.ttf", 1.0),
        "state": ("Syne-Medium.ttf", 0.5),
        "coords": ("Inconsolata-Regular.ttf", 0.35),
        "note": "Bolder variant of the Syne combo",
    },
    {
        "label": "I — Cormorant Garamond (all weights)",
        "title": ("CormorantGaramond-Bold.ttf", 1.0),
        "state": ("CormorantGaramond-Regular.ttf", 0.5),
        "coords": ("CormorantGaramond-Light.ttf", 0.35),
        "note": "Full serif elegance",
    },
    {
        "label": "J — Syne + JetBrains Mono",
        "title": ("Syne-Bold.ttf", 1.0),
        "state": ("Syne-Regular.ttf", 0.5),
        "coords": ("JetBrainsMono-Light.ttf", 0.35),
        "note": "Artistic title + techy coords",
    },
]

# Layout
CELL_W = 900
CELL_H = 400
COLS = 2
ROWS = (len(COMBOS) + COLS - 1) // COLS
CANVAS_W = CELL_W * COLS + 40  # 20px margin each side
CANVAS_H = CELL_H * ROWS + 100  # room for header
BG_COLOR = (255, 255, 255)
TEXT_COLOR = (44, 44, 44)      # #2C2C2C
LABEL_COLOR = (120, 120, 120)
DIVIDER_COLOR = (220, 220, 220)

BASE_FONT_SIZE = 52  # title size


def load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = os.path.join(FONTS_DIR, name)
    return ImageFont.truetype(path, size)


def draw_combo(draw: ImageDraw.Draw, x: int, y: int, combo: dict) -> None:
    """Draw one font combo in its cell."""
    # Label (small, gray)
    label_font = ImageFont.truetype(
        os.path.join(FONTS_DIR, "SpaceGrotesk-Regular.ttf"), 16
    )
    draw.text((x + 20, y + 15), combo["label"], fill=LABEL_COLOR, font=label_font)
    draw.text((x + 20, y + 35), combo["note"], fill=(160, 160, 160), font=label_font)

    # County name (title)
    title_file, title_scale = combo["title"]
    title_size = int(BASE_FONT_SIZE * title_scale)
    title_font = load_font(title_file, title_size)

    # Letter-space the title
    title_text = "   ".join(COUNTY_NAME)
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]

    # If too wide with full spacing, reduce
    if title_w > CELL_W - 60:
        title_text = "  ".join(COUNTY_NAME)
        title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
        title_w = title_bbox[2] - title_bbox[0]
    if title_w > CELL_W - 60:
        title_text = " ".join(COUNTY_NAME)
        title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
        title_w = title_bbox[2] - title_bbox[0]

    title_x = x + (CELL_W - title_w) // 2
    title_y = y + 100
    draw.text((title_x, title_y), title_text, fill=TEXT_COLOR, font=title_font)

    # State (subtitle)
    state_file, state_scale = combo["state"]
    state_size = int(BASE_FONT_SIZE * state_scale)
    state_font = load_font(state_file, state_size)
    state_text = "   ".join(STATE)
    state_bbox = draw.textbbox((0, 0), state_text, font=state_font)
    state_w = state_bbox[2] - state_bbox[0]
    state_x = x + (CELL_W - state_w) // 2
    state_y = title_y + title_size + 30
    draw.text((state_x, state_y), state_text, fill=TEXT_COLOR, font=state_font)

    # Coordinates
    coord_file, coord_scale = combo["coords"]
    coord_size = int(BASE_FONT_SIZE * coord_scale)
    coord_font = load_font(coord_file, coord_size)
    coord_bbox = draw.textbbox((0, 0), COORDS, font=coord_font)
    coord_w = coord_bbox[2] - coord_bbox[0]
    coord_x = x + (CELL_W - coord_w) // 2
    coord_y = state_y + state_size + 20
    draw.text((coord_x, coord_y), COORDS, fill=LABEL_COLOR, font=coord_font)


def main() -> None:
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Header
    header_font = ImageFont.truetype(
        os.path.join(FONTS_DIR, "SpaceGrotesk-Bold.ttf"), 28
    )
    draw.text((20, 20), "CountyMap Font Comparison", fill=TEXT_COLOR, font=header_font)

    sub_font = ImageFont.truetype(
        os.path.join(FONTS_DIR, "SpaceGrotesk-Light.ttf"), 16
    )
    draw.text(
        (20, 58),
        "Each combo shown with letter-spaced county name, state, and coordinates",
        fill=LABEL_COLOR,
        font=sub_font,
    )

    # Draw combos in grid
    for i, combo in enumerate(COMBOS):
        col = i % COLS
        row = i // COLS
        cx = 20 + col * CELL_W
        cy = 100 + row * CELL_H

        # Cell divider
        draw.line([(cx, cy), (cx + CELL_W - 20, cy)], fill=DIVIDER_COLOR, width=1)

        draw_combo(draw, cx, cy, combo)

    output = os.path.join(OUTPUT_DIR, "font_comparison.png")
    img.save(output, "PNG")
    print(f"Saved: {output}")
    print(f"Size: {CANVAS_W}x{CANVAS_H}")


if __name__ == "__main__":
    main()
