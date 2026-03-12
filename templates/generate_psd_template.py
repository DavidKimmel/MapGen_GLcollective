"""
MapGen -- PSD Template Generator for Photopea Workflow.

Creates layered PSD templates matching our poster layout:
  - Full: map rectangle + 3 text placeholders
  - Heart / Circle / House: shape placeholder + shape outline (no text layers)

Uses per-layer bounding boxes and PackBits (RLE) compression
to keep file sizes manageable.

Usage:
    python -m templates.generate_psd_template --size 16x20
    python -m templates.generate_psd_template --size 16x20 --crop heart
    python -m templates.generate_psd_template --size all --crop all
"""

from __future__ import annotations

import argparse
import math
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from export.output_sizes import PRINT_SIZES

TEMPLATES_DIR = PROJECT_DIR / "templates" / "psd"
DPI = 300

# Layout zones -- expanded bottom for bigger text + bleed margin
MAP_LEFT = 0.07
MAP_BOTTOM = 0.21
MAP_WIDTH = 0.86
MAP_HEIGHT = 0.72

# Text positions (y from bottom of canvas, as fraction)
TEXT_LINE_1_Y = 0.155
TEXT_LINE_2_Y = 0.100
TEXT_LINE_3_Y = 0.060

ALL_CROPS = ["full", "heart", "circle", "house"]


def px(fraction: float, total: int) -> int:
    return int(round(fraction * total))


# ---------------------------------------------------------------------------
# PackBits RLE compression
# ---------------------------------------------------------------------------

def packbits_encode(data: bytes) -> bytes:
    result = bytearray()
    i = 0
    n = len(data)
    while i < n:
        run_start = i
        if i + 1 < n and data[i] == data[i + 1]:
            while i + 1 < n and data[i] == data[i + 1] and (i - run_start) < 127:
                i += 1
            run_len = i - run_start + 1
            result.append(256 - run_len + 1)
            result.append(data[run_start])
            i += 1
        else:
            literal_start = i
            while i < n:
                if i + 1 < n and data[i] == data[i + 1]:
                    break
                i += 1
                if i - literal_start >= 128:
                    break
            literal_len = i - literal_start
            result.append(literal_len - 1)
            result.extend(data[literal_start:i])
    return bytes(result)


def compress_channel_rle(channel_data: np.ndarray, width: int, height: int) -> bytes:
    parts = [struct.pack(">H", 1)]
    rows = []
    for y in range(height):
        rows.append(packbits_encode(channel_data[y].tobytes()))
    for row_data in rows:
        parts.append(struct.pack(">H", len(row_data)))
    for row_data in rows:
        parts.append(row_data)
    return b"".join(parts)


# ---------------------------------------------------------------------------
# Map area geometry
# ---------------------------------------------------------------------------

def get_map_rect(width_px: int, height_px: int) -> tuple[int, int, int, int]:
    """Map area in pixel coords (x1, y1, x2, y2) with top-left origin."""
    x1 = px(MAP_LEFT, width_px)
    x2 = px(MAP_LEFT + MAP_WIDTH, width_px)
    y1 = px(1.0 - (MAP_BOTTOM + MAP_HEIGHT), height_px)
    y2 = px(1.0 - MAP_BOTTOM, height_px)
    return (x1, y1, x2, y2)


# ---------------------------------------------------------------------------
# Shape generators (match engine/crop_masks.py exactly)
# ---------------------------------------------------------------------------

def _heart_polygon(cx: float, cy: float, sx: float, sy: float,
                   n_points: int = 300) -> list[tuple[int, int]]:
    """Generate heart outline matching crop_masks._heart_svg_verts.
    Uses cubic bezier sampling to match the SVG heart shape.
    """
    segs = [
        ((0.4580, 0.8506), (0.2722, 0.8507), (0.0993, 0.7556), (0.0000, 0.5985)),
        ((0.0000, 0.5985), (-0.0843, 0.7317), (-0.2225, 0.8216), (-0.3784, 0.8447)),
        ((-0.3784, 0.8447), (-0.5343, 0.8679), (-0.6926, 0.8220), (-0.8120, 0.7190)),
        ((-0.8120, 0.7190), (-0.9313, 0.6160), (-1.0000, 0.4662), (-1.0000, 0.3086)),
        ((-1.0000, 0.3086), (-1.0000, -0.2350), (-0.1950, -0.6855), (0.0000, -0.8506)),
        ((0.0000, -0.8506), (0.1950, -0.6855), (1.0000, -0.2350), (1.0000, 0.3086)),
        ((1.0000, 0.3086), (1.0000, 0.4523), (0.9429, 0.5902), (0.8412, 0.6918)),
        ((0.8412, 0.6918), (0.7396, 0.7935), (0.6017, 0.8506), (0.4580, 0.8506)),
    ]

    pts_per_seg = n_points // len(segs)
    points = []
    for start, cp1, cp2, end in segs:
        for i in range(pts_per_seg):
            t = i / pts_per_seg
            u = 1 - t
            x = (u**3 * start[0] + 3 * u**2 * t * cp1[0] +
                 3 * u * t**2 * cp2[0] + t**3 * end[0])
            y = (u**3 * start[1] + 3 * u**2 * t * cp1[1] +
                 3 * u * t**2 * cp2[1] + t**3 * end[1])
            # Note: y is inverted for screen coords (PIL top-left origin)
            points.append((int(cx + x * sx), int(cy - y * sy)))

    return points


def _circle_polygon(cx: float, cy: float, radius: float,
                    n_points: int = 300) -> list[tuple[int, int]]:
    points = []
    for i in range(n_points):
        angle = 2 * math.pi * i / n_points
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        points.append((int(x), int(y)))
    return points


def _house_polygon(map_rect: tuple[int, int, int, int]) -> list[tuple[int, int]]:
    """Generate house shape matching crop_masks.apply_house_crop."""
    x1, y1, x2, y2 = map_rect
    map_w = x2 - x1
    map_h = y2 - y1

    # Insets matching crop_masks (10% x, 4% y)
    inset_x = map_w * 0.10
    inset_y = map_h * 0.04

    left = x1 + inset_x
    right = x2 - inset_x
    bottom = y2 - inset_y   # PIL y: bottom is larger
    top = y1 + inset_y      # PIL y: top is smaller

    inner_w = right - left
    inner_h = bottom - top

    # Wall top at 55% up from bottom of inner area
    wall_top_y = bottom - inner_h * 0.55  # PIL coords
    roof_peak_y = top
    center_x = (left + right) / 2

    overhang = inner_w * 0.12
    roof_left = left - overhang
    roof_right = right + overhang

    # Chimney
    chimney_cx = center_x + inner_w * 0.25
    chimney_w = inner_w * 0.09
    chimney_left = chimney_cx - chimney_w / 2
    chimney_right = chimney_cx + chimney_w / 2

    # Roof slope at chimney positions
    t_left = (chimney_left - center_x) / (roof_right - center_x)
    t_right = (chimney_right - center_x) / (roof_right - center_x)
    # In PIL coords (y inverted vs matplotlib)
    roof_y_at_chim_left = roof_peak_y + t_left * (wall_top_y - roof_peak_y)
    roof_y_at_chim_right = roof_peak_y + t_right * (wall_top_y - roof_peak_y)
    chimney_top = roof_y_at_chim_left - inner_h * 0.04  # above roof line

    points = [
        (left, bottom),
        (right, bottom),
        (right, wall_top_y),
        (roof_right, wall_top_y),
        (chimney_right, roof_y_at_chim_right),
        (chimney_right, chimney_top),
        (chimney_left, chimney_top),
        (chimney_left, roof_y_at_chim_left),
        (center_x, roof_peak_y),
        (roof_left, wall_top_y),
        (left, wall_top_y),
    ]
    return [(int(x), int(y)) for x, y in points]


# ---------------------------------------------------------------------------
# Layer creation
# ---------------------------------------------------------------------------

def create_map_placeholder(width_px: int, height_px: int,
                           map_rect: tuple, crop: str = "full") -> Image.Image:
    """Map placeholder layer - gray shape where the map goes."""
    layer = Image.new("RGBA", (width_px, height_px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x1, y1, x2, y2 = map_rect
    map_w = x2 - x1
    map_h = y2 - y1
    map_cx = (x1 + x2) / 2
    map_cy = (y1 + y2) / 2

    fill_color = (220, 220, 220, 255)

    if crop == "full":
        draw.rectangle([x1, y1, x2, y2], fill=fill_color)
    elif crop == "circle":
        radius = min(map_w, map_h) / 2 * 0.98
        poly = _circle_polygon(map_cx, map_cy, radius)
        draw.polygon(poly, fill=fill_color)
    elif crop == "heart":
        # Match crop_masks: sx = x_range * 0.50, sy = y_range * 0.54
        sx = map_w * 0.50
        sy = map_h * 0.54
        heart_cy = map_cy - map_h * 0.02  # slight upward offset
        poly = _heart_polygon(map_cx, heart_cy, sx, sy)
        draw.polygon(poly, fill=fill_color)
    elif crop == "house":
        poly = _house_polygon(map_rect)
        draw.polygon(poly, fill=fill_color)

    # Label text
    try:
        font = ImageFont.truetype("arial.ttf", max(24, width_px // 40))
    except OSError:
        font = ImageFont.load_default()
    label = "MAP PLACEHOLDER"
    bbox = draw.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = int(map_cx - tw / 2)
    ty = int(map_cy - th / 2)
    draw.text((tx, ty), label, fill=(180, 180, 180, 255), font=font)

    return layer


def create_shape_outline(width_px: int, height_px: int,
                         map_rect: tuple, crop: str) -> Image.Image:
    """Thin outline of the crop shape for reference."""
    layer = Image.new("RGBA", (width_px, height_px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x1, y1, x2, y2 = map_rect
    map_w = x2 - x1
    map_h = y2 - y1
    map_cx = (x1 + x2) / 2
    map_cy = (y1 + y2) / 2

    outline_color = (80, 80, 80, 200)
    line_w = max(2, width_px // 1000)

    if crop == "circle":
        radius = min(map_w, map_h) / 2 * 0.98
        poly = _circle_polygon(map_cx, map_cy, radius)
        draw.polygon(poly, outline=outline_color, width=line_w)
    elif crop == "heart":
        sx = map_w * 0.50
        sy = map_h * 0.54
        heart_cy = map_cy - map_h * 0.02
        poly = _heart_polygon(map_cx, heart_cy, sx, sy)
        draw.polygon(poly, outline=outline_color, width=line_w)
    elif crop == "house":
        poly = _house_polygon(map_rect)
        draw.polygon(poly, outline=outline_color, width=line_w)

    return layer


def create_text_layer(width_px: int, height_px: int, text: str,
                      y_frac: float, font_size: int) -> Image.Image:
    layer = Image.new("RGBA", (width_px, height_px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    y_px = height_px - px(y_frac, height_px) - th // 2
    x_px = (width_px - tw) // 2
    draw.text((x_px, y_px), text, fill=(26, 26, 26, 255), font=font)
    return layer


def create_guides_layer(width_px: int, height_px: int, map_rect: tuple,
                        show_text_guides: bool = True) -> Image.Image:
    layer = Image.new("RGBA", (width_px, height_px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x1, y1, x2, y2 = map_rect
    guide_color = (0, 150, 255, 80)

    draw.line([(x1, 0), (x1, height_px)], fill=guide_color, width=2)
    draw.line([(x2, 0), (x2, height_px)], fill=guide_color, width=2)
    draw.line([(0, y1), (width_px, y1)], fill=guide_color, width=2)
    draw.line([(0, y2), (width_px, y2)], fill=guide_color, width=2)

    if show_text_guides:
        for y_frac in [TEXT_LINE_1_Y, TEXT_LINE_2_Y, TEXT_LINE_3_Y]:
            y_px = height_px - px(y_frac, height_px)
            draw.line([(x1, y_px), (x2, y_px)], fill=(255, 100, 0, 60), width=2)

    return layer


# ---------------------------------------------------------------------------
# Layer helpers / trim
# ---------------------------------------------------------------------------

def trim_to_content(img: Image.Image) -> tuple[Image.Image, tuple[int, int, int, int]]:
    bbox = img.getbbox()
    if bbox is None:
        return img, (0, 0, img.width, img.height)
    return img.crop(bbox), bbox


# ---------------------------------------------------------------------------
# PSD binary builder
# ---------------------------------------------------------------------------

def build_layer_record(name: str, top: int, left: int, bottom: int, right: int,
                       channel_sizes: list[int]) -> bytes:
    rec = b""
    rec += struct.pack(">IIII", top, left, bottom, right)
    rec += struct.pack(">H", 4)
    for ch_id, ch_size in zip([-1, 0, 1, 2], channel_sizes):
        rec += struct.pack(">hI", ch_id, ch_size)
    rec += b"8BIMnorm"
    rec += struct.pack(">BBBB", 255, 0, 0, 0)
    extra = b""
    extra += struct.pack(">I", 0)
    extra += struct.pack(">I", 0)
    name_bytes = name.encode("ascii", errors="replace")[:255]
    pascal = struct.pack(">B", len(name_bytes)) + name_bytes
    while len(pascal) % 4 != 0:
        pascal += b"\x00"
    extra += pascal
    rec += struct.pack(">I", len(extra))
    rec += extra
    return rec


def build_psd(width_px: int, height_px: int,
              layers: list[tuple[str, Image.Image]]) -> bytes:
    parts = []

    # File Header
    parts.append(b"8BPS")
    parts.append(struct.pack(">H", 1))
    parts.append(b"\x00" * 6)
    parts.append(struct.pack(">H", 3))
    parts.append(struct.pack(">II", height_px, width_px))
    parts.append(struct.pack(">H", 8))
    parts.append(struct.pack(">H", 3))

    # Color Mode Data
    parts.append(struct.pack(">I", 0))

    # Image Resources (DPI)
    res_data = struct.pack(">IHH IHH",
                           DPI * 65536, 1, 2,
                           DPI * 65536, 1, 2)
    res_block = (b"8BIM" + struct.pack(">HH", 0x03ED, 0) +
                 struct.pack(">I", len(res_data)) + res_data)
    if len(res_data) % 2:
        res_block += b"\x00"
    parts.append(struct.pack(">I", len(res_block)))
    parts.append(res_block)

    # Layer and Mask Info
    layer_records = []
    layer_channel_data = []

    for name, img in layers:
        img = img.convert("RGBA")
        is_bg = (name == "Background")
        if is_bg:
            cropped = img
            bx1, by1, bx2, by2 = 0, 0, width_px, height_px
        else:
            cropped, (bx1, by1, bx2, by2) = trim_to_content(img)

        crop_w = bx2 - bx1
        crop_h = by2 - by1
        r, g, b, a = cropped.split()

        ch_compressed = []
        for ch in [a, r, g, b]:
            arr = np.array(ch)
            compressed = compress_channel_rle(arr, crop_w, crop_h)
            ch_compressed.append(compressed)

        ch_sizes = [len(c) for c in ch_compressed]
        rec = build_layer_record(name, by1, bx1, by2, bx2, ch_sizes)
        layer_records.append(rec)
        layer_channel_data.append(ch_compressed)

    layer_info = struct.pack(">h", len(layers))
    for rec in layer_records:
        layer_info += rec
    for ch_list in layer_channel_data:
        for ch_data in ch_list:
            layer_info += ch_data

    if len(layer_info) % 2:
        layer_info += b"\x00"

    layer_section = struct.pack(">I", len(layer_info)) + layer_info
    layer_section += struct.pack(">I", 0)

    parts.append(struct.pack(">I", len(layer_section)))
    parts.append(layer_section)

    # Composite Image Data
    composite = Image.new("RGB", (width_px, height_px), (255, 255, 255))
    for _, img in layers:
        composite = Image.alpha_composite(composite.convert("RGBA"), img.convert("RGBA"))
    composite = composite.convert("RGB")
    r, g, b = composite.split()

    composite_parts = [struct.pack(">H", 1)]
    all_row_counts = []
    all_row_data = []
    for ch in [r, g, b]:
        arr = np.array(ch)
        for y in range(height_px):
            row_compressed = packbits_encode(arr[y].tobytes())
            all_row_counts.append(struct.pack(">H", len(row_compressed)))
            all_row_data.append(row_compressed)

    composite_parts.extend(all_row_counts)
    composite_parts.extend(all_row_data)
    parts.extend(composite_parts)

    return b"".join(parts)


# ---------------------------------------------------------------------------
# Template generators
# ---------------------------------------------------------------------------

def generate_template(size_name: str, crop: str = "full") -> Path:
    """Generate a PSD template for the given poster size and crop shape."""
    if size_name not in PRINT_SIZES:
        raise ValueError(f"Unknown size: {size_name}")

    config = PRINT_SIZES[size_name]
    width_px = config["width_in"] * DPI
    height_px = config["height_in"] * DPI

    print(f"\nGenerating {size_name} {crop} template ({width_px}x{height_px}px @ {DPI} DPI)...")

    map_rect = get_map_rect(width_px, height_px)
    map_w = map_rect[2] - map_rect[0]
    map_h = map_rect[3] - map_rect[1]
    print(f"  Map area: {map_w}x{map_h}px (left={map_rect[0]}, top={map_rect[1]})")

    layers: list[tuple[str, Image.Image]] = []

    # 1. Background
    bg = Image.new("RGBA", (width_px, height_px), (255, 255, 255, 255))
    layers.append(("Background", bg))

    # 2. Map placeholder (shape-aware)
    map_layer = create_map_placeholder(width_px, height_px, map_rect, crop)
    layers.append(("Map - Smart Object", map_layer))

    # 3. Shape outline (for non-full crops)
    if crop != "full":
        outline = create_shape_outline(width_px, height_px, map_rect, crop)
        layers.append(("Shape Outline", outline))

    # 4. Text layers only for full crop
    if crop == "full":
        ref_scale = min(config["width_in"], config["height_in"]) / 12.0
        title_size = int(63 * ref_scale)
        subtitle_size = int(20 * ref_scale)
        detail_size = int(18 * ref_scale)

        line1 = create_text_layer(width_px, height_px, "City Name",
                                  TEXT_LINE_1_Y, title_size)
        layers.append(("Line 1 - Title", line1))
        line2 = create_text_layer(width_px, height_px, "Subtitle Text",
                                  TEXT_LINE_2_Y, subtitle_size)
        layers.append(("Line 2 - Subtitle", line2))
        line3 = create_text_layer(width_px, height_px, "39.2859 N, 76.6254 W",
                                  TEXT_LINE_3_Y, detail_size)
        layers.append(("Line 3 - Detail", line3))

    # 5. Guides
    guides = create_guides_layer(width_px, height_px, map_rect,
                                 show_text_guides=(crop == "full"))
    layers.append(("Guides", guides))

    # Build and save
    psd_data = build_psd(width_px, height_px, layers)

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    crop_suffix = f"_{crop}" if crop != "full" else ""
    output_path = TEMPLATES_DIR / f"mapgen_template_{size_name}{crop_suffix}.psd"
    output_path.write_bytes(psd_data)

    file_mb = len(psd_data) / 1e6
    print(f"  Saved: {output_path} ({file_mb:.1f} MB)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate PSD templates for Photopea")
    parser.add_argument("--size", "-s", default="16x20",
                        help="Size (8x10, 11x14, 16x20, 18x24, 24x36, or 'all')")
    parser.add_argument("--crop", "-c", default="full",
                        help="Crop shape (full, heart, circle, house, or 'all')")
    args = parser.parse_args()

    sizes = list(PRINT_SIZES.keys()) if args.size == "all" else [args.size]
    crops = ALL_CROPS if args.crop == "all" else [args.crop]

    for size_name in sizes:
        for crop in crops:
            generate_template(size_name, crop)

    print("\nDone!")


if __name__ == "__main__":
    main()
