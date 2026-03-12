"""
Generate a font & pin style sheet image for Etsy listings.

Shows all 5 font presets on the left with sample text,
and all 5 pin styles on the right with rendered icons.

Usage:
    python -m etsy.generate_style_sheet
    python -m etsy.generate_style_sheet --output etsy/style_sheet.png
"""

import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.patches import PathPatch, Circle, FancyBboxPatch
from matplotlib.path import Path as MplPath

# Add project root to path
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from engine.text_layout import FONT_PRESETS, FONTS_DIR, _get_font
from engine.pin_renderer import (
    _svg_path_to_mpl, _svg_heart, _svg_teardrop,
    _FA_PIN_D, _FA_PIN_VBW, _FA_PIN_VBH,
    _FA_HEART_D, _FA_HEART_VBW, _FA_HEART_VBH,
    _FA_HOUSE_D, _FA_HOUSE_VBW, _FA_HOUSE_VBH,
    _FA_GRADCAP_D, _FA_GRADCAP_VBW, _FA_GRADCAP_VBH,
)

# Style sheet colors
BG_COLOR = "#F5F0EB"
ACCENT_COLOR = "#C85C5C"
TEXT_COLOR = "#2C2C2C"
SUBTITLE_COLOR = "#555555"
DIVIDER_COLOR = "#D5CFC8"

# Sample text
TITLE_TEXT = "Stephen & Grace"
LINE2_TEXT = "Where We First Met"
LINE3_TEXT = "16 July 2022"


def _numbered_circle(fig, x, y, number, radius=0.022):
    """Draw a numbered circle badge using an Ellipse for perfect roundness."""
    # Compensate for non-square figure aspect ratio
    fig_w, fig_h = fig.get_size_inches()
    aspect = fig_h / fig_w
    circle = matplotlib.patches.Ellipse(
        (x, y), radius * 2 * aspect, radius * 2,
        transform=fig.transFigure,
        facecolor="none",
        edgecolor=ACCENT_COLOR,
        linewidth=1.8,
        zorder=10,
    )
    fig.patches.append(circle)
    fig.text(
        x, y, str(number),
        color=ACCENT_COLOR,
        fontsize=14,
        fontweight="bold",
        ha="center", va="center",
        fontfamily="sans-serif",
        zorder=11,
    )


def _draw_pin_icon(fig, ax_pin, pin_style, color=ACCENT_COLOR):
    """Draw a pin icon in the given axes."""
    cx, cy = 0.5, 0.5
    size = 0.8

    if pin_style == 1:
        # Solid heart
        path = _svg_path_to_mpl(
            _FA_HEART_D, cx, cy, size,
            _FA_HEART_VBW, _FA_HEART_VBH, anchor="center"
        )
        ax_pin.add_patch(PathPatch(
            path, facecolor=color, edgecolor="none", zorder=5,
        ))

    elif pin_style == 2:
        # Heart in teardrop pin
        path = _svg_path_to_mpl(
            _FA_PIN_D, cx, cy - 0.05, size * 0.9,
            _FA_PIN_VBW, _FA_PIN_VBH, anchor="center"
        )
        ax_pin.add_patch(PathPatch(
            path, facecolor=color, edgecolor="none", zorder=5,
        ))
        # Inner heart
        heart = _svg_path_to_mpl(
            _FA_HEART_D, cx, cy + 0.05, size * 0.3,
            _FA_HEART_VBW, _FA_HEART_VBH, anchor="center"
        )
        ax_pin.add_patch(PathPatch(
            heart, facecolor="white", edgecolor="none", zorder=6,
        ))
        # Shadow ellipse
        shadow = matplotlib.patches.Ellipse(
            (cx, cy - 0.42), 0.35, 0.06,
            facecolor=color, edgecolor="none", alpha=0.25, zorder=4,
        )
        ax_pin.add_patch(shadow)

    elif pin_style == 3:
        # Classic pin with dot
        path = _svg_path_to_mpl(
            _FA_PIN_D, cx, cy - 0.05, size * 0.9,
            _FA_PIN_VBW, _FA_PIN_VBH, anchor="center"
        )
        ax_pin.add_patch(PathPatch(
            path, facecolor=color, edgecolor="none", zorder=5,
        ))
        # Inner circle
        dot = Circle(
            (cx, cy + 0.05), 0.1,
            facecolor="white", edgecolor="none", zorder=6,
        )
        ax_pin.add_patch(dot)
        # Shadow ellipse
        shadow = matplotlib.patches.Ellipse(
            (cx, cy - 0.42), 0.35, 0.06,
            facecolor=color, edgecolor="none", alpha=0.25, zorder=4,
        )
        ax_pin.add_patch(shadow)

    elif pin_style == 4:
        # House
        path = _svg_path_to_mpl(
            _FA_HOUSE_D, cx, cy, size,
            _FA_HOUSE_VBW, _FA_HOUSE_VBH, anchor="center"
        )
        ax_pin.add_patch(PathPatch(
            path, facecolor=color, edgecolor="none", zorder=5,
        ))

    elif pin_style == 5:
        # Graduation cap
        path = _svg_path_to_mpl(
            _FA_GRADCAP_D, cx, cy, size,
            _FA_GRADCAP_VBW, _FA_GRADCAP_VBH, anchor="center"
        )
        ax_pin.add_patch(PathPatch(
            path, facecolor=color, edgecolor="none", zorder=5,
        ))

    ax_pin.set_xlim(-0.1, 1.1)
    ax_pin.set_ylim(-0.1, 1.1)
    ax_pin.set_aspect("equal")
    ax_pin.axis("off")


def generate_style_sheet(output_path: str = "etsy/style_sheet.png", dpi: int = 200):
    """Generate the complete font + pin style sheet."""

    fig = plt.figure(figsize=(10, 8), facecolor=BG_COLOR)

    # ── HEADER ──
    fig.text(
        0.27, 0.93, "F O N T S",
        color=TEXT_COLOR, fontsize=24, fontweight="bold",
        ha="center", va="center", fontfamily="sans-serif",
    )
    fig.text(
        0.78, 0.93, "P I N S",
        color=TEXT_COLOR, fontsize=24, fontweight="bold",
        ha="center", va="center", fontfamily="sans-serif",
    )
    fig.text(
        0.78, 0.895, "(can be in any color)",
        color=SUBTITLE_COLOR, fontsize=10,
        ha="center", va="center", fontfamily="sans-serif",
        style="italic",
    )

    # Vertical divider
    fig.add_artist(plt.Line2D(
        [0.56, 0.56], [0.05, 0.88],
        transform=fig.transFigure,
        color=DIVIDER_COLOR, linewidth=1,
    ))

    # ── FONT ROWS ──
    row_height = 0.155
    start_y = 0.80

    for i in range(1, 6):
        preset = FONT_PRESETS[i]
        y = start_y - (i - 1) * row_height

        # Numbered circle
        _numbered_circle(fig, 0.06, y - 0.01, i)

        # Title line — use actual font
        title_display = TITLE_TEXT
        if preset.get("city_uppercase"):
            title_display = TITLE_TEXT.upper()
        if preset.get("city_letterspaced"):
            title_display = "  ".join(list(title_display))

        font_center_x = 0.30  # center of the fonts column

        title_size = 22
        # Reduce size for letterspaced presets to prevent overflow
        if preset.get("city_letterspaced"):
            title_size = 14
        title_font = _get_font(preset, "city", title_size)
        fig.text(
            font_center_x, y + 0.015, title_display,
            color=TEXT_COLOR,
            fontproperties=title_font,
            ha="center", va="center",
        )

        # Subtitle lines — use actual body font
        line2_display = LINE2_TEXT
        line3_display = LINE3_TEXT
        if preset.get("line2_uppercase"):
            line2_display = LINE2_TEXT.upper()
            line3_display = LINE3_TEXT.upper()
        if preset.get("line2_letterspaced"):
            line2_display = "  ".join(list(line2_display))
            line3_display = "  ".join(list(line3_display))

        body_font = _get_font(preset, "body", 11)
        fig.text(
            font_center_x, y - 0.030, line2_display,
            color=SUBTITLE_COLOR,
            fontproperties=body_font,
            ha="center", va="center",
        )
        fig.text(
            font_center_x, y - 0.058, line3_display,
            color=SUBTITLE_COLOR,
            fontproperties=body_font,
            ha="center", va="center",
        )

        # Horizontal divider between rows (except last)
        if i < 5:
            div_y = y - row_height / 2 - 0.02
            fig.add_artist(plt.Line2D(
                [0.03, 0.53], [div_y, div_y],
                transform=fig.transFigure,
                color=DIVIDER_COLOR, linewidth=0.5,
            ))

    # ── PIN ROWS ──
    for i in range(1, 6):
        y = start_y - (i - 1) * row_height

        # Numbered circle
        _numbered_circle(fig, 0.64, y - 0.01, i)

        # Pin icon in a small axes
        pin_ax = fig.add_axes([0.72, y - 0.065, 0.12, 0.12])
        _draw_pin_icon(fig, pin_ax, i, color=ACCENT_COLOR)

        # Horizontal divider (except last)
        if i < 5:
            div_y = y - row_height / 2 - 0.02
            fig.add_artist(plt.Line2D(
                [0.60, 0.95], [div_y, div_y],
                transform=fig.transFigure,
                color=DIVIDER_COLOR, linewidth=0.5,
            ))

    # Save
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=dpi, facecolor=BG_COLOR, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Style sheet saved to {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate font & pin style sheet")
    parser.add_argument("--output", default="etsy/style_sheet.png")
    parser.add_argument("--dpi", type=int, default=200)
    args = parser.parse_args()
    generate_style_sheet(args.output, args.dpi)
