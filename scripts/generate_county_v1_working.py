#!/usr/bin/env python3
"""
MapGen — County Map Generator.

Generates map posters clipped to U.S. county boundaries instead of
rectangular bounding boxes.

Usage:
    python scripts/generate_county.py --county "Fairfax" --state "VA" --theme 37th_parallel --size 16x20
    python scripts/generate_county.py --county "Fairfax" --state "VA" --all-themes --size 16x20
    python scripts/generate_county.py --list-counties --state "VA"
"""

import argparse
import math
import os
import sys
import time

# Ensure project root is on sys.path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from engine.county_mask import (
    get_county_bounds,
    get_county_info,
    list_counties,
)
from engine.renderer import get_available_themes, load_theme, render_poster
from export.output_sizes import PRINT_SIZES


def _distance_from_bbox(
    bbox: tuple[float, float, float, float],
    padding_factor: float = 1.15,
) -> int:
    """Calculate a suitable distance (meters) from a county bounding box.

    bbox: (min_lon, min_lat, max_lon, max_lat) in EPSG:4269.
    Returns distance in meters that covers the county with padding.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    center_lat = (min_lat + max_lat) / 2.0

    # Approximate meters per degree at this latitude
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(center_lat))

    width_m = (max_lon - min_lon) * m_per_deg_lon
    height_m = (max_lat - min_lat) * m_per_deg_lat

    # Use the larger dimension as radius (half-extent), with padding
    half_extent = max(width_m, height_m) / 2.0
    return int(half_extent * padding_factor)


def generate_county_map(
    county_name: str,
    state: str,
    theme: str = "37th_parallel",
    size: str = "16x20",
    output_path: str | None = None,
    dpi: int = 300,
    font_preset: int = 1,
) -> str:
    """Generate a county-clipped map poster.

    Returns the path to the saved image.
    """
    info = get_county_info(county_name, state)
    center_lat, center_lon, bbox = get_county_bounds(county_name, state)

    distance = _distance_from_bbox(bbox, padding_factor=1.15)

    location = f"{center_lat},{center_lon}"

    # Build text lines
    text_line_1 = info["namelsad"]  # e.g., "Fairfax County"
    text_line_2 = info["state"]  # e.g., "Virginia"
    lat_dir = "N" if center_lat >= 0 else "S"
    lon_dir = "W" if center_lon < 0 else "E"
    text_line_3 = (
        f"{abs(center_lat):.4f}\u00b0 {lat_dir}  "
        f"{abs(center_lon):.4f}\u00b0 {lon_dir}"
    )

    # Default output path
    if output_path is None:
        county_slug = county_name.lower().replace(" ", "_")
        state_slug = state.lower().replace(" ", "_")
        output_dir = os.path.join(_PROJECT_DIR, "etsy", "renders", "CountyMap")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(
            output_dir,
            f"{county_slug}_{state_slug}_{theme}_{size}.png",
        )

    # County maps need boosted linewidths since they render at much wider
    # distances than city maps. Scale the zoom floor proportionally so roads
    # remain visible at county scale.
    min_zoom = 1.0

    # Enable detail layers for fill (residential, natural, landuse) but
    # buildings are skipped automatically for county crops in the renderer.
    result = render_poster(
        location=location,
        theme=theme,
        size=size,
        crop="county",
        detail_layers=True,
        distance=distance,
        font_preset=font_preset,
        text_line_1=text_line_1,
        text_line_2=text_line_2,
        text_line_3=text_line_3,
        dpi=dpi,
        output_path=output_path,
        county_name=county_name,
        county_state=state,
        min_zoom_scale=min_zoom,
    )

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MapGen — County Map Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--county", type=str, help="County name (e.g., 'Fairfax')")
    parser.add_argument("--state", type=str, required=True,
                        help="State abbreviation or name (e.g., 'VA' or 'Virginia')")
    parser.add_argument("--theme", type=str, default="37th_parallel",
                        help="Theme name (default: 37th_parallel)")
    parser.add_argument("--size", type=str, default="16x20",
                        choices=list(PRINT_SIZES.keys()),
                        help="Print size (default: 16x20)")
    parser.add_argument("--dpi", type=int, default=300,
                        help="Resolution (default: 300)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output file path")
    parser.add_argument("--font-preset", type=int, default=1,
                        choices=[1, 2, 3, 4, 5, 6],
                        help="Font preset (default: 1)")
    parser.add_argument("--all-themes", action="store_true",
                        help="Render in all available themes")
    parser.add_argument("--list-counties", action="store_true",
                        help="List all counties for the given state")

    args = parser.parse_args()

    # List mode
    if args.list_counties:
        counties = list_counties(args.state)
        print(f"\nCounties in {args.state} ({len(counties)} total):\n")
        for name in counties:
            print(f"  {name}")
        return

    if not args.county:
        parser.error("--county is required (unless using --list-counties)")

    # All-themes mode
    if args.all_themes:
        themes = get_available_themes()
        print(f"\nRendering {args.county} County, {args.state} in {len(themes)} themes...")
        for i, theme_data in enumerate(themes, 1):
            theme_id = theme_data["id"]
            # Skip special renderers (florence, nordic) — they have different pipelines
            if theme_data.get("renderer"):
                print(f"  [{i}/{len(themes)}] Skipping {theme_id} (custom renderer)")
                continue
            print(f"  [{i}/{len(themes)}] Rendering {theme_id}...")
            try:
                path = generate_county_map(
                    county_name=args.county,
                    state=args.state,
                    theme=theme_id,
                    size=args.size,
                    dpi=args.dpi,
                    font_preset=args.font_preset,
                )
                print(f"    -> {path}")
            except Exception as e:
                print(f"    [ERROR] {e}")
        return

    # Single render
    t_start = time.time()
    path = generate_county_map(
        county_name=args.county,
        state=args.state,
        theme=args.theme,
        size=args.size,
        output_path=args.output,
        dpi=args.dpi,
        font_preset=args.font_preset,
    )
    elapsed = time.time() - t_start
    print(f"\nCounty map saved: {path} ({elapsed:.1f}s)")


if __name__ == "__main__":
    main()
