"""Generate mockups for custom expansion listings.

Uses the mockup_composer's compose logic directly, pointing at
custom expansion renders instead of the standard city render directories.

Usage:
    python scripts/generate_custom_expansion_mockups.py --all
    python scripts/generate_custom_expansion_mockups.py --listing where_we_met
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
from psd_tools import PSDImage

from etsy.mockup_composer import (
    ALL_MOCKUPS,
    MockupDef,
    MockupSlot,
    fit_to_slot,
    get_smart_object_slots,
    find_city_render,
    MOCKUP_DIR,
)

BASE_DIR = Path("etsy/renders/CustomExpansion")

# Which render file to use as hero for each listing (24x36 and 18x24)
LISTING_RENDERS: dict[str, dict[str, str]] = {
    "where_we_met": {
        "24x36": "wwm_nashville_classic_24x36.png",
        "18x24": "wwm_nashville_classic_18x24.png",
    },
    "graduation_map": {
        "24x36": "grad_austin_classic_24x36.png",
        "18x24": "grad_austin_classic_18x24.png",
    },
    "multi_style_map": {
        "24x36": "style_nashville_classic_24x36.png",
        "18x24": "style_nashville_classic_18x24.png",
    },
    "born_in_map": {
        "24x36": "baby_nashville_beige_24x36.png",
        "18x24": "baby_nashville_beige_18x24.png",
    },
    "custom_blueprint": {
        "24x36": "blueprint_nashville_terracotta_24x36.png",
        "18x24": "blueprint_nashville_terracotta_18x24.png",
    },
}

# Filler cities for multi-frame mockups (use existing Classic posted renders)
FILLER_SLUGS = ["pittsburgh", "new_orleans", "washington_dc", "amsterdam"]


def load_render(path: Path) -> Image.Image:
    """Load a render as RGBA."""
    return Image.open(str(path)).convert("RGBA")


def load_filler(slug: str, render_size: str) -> Image.Image | None:
    """Load a filler city render from the standard posted directories."""
    path = find_city_render(slug, render_size)
    if path is None:
        return None
    return Image.open(str(path)).convert("RGBA")


def compose_single_mockup(
    mockup_def: MockupDef,
    featured_render: Image.Image,
    filler_renders: list[Image.Image],
    output_path: Path,
) -> Path | None:
    """Compose a mockup with featured + filler renders."""
    # Resolve PSD path
    if Path(mockup_def.filename).is_absolute():
        psd_path = Path(mockup_def.filename)
    else:
        psd_path = MOCKUP_DIR / mockup_def.filename

    if not psd_path.exists():
        print(f"    PSD not found: {psd_path}")
        return None

    psd = PSDImage.open(str(psd_path))
    base = psd.composite().convert("RGBA")

    # Determine slots
    if mockup_def.use_smart_object_bounds:
        slots = get_smart_object_slots(psd)
    else:
        slots = list(mockup_def.slots)

    if not slots:
        print(f"    No slots in {mockup_def.filename}")
        return None

    # Fill slots
    filler_idx = 0
    for i, slot in enumerate(slots):
        if i == mockup_def.featured_slot:
            fitted = fit_to_slot(featured_render, slot)
        else:
            if filler_idx < len(filler_renders):
                fitted = fit_to_slot(filler_renders[filler_idx], slot)
                filler_idx += 1
            else:
                fitted = fit_to_slot(featured_render, slot)
        base.paste(fitted, (slot.left, slot.top), fitted)

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(str(output_path), "JPEG", quality=95)
    return output_path


def generate_mockups(listing_slug: str) -> None:
    """Generate all 7 flat mockups for a listing."""
    renders = LISTING_RENDERS.get(listing_slug)
    if not renders:
        print(f"  No render mapping for {listing_slug}")
        return

    out_dir = BASE_DIR / listing_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load featured renders
    featured_24x36_path = out_dir / renders["24x36"]
    featured_18x24_path = out_dir / renders["18x24"]

    if not featured_24x36_path.exists():
        print(f"  Missing 24x36: {featured_24x36_path}")
        return
    if not featured_18x24_path.exists():
        print(f"  Missing 18x24: {featured_18x24_path}")
        return

    featured_24 = load_render(featured_24x36_path)
    featured_18 = load_render(featured_18x24_path)

    # Load filler renders (Classic posted cities)
    fillers_24: list[Image.Image] = []
    fillers_18: list[Image.Image] = []
    for slug in FILLER_SLUGS:
        img = load_filler(slug, "24x36")
        if img:
            fillers_24.append(img)
        img = load_filler(slug, "18x24")
        if img:
            fillers_18.append(img)

    print(f"  Loaded {len(fillers_24)} fillers (24x36), {len(fillers_18)} fillers (18x24)")

    # Generate each mockup
    for mockup_def in ALL_MOCKUPS:
        if mockup_def.render_size == "18x24":
            featured = featured_18
            fillers = fillers_18
        else:
            featured = featured_24
            fillers = fillers_24

        out_path = out_dir / f"mockup_{mockup_def.short_name}.jpg"
        print(f"  Composing {mockup_def.short_name}...", end="", flush=True)
        result = compose_single_mockup(mockup_def, featured, fillers, out_path)
        if result:
            print(f" OK ({result.stat().st_size // 1024}KB)")
        else:
            print(" FAILED")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate mockups for custom expansion")
    parser.add_argument("--listing", "-l", help="Generate for one listing")
    parser.add_argument("--all", "-a", action="store_true", help="Generate all")
    args = parser.parse_args()

    if args.all:
        for slug in LISTING_RENDERS:
            print(f"\n=== {slug} ===")
            generate_mockups(slug)
    elif args.listing:
        print(f"=== {args.listing} ===")
        generate_mockups(args.listing)
    else:
        parser.print_help()

    print("\nDone!")


if __name__ == "__main__":
    main()
