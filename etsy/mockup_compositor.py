"""GeoLine Collective — Mockup Template Compositor.

Composites city poster renders into pre-generated room scene templates.
Templates have bright magenta (#FF00FF) placeholder regions that get
detected, masked, and replaced with the poster image.

Handles:
  - Perspective-warped frames (angled/tilted frames)
  - Multi-frame templates (dual/triple) — featured city center, others flanking
  - Shadow/lighting preservation from the original template
  - Batch processing across all cities and templates

Usage:
    python -m etsy.mockup_compositor --city Chicago
    python -m etsy.mockup_compositor --tier 1
    python -m etsy.mockup_compositor --city Chicago --templates single_white_wall,single_dark_shelf
    python -m etsy.mockup_compositor --list-templates
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from etsy.city_list import ALL_CITIES, CityListing, get_cities_by_tier, get_city
from etsy.batch_etsy_render import RENDERS_DIR

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "mockup_templates")

# Magenta detection: chromatic approach
# Detect pixels where R and B dominate over G (magenta family)
# Thresholds calibrated against Leonardo FLUX Kontext output
MAGENTA_R_MIN = 150       # Minimum red channel
MAGENTA_B_MIN = 80        # Minimum blue channel
MAGENTA_RG_DIFF = 30      # Minimum (R - G) gap
MAGENTA_BG_DIFF = 5       # Minimum (B - G) gap
MAGENTA_G_MAX = 160       # Absolute max green

# Minimum area for a placeholder region (as fraction of image area)
MIN_REGION_FRACTION = 0.005

# Template definitions — which templates exist and how many frames they have
TEMPLATE_DEFS: list[dict] = [
    {
        "id": "black_poster_frame",
        "name": "Black Poster Frame on White",
        "file": "AI/lucid-origin_Create_a_simple_frame_against_a_white_backdrop._The_frame_is_a_poster_frame_with-0.jpg",
        "frames": 1,
    },
    {
        "id": "black_frame_clean",
        "name": "Black Frame Clean",
        "file": "AI/lucid-origin_large_thin_black_frame_no_mat_blank_white_interior_frame_dominates_the_compositi-0.jpg",
        "frames": 1,
    },
    {
        "id": "white_frame_wall",
        "name": "White Frame on Wall",
        "file": "AI/il_1588xN.7436710975_hgkx.jpg",
        "frames": 1,
    },
    {
        "id": "wood_shelf",
        "name": "Wood Frame on Shelf",
        "file": "AI/lucid-origin_Photorealistic_Scandinavian_interior_light_gray_wall_natural_oak_floating_shelf_-0.jpg",
        "frames": 1,
    },
    {
        "id": "wood_frame_sofa",
        "name": "Wood Frame Above Sofa",
        "file": "AI/lucid-origin_Minimal_neutral_living_room_blurred_sofa_edges_at_bottom_of_frame_large_wooden_f-0.jpg",
        "frames": 1,
    },
    {
        "id": "dual_white_sofa",
        "name": "Two White Frames Above Sofa",
        "file": "AI/lucid-origin_Bright_airy_Scandinavian_living_room_interior_two_large_thin_white_picture_frame-0.jpg",
        "frames": 2,
    },
    {
        "id": "size_comparison",
        "name": "Size Comparison (8x10, 11x14, 18x24)",
        "file": "AI/gemini-2.5-flash-image_Recreate_but_use_empty_frames_no_mat_no_shadows._Light_grey_wall._Keep_all_3_fra-0.jpg",
        "frames": 3,
    },
]


def _template_by_id(tid: str) -> dict | None:
    for t in TEMPLATE_DEFS:
        if t["id"] == tid:
            return t
    return None


# ---------------------------------------------------------------------------
# Magenta region detection
# ---------------------------------------------------------------------------

def detect_magenta_regions(
    img: Image.Image,
) -> list[dict]:
    """Detect magenta placeholder regions in a template image.

    Returns a list of region dicts sorted left-to-right, each containing:
      - 'bbox': (x1, y1, x2, y2) bounding box
      - 'mask': PIL Image mask of the region
      - 'corners': list of 4 (x, y) corner points (for perspective)
      - 'center_x': horizontal center for sorting
    """
    arr = np.array(img)
    r = arr[:, :, 0].astype(np.int16)
    g = arr[:, :, 1].astype(np.int16)
    b = arr[:, :, 2].astype(np.int16)
    # Chromatic magenta detection: R and B dominate over G
    magenta = (
        (r > MAGENTA_R_MIN) &
        (b > MAGENTA_B_MIN) &
        (g < MAGENTA_G_MAX) &
        ((r - g) > MAGENTA_RG_DIFF) &
        ((b - g) > MAGENTA_BG_DIFF)
    )

    # Dilate mask to catch anti-aliased edges around the magenta regions
    try:
        from scipy import ndimage as ndi
        magenta = ndi.binary_dilation(magenta, iterations=4)
    except ImportError:
        pass

    # Label connected components via flood fill
    regions = _find_connected_regions(magenta)

    # Filter by minimum size
    min_area = img.width * img.height * MIN_REGION_FRACTION
    regions = [r for r in regions if r["area"] >= min_area]

    # Expand each region through white matting to fill the full frame interior
    regions = [_expand_through_matting(r, arr) for r in regions]

    # Sort left-to-right by center x
    regions.sort(key=lambda r: r["center_x"])

    return regions


def _expand_through_matting(
    region: dict,
    img_arr: np.ndarray,
    white_thresh: int = 220,
    scan_limit: int = 200,
) -> dict:
    """Expand a magenta region outward through white matting to the frame edge.

    Scans outward from each edge of the magenta bounding box through
    white/near-white pixels until hitting darker pixels (the frame).
    This makes the poster fill the entire frame interior, not just the magenta.

    The poster's own built-in white margin (with city name text) then serves
    as the visual 'matting', matching competitor style.
    """
    x1, y1, x2, y2 = region["bbox"]
    h, w = img_arr.shape[:2]

    # Helper: check if a row/column slice is mostly white
    def is_white_row(row_pixels: np.ndarray) -> bool:
        """Check if pixels are mostly white (matting)."""
        if len(row_pixels) == 0:
            return False
        avg = row_pixels.mean(axis=0)  # Average RGB
        return avg[0] > white_thresh and avg[1] > white_thresh and avg[2] > white_thresh

    # Expand upward
    mid_x_start = x1 + (x2 - x1) // 4
    mid_x_end = x1 + 3 * (x2 - x1) // 4
    new_y1 = y1
    for y in range(y1 - 1, max(0, y1 - scan_limit), -1):
        row = img_arr[y, mid_x_start:mid_x_end]
        if is_white_row(row):
            new_y1 = y
        else:
            break

    # Expand downward
    new_y2 = y2
    for y in range(y2 + 1, min(h, y2 + scan_limit)):
        row = img_arr[y, mid_x_start:mid_x_end]
        if is_white_row(row):
            new_y2 = y
        else:
            break

    # Expand left
    mid_y_start = y1 + (y2 - y1) // 4
    mid_y_end = y1 + 3 * (y2 - y1) // 4
    new_x1 = x1
    for x in range(x1 - 1, max(0, x1 - scan_limit), -1):
        col = img_arr[mid_y_start:mid_y_end, x]
        if is_white_row(col):
            new_x1 = x
        else:
            break

    # Expand right
    new_x2 = x2
    for x in range(x2 + 1, min(w, x2 + scan_limit)):
        col = img_arr[mid_y_start:mid_y_end, x]
        if is_white_row(col):
            new_x2 = x
        else:
            break

    # Build new expanded region
    new_w = new_x2 - new_x1
    new_h = new_y2 - new_y1

    # Create a simple rectangular mask for the expanded region
    expanded_mask = np.zeros((h, w), dtype=np.uint8)
    expanded_mask[new_y1:new_y2, new_x1:new_x2] = 255
    pil_mask = Image.fromarray(expanded_mask)

    return {
        "bbox": (new_x1, new_y1, new_x2, new_y2),
        "mask": pil_mask,
        "corners": [
            (new_x1, new_y1), (new_x2, new_y1),
            (new_x2, new_y2), (new_x1, new_y2),
        ],
        "area": new_w * new_h,
        "center_x": (new_x1 + new_x2) / 2,
    }


def _find_connected_regions(mask: np.ndarray) -> list[dict]:
    """Find connected regions in a boolean mask using simple flood fill.

    Returns list of region dicts with bbox, mask image, corners, area, center_x.
    """
    h, w = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    regions = []

    # Use scipy if available for faster labeling, otherwise manual
    try:
        from scipy import ndimage
        labeled, num_features = ndimage.label(mask)
        for label_id in range(1, num_features + 1):
            region_mask = labeled == label_id
            ys, xs = np.where(region_mask)
            if len(ys) == 0:
                continue
            y1, y2 = int(ys.min()), int(ys.max())
            x1, x2 = int(xs.min()), int(xs.max())
            area = int(region_mask.sum())
            center_x = (x1 + x2) / 2

            # Create PIL mask
            pil_mask = Image.fromarray((region_mask * 255).astype(np.uint8))

            # Find corners using the convex hull approximation
            corners = _find_quad_corners(region_mask, x1, y1, x2, y2)

            regions.append({
                "bbox": (x1, y1, x2, y2),
                "mask": pil_mask,
                "corners": corners,
                "area": area,
                "center_x": center_x,
            })
        return regions
    except ImportError:
        pass

    # Fallback: scan for contiguous horizontal runs and merge
    # Group magenta pixels by bounding box clusters
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return []

    # Simple approach: use row-based clustering
    # For our templates, magenta regions are well-separated rectangles
    # so we can use a simpler bbox-based approach
    from collections import deque

    for start_y in range(h):
        for start_x in range(w):
            if mask[start_y, start_x] and not visited[start_y, start_x]:
                # BFS flood fill
                queue = deque([(start_y, start_x)])
                visited[start_y, start_x] = True
                pixels = []

                while queue:
                    cy, cx = queue.popleft()
                    pixels.append((cy, cx))

                    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not visited[ny, nx]:
                            visited[ny, nx] = True
                            queue.append((ny, nx))

                if not pixels:
                    continue

                pys = [p[0] for p in pixels]
                pxs = [p[1] for p in pixels]
                y1, y2 = min(pys), max(pys)
                x1, x2 = min(pxs), max(pxs)
                area = len(pixels)
                center_x = (x1 + x2) / 2

                region_mask = np.zeros_like(mask, dtype=np.uint8)
                for py, px in pixels:
                    region_mask[py, px] = 255
                pil_mask = Image.fromarray(region_mask)

                corners = _find_quad_corners(
                    region_mask.astype(bool), x1, y1, x2, y2
                )

                regions.append({
                    "bbox": (x1, y1, x2, y2),
                    "mask": pil_mask,
                    "corners": corners,
                    "area": area,
                    "center_x": center_x,
                })

    return regions


def _find_quad_corners(
    region_mask: np.ndarray,
    x1: int, y1: int, x2: int, y2: int,
) -> list[tuple[int, int]]:
    """Find the 4 corner points of a quadrilateral region.

    Uses rows ~5% from top/bottom to avoid thin edge artifacts from
    perspective-angled frames.
    Returns: [(top_left), (top_right), (bottom_right), (bottom_left)]
    """
    ys, xs = np.where(region_mask)
    if len(ys) == 0:
        return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]

    y_min, y_max = int(ys.min()), int(ys.max())
    height = y_max - y_min
    if height < 10:
        return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]

    # Sample rows at 5% and 95% to get stable edge measurements
    margin = max(3, int(height * 0.05))
    top_band_y = y_min + margin
    bottom_band_y = y_max - margin

    # Get x range in the top band (rows near top)
    top_band = (ys >= y_min) & (ys <= top_band_y)
    top_xs = xs[top_band]
    if len(top_xs) == 0:
        top_xs = xs[ys == y_min]

    # Get x range in the bottom band
    bottom_band = (ys >= bottom_band_y) & (ys <= y_max)
    bottom_xs = xs[bottom_band]
    if len(bottom_xs) == 0:
        bottom_xs = xs[ys == y_max]

    top_left = (int(top_xs.min()), y_min)
    top_right = (int(top_xs.max()), y_min)
    bottom_left = (int(bottom_xs.min()), y_max)
    bottom_right = (int(bottom_xs.max()), y_max)

    return [top_left, top_right, bottom_right, bottom_left]


# ---------------------------------------------------------------------------
# Perspective warp and compositing
# ---------------------------------------------------------------------------

def composite_poster_into_region(
    template: Image.Image,
    poster: Image.Image,
    region: dict,
) -> Image.Image:
    """Composite a poster image into a detected magenta region.

    Simple approach: resize poster to fit the bounding box, paste with mask.
    No shadow/glass effects — clean paste matching competitor style.

    Args:
        template: The room scene template
        poster: The poster to place into the frame
        region: Region dict from detect_magenta_regions()

    Returns:
        The composited template image
    """
    mask = region["mask"]
    bbox = region["bbox"]
    x1, y1, x2, y2 = bbox

    region_w = x2 - x1
    region_h = y2 - y1

    if region_w <= 0 or region_h <= 0:
        return template

    # Resize poster to COVER the region while preserving aspect ratio,
    # then center-crop to exact region size. This prevents stretching/distortion.
    poster_w, poster_h = poster.size
    scale = max(region_w / poster_w, region_h / poster_h)
    scaled_w = round(poster_w * scale)
    scaled_h = round(poster_h * scale)
    poster_scaled = poster.resize((scaled_w, scaled_h), Image.LANCZOS)

    # Center-crop to match region dimensions
    crop_x = (scaled_w - region_w) // 2
    crop_y = (scaled_h - region_h) // 2
    poster_resized = poster_scaled.crop((
        crop_x, crop_y, crop_x + region_w, crop_y + region_h
    ))

    # Create a cropped mask for just the region bbox
    mask_crop = mask.crop((x1, y1, x2, y2))

    # Simple paste with mask — clean and straightforward
    result = template.copy()
    result.paste(poster_resized, (x1, y1), mask_crop)
    return result




# ---------------------------------------------------------------------------
# High-level compositing functions
# ---------------------------------------------------------------------------

def composite_single_template(
    template_id: str,
    city: CityListing,
    other_cities: list[CityListing] | None = None,
    output_path: str | None = None,
) -> str | None:
    """Composite a city's poster into a specific template.

    For multi-frame templates, other_cities are used for flanking frames.
    The featured city always goes in the center (or leftmost for dual).

    Args:
        template_id: Template ID from TEMPLATE_DEFS
        city: Primary city to feature
        other_cities: Cities for additional frames (auto-selected if None)
        output_path: Override output file path

    Returns:
        Output file path, or None if failed
    """
    tdef = _template_by_id(template_id)
    if not tdef:
        print(f"  [!] Unknown template: {template_id}")
        return None

    template_path = os.path.join(TEMPLATES_DIR, tdef["file"])
    if not os.path.exists(template_path):
        print(f"  [!] Template not found: {template_path}")
        return None

    # Find the city's hero poster
    city_dir = os.path.join(RENDERS_DIR, city.slug)
    hero_path = os.path.join(city_dir, f"{city.slug}_37th_parallel_16x20.png")
    if not os.path.exists(hero_path):
        print(f"  [!] No hero render: {hero_path}")
        return None

    # Load template and poster
    template = Image.open(template_path).convert("RGB")
    poster = Image.open(hero_path).convert("RGB")

    # Detect placeholder regions
    regions = detect_magenta_regions(template)
    expected_frames = tdef["frames"]

    if len(regions) < expected_frames:
        print(
            f"  [!] Expected {expected_frames} frames in {template_id}, "
            f"found {len(regions)}"
        )
        if len(regions) == 0:
            return None

    # Assign posters to frames
    posters = _assign_posters_to_frames(
        city, poster, regions, other_cities
    )

    # Composite each poster into its region
    result = template
    for region, poster_img in zip(regions[:len(posters)], posters):
        result = composite_poster_into_region(result, poster_img, region)

    # Save output
    if output_path is None:
        output_path = os.path.join(
            city_dir, f"mockup_{template_id}.png"
        )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    result.save(output_path, "PNG", optimize=True)
    print(f"    Saved: {os.path.basename(output_path)}")
    return output_path


def _assign_posters_to_frames(
    city: CityListing,
    poster: Image.Image,
    regions: list[dict],
    other_cities: list[CityListing] | None,
) -> list[Image.Image]:
    """Assign poster images to frame regions.

    For single-frame: just the featured city.
    For dual-frame: featured city left, other city right.
    For triple-frame: other city left, featured center, other right.
    """
    num_frames = len(regions)

    if num_frames == 1:
        return [poster]

    # For multi-frame, load other city posters
    all_posters = [poster]

    if other_cities:
        for oc in other_cities[:num_frames - 1]:
            oc_path = os.path.join(
                RENDERS_DIR, oc.slug,
                f"{oc.slug}_37th_parallel_16x20.png"
            )
            if os.path.exists(oc_path):
                all_posters.append(Image.open(oc_path).convert("RGB"))
            else:
                # Re-use the main poster
                all_posters.append(poster)
    else:
        # Auto-select other cities from the same tier
        same_tier = [
            c for c in ALL_CITIES
            if c.tier == city.tier and c.slug != city.slug
        ]
        for oc in same_tier[:num_frames - 1]:
            oc_path = os.path.join(
                RENDERS_DIR, oc.slug,
                f"{oc.slug}_37th_parallel_16x20.png"
            )
            if os.path.exists(oc_path):
                all_posters.append(Image.open(oc_path).convert("RGB"))
            else:
                all_posters.append(poster)

    # Pad if needed
    while len(all_posters) < num_frames:
        all_posters.append(poster)

    if num_frames == 2:
        # Featured city left, other right
        return [all_posters[0], all_posters[1]]
    elif num_frames == 3:
        # Other, featured center, other
        return [all_posters[1], all_posters[0], all_posters[2]]
    else:
        return all_posters[:num_frames]


def composite_city_mockups(
    city: CityListing,
    template_ids: list[str] | None = None,
) -> dict[str, str | None]:
    """Generate all mockup composites for a city.

    Args:
        city: City to generate mockups for
        template_ids: Specific templates (None = all)

    Returns:
        Dict of template_id -> output_path (None if failed)
    """
    templates = TEMPLATE_DEFS if template_ids is None else [
        t for t in TEMPLATE_DEFS if t["id"] in template_ids
    ]

    print(f"\n  Compositing mockups: {city.city}, {city.state}")

    results: dict[str, str | None] = {}
    for tdef in templates:
        result = composite_single_template(tdef["id"], city)
        results[tdef["id"]] = result

    success = sum(1 for v in results.values() if v is not None)
    print(f"  Done: {success}/{len(templates)} mockups for {city.city}")
    return results


def composite_batch_mockups(
    cities: list[CityListing],
    template_ids: list[str] | None = None,
) -> dict[str, dict[str, str | None]]:
    """Generate mockup composites for multiple cities.

    Returns:
        Dict of city_slug -> {template_id -> output_path}
    """
    print(f"\n{'#' * 60}")
    print(f"GeoLine Collective — Mockup Compositor")
    print(f"  Cities: {len(cities)}")
    templates = template_ids or [t["id"] for t in TEMPLATE_DEFS]
    print(f"  Templates: {len(templates)} per city")
    print(f"  Estimated total: ~{len(cities) * len(templates)} images")
    print(f"{'#' * 60}")

    all_results: dict[str, dict[str, str | None]] = {}
    for i, city in enumerate(cities, 1):
        print(f"\n[{i}/{len(cities)}]")
        results = composite_city_mockups(city, template_ids=template_ids)
        all_results[city.slug] = results

    # Summary
    total = sum(
        1 for cr in all_results.values()
        for v in cr.values() if v is not None
    )
    print(f"\n{'#' * 60}")
    print(f"Batch complete: {total} mockup images composited")
    print(f"{'#' * 60}")

    return all_results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Composite posters into mockup templates"
    )
    parser.add_argument("--tier", type=int, default=None, help="Tier (1/2/3)")
    parser.add_argument("--city", type=str, default=None, help="Single city")
    parser.add_argument("--all", action="store_true", help="All cities")
    parser.add_argument(
        "--templates", type=str, default=None,
        help="Comma-separated template IDs"
    )
    parser.add_argument(
        "--list-templates", action="store_true", help="List templates"
    )
    args = parser.parse_args()

    if args.list_templates:
        print("Available mockup templates:")
        for t in TEMPLATE_DEFS:
            print(f"  {t['id']:25s} — {t['name']} ({t['frames']} frame(s))")
        return

    template_ids = args.templates.split(",") if args.templates else None

    if args.city:
        city = get_city(args.city)
        if not city:
            print(f"City not found: {args.city}")
            sys.exit(1)
        composite_city_mockups(city, template_ids=template_ids)
    elif args.all:
        composite_batch_mockups(ALL_CITIES, template_ids=template_ids)
    elif args.tier:
        cities = get_cities_by_tier(args.tier)
        composite_batch_mockups(cities, template_ids=template_ids)
    else:
        print("Specify --tier, --city, or --all")
        sys.exit(1)


if __name__ == "__main__":
    main()
