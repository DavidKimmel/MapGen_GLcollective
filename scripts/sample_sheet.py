"""
MapGen — Sample Sheet Generator

Renders a reference sheet showing all 5 font presets and all 5 pin styles
side by side, without rendering any maps. Fast iteration for design tuning.
Formatted for use as an Etsy listing image.

Usage:
    python sample_sheet.py
    python sample_sheet.py --output output/sample_sheet.png
"""

import argparse
import os

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MplPath
from matplotlib.lines import Line2D

from engine.text_layout import FONT_PRESETS, _get_font, WIDE_SPACE
from utils.logging import is_latin_script, safe_print
from engine.pin_renderer import _svg_teardrop, _svg_heart, _svg_house, _svg_gradcap


# Sample text for the sheet
SAMPLE_LINE_1 = "Our First Home"
SAMPLE_LINE_2 = "Middletown, CT"
SAMPLE_LINE_3 = "Est. 2015"

# Pin color
PIN_COLOR = "#D4736B"
PIN_LABELS = ["Heart", "Heart Pin", "Classic Pin", "House", "Grad Cap"]

# Background
BG_COLOR = "#F5F3F0"


def render_font_samples(fig, left_x, right_x, top_y, row_height):
    """Render all 5 font presets in a column layout."""
    cx = (left_x + right_x) / 2

    for i, (preset_id, preset) in enumerate(FONT_PRESETS.items()):
        cy = top_y - i * row_height

        # Circled number
        circle = plt.Circle(
            (left_x + 0.05, cy + 0.005), 0.016,
            transform=fig.transFigure,
            facecolor="none", edgecolor=PIN_COLOR,
            linewidth=1.5, zorder=10,
        )
        fig.patches.append(circle)
        fig.text(
            left_x + 0.05, cy + 0.005,
            str(preset_id),
            ha="center", va="center",
            fontsize=13, color=PIN_COLOR, fontweight="600",
        )

        # Label under number
        fig.text(
            left_x + 0.05, cy - 0.025,
            preset["name"],
            ha="center", va="center",
            fontsize=9, color="#999999",
        )

        # Line 1 (large title)
        line1 = SAMPLE_LINE_1
        line1_size = 20
        if preset["name"] in ("script", "cursive"):
            line1_size = 24

        if preset.get("city_uppercase"):
            line1 = line1.upper()
        if preset.get("city_letterspaced") and is_latin_script(line1):
            line1 = WIDE_SPACE.join(list(line1))
            line1_size = 15

        font1 = _get_font(preset, "city", line1_size)
        fig.text(
            cx + 0.03, cy + 0.012,
            line1,
            ha="center", va="center",
            fontproperties=font1, color="#1A1A1A",
        )

        # Line 2 (medium subtitle)
        line2 = SAMPLE_LINE_2
        line2_size = 10
        if preset.get("line2_uppercase"):
            line2 = line2.upper()
        if preset.get("line2_letterspaced") and is_latin_script(line2):
            line2 = WIDE_SPACE.join(list(line2))

        font2 = _get_font(preset, "body", line2_size)
        fig.text(
            cx + 0.03, cy - 0.022,
            line2,
            ha="center", va="center",
            fontproperties=font2, color="#1A1A1A",
        )

        # Line 3 (small detail)
        line3 = SAMPLE_LINE_3
        line3_size = 9
        if preset.get("line3_uppercase"):
            line3 = line3.upper()
        if preset.get("line3_letterspaced") and is_latin_script(line3):
            line3 = WIDE_SPACE.join(list(line3))

        font3 = _get_font(preset, "body", line3_size)
        fig.text(
            cx + 0.03, cy - 0.042,
            line3,
            ha="center", va="center",
            fontproperties=font3, color="#1A1A1A",
        )


def render_pin_samples(ax, top_y, row_height, axes_bottom, axes_height):
    """Render all 5 pin styles using axes data coordinates."""
    fig = ax.figure
    pin_size = 0.11
    pin_cx = 0.38
    shadow_color = "#D8D4D0"

    for i in range(5):
        frac = (top_y - i * row_height - axes_bottom) / axes_height
        dy = frac
        dx = pin_cx
        pin_id = i + 1
        ps = pin_size

        # Circled number + label (figure coords)
        fig_y = top_y - i * row_height
        fig_num_x = 0.58
        circle = plt.Circle(
            (fig_num_x, fig_y), 0.016,
            transform=fig.transFigure,
            facecolor="none", edgecolor=PIN_COLOR,
            linewidth=1.5, zorder=10,
        )
        fig.patches.append(circle)
        fig.text(
            fig_num_x, fig_y,
            str(pin_id),
            ha="center", va="center",
            fontsize=13, color=PIN_COLOR, fontweight="600",
        )
        fig.text(
            fig_num_x, fig_y - 0.028,
            PIN_LABELS[i],
            ha="center", va="center",
            fontsize=9, color="#999999",
        )

        if pin_id == 1:
            path = _svg_heart(dx, dy, ps)
            ax.add_patch(PathPatch(path, facecolor=PIN_COLOR, edgecolor='none', linewidth=0, zorder=20))

        elif pin_id == 2:
            path, head_cy = _svg_teardrop(dx, dy, ps)
            ax.add_patch(PathPatch(path, facecolor=PIN_COLOR, edgecolor='none', linewidth=0, zorder=20))
            inner = _svg_heart(dx, head_cy, ps * 0.35)
            ax.add_patch(PathPatch(inner, facecolor='white', edgecolor='none', zorder=21))

        elif pin_id == 3:
            path, head_cy = _svg_teardrop(dx, dy, ps)
            ax.add_patch(PathPatch(path, facecolor=PIN_COLOR, edgecolor='none', linewidth=0, zorder=20))
            circle_r = ps * 0.14
            t = np.linspace(0, 2 * np.pi, 40)
            cverts = list(zip(dx + circle_r * np.cos(t), head_cy + circle_r * np.sin(t)))
            cverts.append(cverts[0])
            ccodes = [MplPath.MOVETO] + [MplPath.LINETO] * (len(cverts) - 2) + [MplPath.CLOSEPOLY]
            ax.add_patch(PathPatch(MplPath(cverts, ccodes), facecolor='white', edgecolor='none', zorder=21))

        elif pin_id == 4:
            path = _svg_house(dx, dy, ps)
            ax.add_patch(PathPatch(path, facecolor=PIN_COLOR, edgecolor='none', linewidth=0, zorder=20))

        elif pin_id == 5:
            path = _svg_gradcap(dx, dy, ps)
            ax.add_patch(PathPatch(path, facecolor=PIN_COLOR, edgecolor='none', linewidth=0, zorder=20))


def generate_sample_sheet(output_path: str = "output/sample_sheet.png", dpi: int = 200) -> str:
    """Generate the full sample sheet with fonts and pins side by side."""
    safe_print("Generating sample sheet...")

    fig = plt.figure(figsize=(10, 8), facecolor=BG_COLOR)

    # Layout constants
    row_height = 0.155
    header_y = 0.93
    top_y = 0.82

    # ---- FONTS header ----
    fig.text(
        0.26, header_y,
        "F O N T   S T Y L E S",
        ha="center", va="center",
        fontsize=16, fontweight="bold",
        color="#1A1A1A",
    )
    fig.lines.append(Line2D(
        [0.08, 0.44], [header_y - 0.025, header_y - 0.025],
        transform=fig.transFigure,
        color="#D8D4D0", linewidth=0.8, zorder=1,
    ))

    # ---- PINS header ----
    fig.text(
        0.74, header_y,
        "P I N   S T Y L E S",
        ha="center", va="center",
        fontsize=16, fontweight="bold",
        color="#1A1A1A",
    )
    fig.text(
        0.74, header_y - 0.045,
        "available in any color",
        ha="center", va="center",
        fontsize=8, fontstyle="italic",
        color="#AAAAAA",
    )
    fig.lines.append(Line2D(
        [0.56, 0.92], [header_y - 0.025, header_y - 0.025],
        transform=fig.transFigure,
        color="#D8D4D0", linewidth=0.8, zorder=1,
    ))

    # ---- Fonts (left side) ----
    render_font_samples(fig, left_x=0.02, right_x=0.48, top_y=top_y, row_height=row_height)

    # ---- Pins (right side) ----
    axes_bottom = 0.06
    axes_height = 0.82
    ax = fig.add_axes([0.52, axes_bottom, 0.46, axes_height])
    ax_aspect = 0.46 / axes_height
    ax.set_xlim(0, ax_aspect)
    ax.set_ylim(0, 1)
    ax.set_aspect('equal')
    ax.axis('off')

    render_pin_samples(ax, top_y=top_y, row_height=row_height,
                       axes_bottom=axes_bottom, axes_height=axes_height)

    # ---- Vertical divider ----
    fig.lines.append(Line2D(
        [0.50, 0.50], [0.04, 0.91],
        transform=fig.transFigure,
        color="#E0DCD8", linewidth=1, zorder=1,
    ))

    # ---- Save ----
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=dpi, facecolor=fig.get_facecolor(),
                bbox_inches='tight', pad_inches=0.25)
    plt.close(fig)
    safe_print(f"[OK] Sample sheet saved: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate font & pin sample sheet")
    parser.add_argument("--output", default="output/EtsySampleSheet.png", help="Output path")
    parser.add_argument("--dpi", type=int, default=200, help="DPI")
    args = parser.parse_args()
    generate_sample_sheet(output_path=args.output, dpi=args.dpi)
