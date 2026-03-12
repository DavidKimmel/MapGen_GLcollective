#!/usr/bin/env python3
"""
MapGen — CLI Single Poster Generator.

Usage:
    python cli.py --location "New York" --theme 37th_parallel --size 16x20
    python cli.py --location "Paris" --crop heart --pin-address "Eiffel Tower" --pin-style 2
    python cli.py --location "41.88,-87.62" --text-line-1 "Our Home" --font-preset 3
"""

import argparse
import sys

from engine.renderer import render_poster
from export.output_sizes import PRINT_SIZES


def main():
    parser = argparse.ArgumentParser(
        description="MapGen — Generate print-quality map posters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--location", "-l", required=True,
                        help="City name or lat,lon (e.g., 'New York' or '40.71,-74.00')")
    parser.add_argument("--theme", "-t", default="37th_parallel",
                        help="Theme name (default: 37th_parallel)")
    parser.add_argument("--size", "-s", default="16x20",
                        choices=list(PRINT_SIZES.keys()),
                        help="Print size (default: 16x20)")
    parser.add_argument("--crop", "-c", default="full",
                        choices=["full", "circle", "heart", "house"],
                        help="Crop shape (default: full)")
    parser.add_argument("--detail-layers", action="store_true", default=True,
                        help="Enable all 11 detail layers (default)")
    parser.add_argument("--no-detail-layers", action="store_true",
                        help="Minimal layers: roads + water + parks only")
    parser.add_argument("--distance", "-d", type=int, default=None,
                        help="Map radius in meters (auto from size if not set)")
    parser.add_argument("--pin-address", default=None,
                        help="Address to place a pin marker")
    parser.add_argument("--pin-style", type=int, default=1, choices=[1, 2, 3, 4, 5],
                        help="Pin style: 1=heart, 2=heart-pin, 3=classic, 4=house, 5=grad cap")
    parser.add_argument("--pin-color", default=None,
                        help="Custom hex color for pin (e.g., #D4736B)")
    parser.add_argument("--font-preset", type=int, default=1, choices=[1, 2, 3, 4, 5],
                        help="Font preset: 1=sans, 2=serif, 3=script, 4=cursive, 5=classic")
    parser.add_argument("--text-line-1", default=None,
                        help="Large title text (e.g., 'Our First Home')")
    parser.add_argument("--text-line-2", default=None,
                        help="Medium subtitle text (e.g., 'Chicago, Illinois')")
    parser.add_argument("--text-line-3", default=None,
                        help="Small detail text (e.g., 'Est. June 2019')")
    parser.add_argument("--dpi", type=int, default=300,
                        help="Resolution in DPI (default: 300)")
    parser.add_argument("--output", "-o", default=None,
                        help="Output file path (auto-generated if not set)")
    parser.add_argument("--border", action="store_true",
                        help="Add double-line border")
    parser.add_argument("--map-only", action="store_true",
                        help="Render map only (no text, no margins) for PSD templates")

    args = parser.parse_args()

    detail_layers = not args.no_detail_layers

    # Geocode pin address if provided
    pin_lat = None
    pin_lon = None
    if args.pin_address:
        from utils.geocoding import parse_location
        pin_lat, pin_lon, _ = parse_location(args.pin_address)

    try:
        output = render_poster(
            location=args.location,
            theme=args.theme,
            size=args.size,
            crop=args.crop,
            detail_layers=detail_layers,
            distance=args.distance,
            pin_lat=pin_lat,
            pin_lon=pin_lon,
            pin_style=args.pin_style,
            pin_color=args.pin_color,
            font_preset=args.font_preset,
            text_line_1=args.text_line_1,
            text_line_2=args.text_line_2,
            text_line_3=args.text_line_3,
            dpi=args.dpi,
            output_path=args.output,
            border=args.border,
            map_only=args.map_only,
        )
        print(f"\nPoster saved: {output}")
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
