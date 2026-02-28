"""
MapGen — Gelato Print Export.

Converts map poster PNGs to Gelato-ready files with proper sizing and bleed.

Gelato Requirements:
  - 300 DPI at final print size
  - sRGB color space
  - 4mm bleed on all sides
"""

import argparse
import os
import sys
from pathlib import Path

from utils.logging import safe_print

try:
    from PIL import Image
except ImportError:
    safe_print("Pillow is required: pip install Pillow")
    sys.exit(1)

POSTER_SIZES = {
    "8x10": (8, 10),
    "11x14": (11, 14),
    "16x20": (16, 20),
    "18x24": (18, 24),
    "24x36": (24, 36),
}

DPI = 300
BLEED_MM = 4
BLEED_INCHES = BLEED_MM / 25.4
BLEED_PX = int(round(BLEED_INCHES * DPI))


def calc_dimensions(width_in: float, height_in: float, dpi: int = 300) -> dict:
    """Calculate pixel dimensions for a given print size with bleed."""
    trim_w = int(width_in * dpi)
    trim_h = int(height_in * dpi)
    bleed_w = trim_w + (2 * BLEED_PX)
    bleed_h = trim_h + (2 * BLEED_PX)
    safe_w = trim_w - (2 * BLEED_PX)
    safe_h = trim_h - (2 * BLEED_PX)
    return {
        "trim": (trim_w, trim_h),
        "bleed": (bleed_w, bleed_h),
        "safe": (safe_w, safe_h),
    }


def export_for_gelato(source_path: str, output_dir: str,
                      sizes: list[str] | None = None,
                      bg_color: str = "#F5F2ED") -> list[dict]:
    """Export a source poster image to Gelato-ready file(s).

    For each target size:
      1. If source matches target dimensions, uses as-is (no quality loss)
      2. Otherwise crops to target aspect ratio and resizes to 300 DPI
      3. Adds 4mm bleed by extending edge pixels outward
      4. Saves as PNG with DPI metadata
    """
    if sizes is None:
        sizes = list(POSTER_SIZES.keys())

    source = Image.open(source_path).convert("RGB")
    src_w, src_h = source.size

    stem = Path(source_path).stem
    parts = stem.split("_")
    city_name = parts[0]

    safe_print(f"Source: {source_path} ({src_w}x{src_h} px)")
    safe_print(f"Bleed: {BLEED_MM}mm ({BLEED_PX}px at {DPI} DPI)")
    safe_print("")

    results = []

    for size_name in sizes:
        if size_name not in POSTER_SIZES:
            safe_print(f"  [!] Unknown size '{size_name}', skipping")
            continue

        w_in, h_in = POSTER_SIZES[size_name]
        dims = calc_dimensions(w_in, h_in)
        trim_w, trim_h = dims["trim"]
        bleed_w, bleed_h = dims["bleed"]

        target_ratio = w_in / h_in
        src_ratio = src_w / src_h

        if src_ratio > target_ratio:
            effective_dpi = src_h / h_in
        else:
            effective_dpi = src_w / w_in

        if effective_dpi < 150:
            safe_print(f"  [!] {size_name}: Source resolution too low "
                       f"(~{effective_dpi:.0f} DPI). Skipping.")
            continue

        # Fast path: source already matches target (rendered at this size)
        if src_w == trim_w and src_h == trim_h:
            resized = source
            safe_print(f"  Source matches {size_name} exactly — no crop/resize needed")
        else:
            # Crop to match target aspect ratio
            if src_ratio > target_ratio:
                new_w = int(src_h * target_ratio)
                left = (src_w - new_w) // 2
                cropped = source.crop((left, 0, left + new_w, src_h))
            else:
                new_h = int(src_w / target_ratio)
                top = (src_h - new_h) // 2
                cropped = source.crop((0, top, src_w, top + new_h))

            resized = cropped.resize((trim_w, trim_h), Image.LANCZOS)

        # Create canvas with bleed
        canvas = Image.new("RGB", (bleed_w, bleed_h), bg_color)
        canvas.paste(resized, (BLEED_PX, BLEED_PX))

        # Extend edge pixels into bleed area
        top_strip = resized.crop((0, 0, trim_w, 1))
        for y in range(BLEED_PX):
            canvas.paste(top_strip, (BLEED_PX, y))

        bottom_strip = resized.crop((0, trim_h - 1, trim_w, trim_h))
        for y in range(BLEED_PX):
            canvas.paste(bottom_strip, (BLEED_PX, BLEED_PX + trim_h + y))

        left_strip = resized.crop((0, 0, 1, trim_h))
        for x in range(BLEED_PX):
            canvas.paste(left_strip, (x, BLEED_PX))

        right_strip = resized.crop((trim_w - 1, 0, trim_w, trim_h))
        for x in range(BLEED_PX):
            canvas.paste(right_strip, (BLEED_PX + trim_w + x, BLEED_PX))

        # Fill corners
        tl = resized.getpixel((0, 0))
        tr = resized.getpixel((trim_w - 1, 0))
        bl = resized.getpixel((0, trim_h - 1))
        br = resized.getpixel((trim_w - 1, trim_h - 1))

        for y in range(BLEED_PX):
            for x in range(BLEED_PX):
                canvas.putpixel((x, y), tl)
                canvas.putpixel((BLEED_PX + trim_w + x, y), tr)
                canvas.putpixel((x, BLEED_PX + trim_h + y), bl)
                canvas.putpixel((BLEED_PX + trim_w + x, BLEED_PX + trim_h + y), br)

        size_dir = Path(output_dir) / size_name
        size_dir.mkdir(parents=True, exist_ok=True)
        out_path = size_dir / f"{city_name}_{size_name}_gelato.png"

        canvas.save(str(out_path), "PNG", dpi=(DPI, DPI))
        file_size_mb = out_path.stat().st_size / 1e6

        safe_print(f"  [OK] {size_name}: {bleed_w}x{bleed_h}px "
                   f"(trim {trim_w}x{trim_h} + {BLEED_MM}mm bleed) "
                   f"[{file_size_mb:.1f} MB] -> {out_path}")

        results.append({
            "size": size_name,
            "path": str(out_path),
            "dimensions": f"{bleed_w}x{bleed_h}",
            "file_size_mb": round(file_size_mb, 1),
        })

    safe_print(f"\nDone! {len(results)} Gelato-ready files in: {output_dir}/")
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Export map posters for Gelato printing",
    )
    parser.add_argument("--input", "-i", help="Source poster PNG file")
    parser.add_argument("--input-dir", help="Process all PNGs in directory")
    parser.add_argument("--output", "-o", default="gelato_ready",
                        help="Output directory (default: gelato_ready)")
    parser.add_argument("--sizes", nargs="+", default=None,
                        choices=list(POSTER_SIZES.keys()),
                        help="Specific sizes to export (default: all)")
    parser.add_argument("--theme", "-t", default=None,
                        help="Filter input-dir to only process this theme")
    parser.add_argument("--bg-color", default="#F5F2ED",
                        help="Background color for bleed (default: cream)")

    args = parser.parse_args()

    if args.input:
        if not os.path.exists(args.input):
            print(f"Error: File not found: {args.input}")
            sys.exit(1)
        export_for_gelato(args.input, args.output, args.sizes, args.bg_color)
    elif args.input_dir:
        input_dir = Path(args.input_dir)
        if not input_dir.exists():
            print(f"Error: Directory not found: {args.input_dir}")
            sys.exit(1)
        pattern = f"*_{args.theme}_*.png" if args.theme else "*.png"
        files = sorted(input_dir.glob(pattern))
        if not files:
            print(f"No matching PNG files found in {args.input_dir}")
            sys.exit(1)
        print(f"Found {len(files)} poster(s) to export\n")
        for png in files:
            print(f"{'=' * 60}")
            export_for_gelato(str(png), args.output, args.sizes, args.bg_color)
            safe_print("")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
