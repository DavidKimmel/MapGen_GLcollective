"""
MapGen — Text Layout System.

Handles the 2-zone text layout for map products:
  - Map zone: the rendered map
  - Bottom zone: 3 lines of text (title, address, date)

5 font presets:
  1 = "sans"     — Montserrat Light (ALL CAPS, wide letter-spacing)
  2 = "serif"    — Lora (title case, elegant)
  3 = "script"   — Great Vibes title + Cormorant Garamond body
  4 = "cursive"  — Pinyon Script title + Cormorant Garamond body
  5 = "classic"  — Cormorant Garamond (elegant classic serif)

Ported from GeoLineCollective's text_layout.py.
"""

import os

from matplotlib.font_manager import FontProperties

from utils.logging import is_latin_script, safe_print

_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_ENGINE_DIR)
FONTS_DIR = os.path.join(_PROJECT_DIR, "fonts")
THIN_SPACE = "\u2009"
WIDE_SPACE = " "

FONT_PRESETS = {
    1: {
        "name": "sans",
        "description": "Century Gothic — clean geometric sans, all caps",
        "city":     ("CenturyGothic-Bold.ttf", "sans-serif", "bold", "normal"),
        "subtitle": ("CenturyGothic-Bold.ttf", "sans-serif", "bold", "normal"),
        "label":    ("CenturyGothic-Bold.ttf", "sans-serif", "bold", "normal"),
        "body":     ("CenturyGothic-Bold.ttf", "sans-serif", "bold", "normal"),
        "body_italic": ("CenturyGothic-Bold.ttf", "sans-serif", "bold", "italic"),
        "coords":   ("CenturyGothic-Bold.ttf", "sans-serif", "bold", "normal"),
        "city_uppercase": True,
        "city_letterspaced": True,
        "line2_uppercase": True,
        "line2_letterspaced": True,
        "line3_uppercase": True,
        "line3_letterspaced": True,
    },
    2: {
        "name": "hightower",
        "description": "High Tower Text — refined traditional serif",
        "city":     ("HighTowerText-Regular.ttf", "serif", "normal", "normal"),
        "subtitle": ("HighTowerText-Regular.ttf", "serif", "normal", "normal"),
        "label":    ("HighTowerText-Regular.ttf", "serif", "normal", "normal"),
        "body":     ("HighTowerText-Regular.ttf", "serif", "normal", "normal"),
        "body_italic": ("HighTowerText-Italic.ttf", "serif", "normal", "italic"),
        "coords":   ("HighTowerText-Regular.ttf", "serif", "normal", "normal"),
        "city_uppercase": False,
        "city_letterspaced": False,
        "line2_uppercase": False,
        "line2_letterspaced": False,
    },
    3: {
        "name": "script",
        "description": "Priestacy title + Lucida Calligraphy body",
        "city":     ("Priestacy.otf", "cursive", "normal", "normal"),
        "subtitle": ("LucidaCalligraphy-Italic.ttf", "cursive", "normal", "normal"),
        "label":    ("LucidaCalligraphy-Italic.ttf", "cursive", "normal", "normal"),
        "body":     ("LucidaCalligraphy-Italic.ttf", "cursive", "normal", "normal"),
        "body_italic": ("LucidaCalligraphy-Italic.ttf", "cursive", "normal", "italic"),
        "coords":   ("LucidaCalligraphy-Italic.ttf", "cursive", "normal", "normal"),
        "city_uppercase": False,
        "city_letterspaced": False,
        "line2_uppercase": False,
        "line2_letterspaced": False,
        "title_descender_offset": 0.012,
    },
    4: {
        "name": "corsiva",
        "description": "Monotype Corsiva — classic italic script",
        "city":     ("MonotypeCorsiva-Regular.ttf", "cursive", "normal", "normal"),
        "subtitle": ("MonotypeCorsiva-Regular.ttf", "cursive", "normal", "normal"),
        "label":    ("MonotypeCorsiva-Regular.ttf", "cursive", "normal", "normal"),
        "body":     ("MonotypeCorsiva-Regular.ttf", "cursive", "normal", "normal"),
        "body_italic": ("MonotypeCorsiva-Regular.ttf", "cursive", "normal", "italic"),
        "coords":   ("MonotypeCorsiva-Regular.ttf", "cursive", "normal", "normal"),
        "city_uppercase": False,
        "city_letterspaced": False,
        "line2_uppercase": False,
        "line2_letterspaced": False,
    },
    5: {
        "name": "classic",
        "description": "Footlight MT Light — warm classic serif",
        "city":     ("FootlightMTLight-Regular.ttf", "serif", "normal", "normal"),
        "subtitle": ("FootlightMTLight-Regular.ttf", "serif", "normal", "normal"),
        "label":    ("FootlightMTLight-Regular.ttf", "serif", "normal", "normal"),
        "body":     ("FootlightMTLight-Regular.ttf", "serif", "normal", "normal"),
        "body_italic": ("FootlightMTLight-Regular.ttf", "serif", "normal", "italic"),
        "coords":   ("FootlightMTLight-Regular.ttf", "serif", "normal", "normal"),
        "city_uppercase": False,
        "city_letterspaced": False,
        "line2_uppercase": False,
        "line2_letterspaced": False,
    },
    6: {
        "name": "house",
        "description": "House map — High Tower title + Priestacy script names + High Tower address",
        "city":     ("HighTowerText-Regular.ttf", "serif", "normal", "normal"),
        "subtitle": ("Priestacy.otf", "cursive", "normal", "normal"),
        "label":    ("HighTowerText-Regular.ttf", "serif", "normal", "normal"),
        "body":     ("HighTowerText-Regular.ttf", "serif", "normal", "normal"),
        "body_italic": ("HighTowerText-Italic.ttf", "serif", "normal", "italic"),
        "coords":   ("HighTowerText-Regular.ttf", "serif", "normal", "normal"),
        "city_uppercase": True,
        "city_letterspaced": True,
        "line2_uppercase": False,
        "line2_letterspaced": False,
        "line2_font_role": "subtitle",
        "line2_size_scale": 2.8,
        "line3_uppercase": False,
        "line3_letterspaced": False,
        "line_positions": {
            "line_1_y": 0.200,
            "line_2_y": 0.129,
            "line_3_y": 0.058,
            "line_4_y": 0.042,
        },
        "map_height_override": 0.70,
        "map_bottom_override": 0.22,
        "use_4_lines": True,
    },
}


def get_zone_positions(has_top_label: bool = False,
                       layout: str = "default") -> dict:
    """Return axes position and text line y-positions for the 2-zone layout.

    Layouts:
        "default"    — standard poster: map on top, 3 text lines below
        "date_night" — heart centered: line 1 above, lines 2-4 below
    """
    left = 0.049
    width = 0.902

    if layout == "date_night":
        # Heart centered with text above and below
        map_bottom = 0.20
        map_height = 0.60
        top_zone_y = None  # handled by render_date_night_text

        bottom_zone = {
            "line_1_y": 0.88,   # names — above heart
            "line_2_y": 0.115,  # tagline — below heart
            "line_3_y": 0.082,  # location
            "line_4_y": 0.056,  # date
        }

        return {
            "map": (left, map_bottom, width, map_height),
            "top_zone_y": top_zone_y,
            "bottom_zone": bottom_zone,
            "layout": "date_night",
        }

    if has_top_label:
        map_bottom = 0.196
        map_height = 0.574
        top_zone_y = 0.951
    else:
        map_bottom = 0.196
        map_height = 0.755
        top_zone_y = None

    # Text zone: 0 to 0.196
    # Bottom padding ~0.048 for framing, lines spaced evenly above
    bottom_zone = {
        "line_1_y": 0.138,
        "line_2_y": 0.088,
        "line_3_y": 0.058,
    }

    return {
        "map": (left, map_bottom, width, map_height),
        "top_zone_y": top_zone_y,
        "bottom_zone": bottom_zone,
        "layout": "default",
    }


_font_cache: dict[tuple[str, float, str], FontProperties] = {}


def _get_font(preset: dict, role: str, size: float,
              style_override: str | None = None) -> FontProperties:
    """Get FontProperties for a specific role from a font preset (cached)."""
    font_file, fallback_family, fallback_weight, fallback_style = preset[role]
    if style_override:
        fallback_style = style_override

    cache_key = (font_file, size, fallback_style)
    if cache_key in _font_cache:
        return _font_cache[cache_key]

    font_path = os.path.join(FONTS_DIR, font_file)

    if os.path.exists(font_path):
        fp = FontProperties(fname=font_path, size=size)
        if fallback_style == "italic":
            fp = fp.copy()
            fp.set_style("italic")
    else:
        fp = FontProperties(
            family=fallback_family,
            weight=fallback_weight,
            style=fallback_style,
            size=size,
        )

    _font_cache[cache_key] = fp
    return fp


def get_font_preset(font_id: int = 1) -> dict:
    """Get a font preset by ID. Returns preset 1 if ID is invalid."""
    return FONT_PRESETS.get(font_id, FONT_PRESETS[1])


def render_bottom_text(fig, city_name: str | None, state_name: str | None,
                       show_coords: bool, point: tuple[float, float] | None,
                       custom_line_1: str | None, custom_line_2: str | None,
                       style_name: str, scale_factor: float = 1.0,
                       font_preset: int = 1,
                       text_line_1: str | None = None,
                       text_line_2: str | None = None,
                       text_line_3: str | None = None,
                       text_line_4: str | None = None) -> None:
    """Render the bottom text zone with 3-4 lines.

    New 3-line API (preferred):
        text_line_1: Large title (e.g., "Our First Home")
        text_line_2: Medium subtitle (e.g., "Middletown, CT")
        text_line_3: Small detail (e.g., "Est. 2015")

    Legacy API (fallback):
        city_name, state_name, show_coords, point, custom_line_1, custom_line_2
    """
    preset = get_font_preset(font_preset)
    zones = get_zone_positions(has_top_label=False)
    bottom = zones["bottom_zone"]
    if "line_positions" in preset:
        bottom = {**bottom, **preset["line_positions"]}

    text_primary = "#1A1A1A"
    text_secondary = "#1A1A1A"

    line1 = text_line_1 if text_line_1 is not None else city_name
    line2 = text_line_2 if text_line_2 is not None else custom_line_1
    line3 = text_line_3 if text_line_3 is not None else custom_line_2

    # Fonts with large descenders need extra space below the title
    descender_offset = preset.get("title_descender_offset", 0)

    # --- Line 1 (large title) ---
    line1_size = 63 * scale_factor

    if line1:
        char_count = len(line1)
        if char_count > 10 and preset["city_uppercase"]:
            line1_size = max(line1_size * (10 / char_count), 14 * scale_factor)

        if preset["city_uppercase"]:
            display_line1 = line1.upper()
        else:
            display_line1 = line1.title()

        if preset["city_letterspaced"] and is_latin_script(line1):
            display_line1 = WIDE_SPACE.join(list(display_line1))

        font_line1 = _get_font(preset, "city", line1_size)
        fig.text(
            0.5, bottom["line_1_y"],
            display_line1,
            color=text_primary,
            ha="center", va="center",
            fontproperties=font_line1,
        )

    # --- Line 2 (medium subtitle) ---
    line2_scale = preset.get("line2_size_scale", 1.0)
    line2_size = 20 * scale_factor * line2_scale
    if line2:
        display_line2 = line2
        if preset.get("line2_uppercase"):
            display_line2 = line2.upper()
        if preset.get("line2_letterspaced") and is_latin_script(line2):
            display_line2 = WIDE_SPACE.join(list(display_line2))

        line2_role = preset.get("line2_font_role", "body")
        font_line2 = _get_font(preset, line2_role, line2_size)
        fig.text(
            0.5, bottom["line_2_y"] - descender_offset,
            display_line2,
            color=text_secondary,
            ha="center", va="center",
            fontproperties=font_line2,
        )

    # --- Line 3 (small detail) ---
    line3_size = 20 * scale_factor
    if line3:
        display_line3 = line3
        if preset.get("line3_uppercase"):
            display_line3 = line3.upper()
        if preset.get("line3_letterspaced") and is_latin_script(line3):
            display_line3 = WIDE_SPACE.join(list(display_line3))

        font_line3 = _get_font(preset, "body", line3_size)
        fig.text(
            0.5, bottom["line_3_y"] - descender_offset,
            display_line3,
            color=text_secondary,
            ha="center", va="center",
            fontproperties=font_line3,
        )

    # --- Line 4 (optional, for presets with use_4_lines) ---
    if text_line_4 and "line_4_y" in bottom:
        line4_size = 20 * scale_factor
        font_line4 = _get_font(preset, "body", line4_size)
        fig.text(
            0.5, bottom["line_4_y"],
            text_line_4,
            color=text_secondary,
            ha="center", va="center",
            fontproperties=font_line4,
        )


def render_date_night_text(fig, scale_factor: float = 1.0,
                           font_preset: int = 3,
                           text_line_1: str | None = None,
                           text_line_2: str | None = None,
                           text_line_3: str | None = None,
                           text_line_4: str | None = None) -> None:
    """Render text for date_night layout: line 1 above heart, lines 2-4 below.

    Line 1: Names (large script, above heart) — uses font_preset (e.g., 3=Priestacy)
    Line 2: Tagline (bold serif, below heart) — always font 2 (High Tower Text)
    Line 3: Location (normal serif) — always font 2
    Line 4: Date (normal serif) — always font 2
    """
    title_preset = get_font_preset(font_preset)
    body_preset = get_font_preset(2)  # High Tower Text for bottom lines
    zones = get_zone_positions(layout="date_night")
    bz = zones["bottom_zone"]

    text_color = "#1A1A1A"

    # --- Line 1: Names above heart (large script) ---
    if text_line_1:
        line1_size = 58 * scale_factor
        font_line1 = _get_font(title_preset, "city", line1_size)
        fig.text(
            0.5, bz["line_1_y"],
            text_line_1,
            color=text_color,
            ha="center", va="center",
            fontproperties=font_line1,
        )

    # --- Line 2: Tagline below heart (Garamond Bold, larger) ---
    if text_line_2:
        line2_size = 28 * scale_factor
        garamond_bold = os.path.join(FONTS_DIR, "Garamond-Bold.ttf")
        font_line2 = FontProperties(fname=garamond_bold, size=line2_size)
        fig.text(
            0.5, bz["line_2_y"],
            text_line_2,
            color=text_color,
            ha="center", va="center",
            fontproperties=font_line2,
        )

    # --- Line 3: Location (normal serif) ---
    if text_line_3:
        line3_size = 18 * scale_factor
        font_line3 = _get_font(body_preset, "body", line3_size)
        fig.text(
            0.5, bz["line_3_y"],
            text_line_3,
            color=text_color,
            ha="center", va="center",
            fontproperties=font_line3,
        )

    # --- Line 4: Date (normal serif) ---
    if text_line_4:
        line4_size = 18 * scale_factor
        font_line4 = _get_font(body_preset, "body", line4_size)
        fig.text(
            0.5, bz["line_4_y"],
            text_line_4,
            color=text_color,
            ha="center", va="center",
            fontproperties=font_line4,
        )


def render_top_label(fig, label_top: str | None, style_name: str,
                     scale_factor: float = 1.0, font_preset: int = 1) -> None:
    """Render the optional top label zone."""
    if not label_top:
        return

    preset = get_font_preset(font_preset)
    zones = get_zone_positions(has_top_label=True)
    y_pos = zones["top_zone_y"]

    text_primary = "#2C2C2C"
    label_size = 22 * scale_factor

    if is_latin_script(label_top):
        display_label = WIDE_SPACE.join(list(label_top.upper()))
    else:
        display_label = label_top.upper()

    font_label = _get_font(preset, "label", label_size)
    fig.text(
        0.5, y_pos,
        display_label,
        color=text_primary, alpha=0.80,
        ha="center", va="center",
        fontproperties=font_label,
    )
