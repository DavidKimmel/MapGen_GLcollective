"""Post-process Florence renders — mockups, detail crops, size comparisons, listing text.

Expects renders in etsy/renders/{slug}_florence/{slug}_{size}.png

Usage:
    python scripts/batch_florence_postprocess.py
    python scripts/batch_florence_postprocess.py --city chicago
"""

import argparse
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from pathlib import Path
from PIL import Image
from psd_tools import PSDImage

RENDERS_DIR = Path("etsy/renders")
MOCKUP_DIR = Path("etsy/TUR2/Best/Flat")
SIZES = ["8x10", "11x14", "16x20", "18x24", "24x36"]

# Filler cities for multi-frame mockups — use Florence renders
FILLER_SLUGS = ["pittsburgh", "new_orleans", "washington_dc", "nashville"]


def get_florence_cities() -> list[str]:
    """Find all city slugs that have Florence renders."""
    slugs = []
    for d in sorted(RENDERS_DIR.iterdir()):
        if d.is_dir() and d.name.endswith("_florence"):
            slug = d.name.replace("_florence", "")
            # Check has at least a 16x20
            if (d / f"{slug}_16x20.png").exists():
                slugs.append(slug)
    return slugs


def find_florence_render(slug: str, size: str) -> Path | None:
    """Find a Florence render for a city at a given size."""
    path = RENDERS_DIR / f"{slug}_florence" / f"{slug}_{size}.png"
    if path.exists():
        return path
    return None


def _find_render_florence(slug: str, theme: str = "37th_parallel",
                          size: str = "16x20") -> str | None:
    """Florence-aware render finder for image_composer functions."""
    path = RENDERS_DIR / f"{slug}_florence" / f"{slug}_{size}.png"
    if path.exists():
        return str(path)
    return None


def create_detail_crop(slug: str) -> str | None:
    """Create a detail crop matching the default theme's format."""
    import etsy.image_composer as ic

    # Monkey-patch _find_render to look in florence folder
    original_find = ic._find_render
    ic._find_render = _find_render_florence
    try:
        out_dir = str(RENDERS_DIR / f"{slug}_florence")
        result = ic.create_detail_crop(slug, output_dir=out_dir)
        return result
    finally:
        ic._find_render = original_find


def create_size_comparison(slug: str) -> str | None:
    """Create a size comparison matching the default theme's format."""
    import etsy.image_composer as ic

    original_find = ic._find_render
    ic._find_render = _find_render_florence
    try:
        out_dir = str(RENDERS_DIR / f"{slug}_florence")
        result = ic.create_size_comparison(slug, output_dir=out_dir)
        return result
    finally:
        ic._find_render = original_find


def compose_mockups(slug: str) -> list[str]:
    """Compose all 7 mockups for a Florence city."""
    from etsy.mockup_composer import ALL_MOCKUPS, get_smart_object_slots, fit_to_slot, MockupSlot

    results = []
    out_dir = RENDERS_DIR / f"{slug}_florence"

    # Load renders we need
    render_cache: dict[str, Image.Image] = {}
    for m in ALL_MOCKUPS:
        size = m.render_size
        if size not in render_cache:
            path = find_florence_render(slug, size)
            if path:
                render_cache[size] = Image.open(str(path)).convert("RGBA")

    for mockup_def in ALL_MOCKUPS:
        size = mockup_def.render_size
        if size not in render_cache:
            print(f"    SKIP {mockup_def.short_name}: no {size} render")
            continue

        city_render = render_cache[size]

        psd_path = MOCKUP_DIR / mockup_def.filename
        if not psd_path.exists():
            print(f"    SKIP {mockup_def.short_name}: PSD not found")
            continue

        psd = PSDImage.open(str(psd_path))
        base = psd.composite().convert("RGBA")

        if mockup_def.use_smart_object_bounds:
            slots = get_smart_object_slots(psd)
        else:
            slots = list(mockup_def.slots)

        if not slots:
            continue

        # Multi-slot: fill with Florence filler cities
        num_fillers = len(slots) - 1
        if num_fillers > 0:
            filler_renders = []
            for fs in FILLER_SLUGS:
                if fs == slug:
                    continue
                fp = find_florence_render(fs, mockup_def.render_size)
                if fp:
                    filler_renders.append(Image.open(str(fp)).convert("RGBA"))
                if len(filler_renders) >= num_fillers:
                    break

            filler_idx = 0
            for i, slot in enumerate(slots):
                if i == mockup_def.featured_slot:
                    fitted = fit_to_slot(city_render, slot)
                else:
                    if filler_idx < len(filler_renders):
                        fitted = fit_to_slot(filler_renders[filler_idx], slot)
                        filler_idx += 1
                    else:
                        fitted = fit_to_slot(city_render, slot)
                base.paste(fitted, (slot.left, slot.top), fitted)
        else:
            fitted = fit_to_slot(city_render, slots[0])
            base.paste(fitted, (slots[0].left, slots[0].top), fitted)

        out_path = out_dir / f"{slug}_{mockup_def.short_name}.jpg"
        base.convert("RGB").save(str(out_path), "JPEG", quality=95)
        results.append(str(out_path))

    return results


def generate_florence_listing_text(slug: str) -> str | None:
    """Generate Florence-specific listing text file."""
    from etsy.city_list import ALL_CITIES

    # Find city data from slug
    city = None
    for c in ALL_CITIES:
        if c.slug == slug or (slug == "manhattan" and c.city == "New York"):
            city = c
            break
    if not city:
        return None

    display_city = "Manhattan" if slug == "manhattan" else city.city
    display_state = "New York" if slug == "manhattan" else (city.state if city.country == "USA" else city.country)
    location_label = f"{display_city}, {display_state}"

    # SEO title — emphasize colorful/mosaic art style
    title_templates = [
        "{city} Map Print, Colorful City Block Mosaic Wall Art, Abstract Street Map Poster, Housewarming Gift",
        "{city} Colorful Map Art Print, Modern City Block Poster, Abstract Mosaic Wall Decor, New Home Gift",
        "{city} Map Wall Art, Colorful Abstract City Poster, Mosaic Street Map Print, Travel Gift",
    ]
    import hashlib
    idx = int(hashlib.md5(slug.encode()).hexdigest(), 16) % len(title_templates)
    title = title_templates[idx].format(city=display_city)
    if len(title) > 140:
        title = f"{display_city} Colorful Map Print | Abstract City Block Mosaic Wall Art"

    # Tags
    tags = [
        f"{display_city.lower()} map print",
        f"{display_city.lower()} wall art",
        f"{display_city.lower()} poster",
        f"{display_city.lower()} gift",
        "colorful map art",
        "city block mosaic",
        "abstract map print",
        "mosaic wall art",
        "city map poster",
        "modern map art",
        "housewarming gift",
        "travel wall decor",
        "colorful city poster",
    ]

    # Description
    description = f"""The perfect piece for anyone who loves {display_city}. This colorful city block mosaic transforms the streets of {location_label} into a vibrant work of abstract art.

Every city block is individually colored from a warm palette of oranges, ambers, grays, and teals — creating a unique mosaic pattern that reveals the city's street grid, parks, and waterways in stunning detail.

WHAT YOU GET
✦ Digital Download — High-resolution 300 DPI PNG file, ready to print at home or at any print shop
✦ Physical Print — Museum-quality poster printed on premium matte paper, shipped directly to you via our print partner
✦ Framed Option — Choose black or white frame in any size

AVAILABLE SIZES
✦ 8×10 inches (20×25 cm)
✦ 11×14 inches (28×36 cm)
✦ 16×20 inches (41×51 cm)
✦ 18×24 inches (46×61 cm)
✦ 24×36 inches (61×91 cm)

ABOUT THIS DESIGN
This map is created by breaking {display_city}'s street network into individual city blocks using a technique called polygonization. Each block receives a random color from our curated warm palette, creating a colorful mosaic that is unique to this city's geography. Parks and natural areas create larger organic shapes, while dense urban grids produce intricate tiny blocks.

Perfect as a housewarming gift, travel memento, or statement piece for any room. Each city's map is as unique as the city itself.

SHIPPING & DELIVERY
✦ Digital downloads are available instantly after purchase
✦ Physical prints ship within 2-5 business days via our print partner
✦ Framed prints ship within 5-7 business days
"""

    # Variations/pricing (same as default theme)
    variations = """VARIATIONS (SKU / Size / Format / Price)
GLC-FLOR-DIG-8x10   | 8x10   | Digital   | $4.20
GLC-FLOR-DIG-11x14  | 11x14  | Digital   | $5.04
GLC-FLOR-DIG-16x20  | 16x20  | Digital   | $5.88
GLC-FLOR-DIG-18x24  | 18x24  | Digital   | $6.72
GLC-FLOR-DIG-24x36  | 24x36  | Digital   | $7.80
GLC-FLOR-UNF-8x10   | 8x10   | Unframed  | $34.83
GLC-FLOR-UNF-11x14  | 11x14  | Unframed  | $39.85
GLC-FLOR-UNF-16x20  | 16x20  | Unframed  | $46.35
GLC-FLOR-UNF-18x24  | 18x24  | Unframed  | $51.37
GLC-FLOR-UNF-24x36  | 24x36  | Unframed  | $62.45
GLC-FLOR-FBK-8x10   | 8x10   | Framed BK | $78.07
GLC-FLOR-FBK-11x14  | 11x14  | Framed BK | $87.50
GLC-FLOR-FBK-16x20  | 16x20  | Framed BK | $119.62
GLC-FLOR-FBK-18x24  | 18x24  | Framed BK | $131.12
GLC-FLOR-FBK-24x36  | 24x36  | Framed BK | $216.17
GLC-FLOR-FWH-8x10   | 8x10   | Framed WH | $78.07
GLC-FLOR-FWH-11x14  | 11x14  | Framed WH | $87.50
GLC-FLOR-FWH-16x20  | 16x20  | Framed WH | $119.62
GLC-FLOR-FWH-18x24  | 18x24  | Framed WH | $131.12
GLC-FLOR-FWH-24x36  | 24x36  | Framed WH | $216.17
"""

    # Write listing text
    out_dir = RENDERS_DIR / f"{slug}_florence"
    out_path = out_dir / f"{slug}_listing.txt"

    lines = []
    lines.append("=" * 70)
    lines.append(f"ETSY LISTING — {location_label} (Florence Style)")
    lines.append("=" * 70)
    lines.append("")
    lines.append("TITLE")
    lines.append("-" * 40)
    lines.append(title)
    lines.append("")
    lines.append("TAGS")
    lines.append("-" * 40)
    lines.append(", ".join(tags))
    lines.append("")
    lines.append("DESCRIPTION")
    lines.append("-" * 40)
    lines.append(description)
    lines.append("VARIATIONS")
    lines.append("-" * 40)
    lines.append(variations)

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return str(out_path)


def generate_florence_gelato_csv(slug: str) -> str | None:
    """Generate Gelato CSV template for a Florence city."""
    from etsy.city_list import ALL_CITIES

    city = None
    for c in ALL_CITIES:
        if c.slug == slug or (slug == "manhattan" and c.city == "New York"):
            city = c
            break
    if not city:
        return None

    display_city = "Manhattan" if slug == "manhattan" else city.city

    out_dir = RENDERS_DIR / f"{slug}_florence"
    out_path = out_dir / f"{slug}_gelato.csv"

    sizes = [
        ("8x10", "8_x_10_in"),
        ("11x14", "11_x_14_in"),
        ("16x20", "16_x_20_in"),
        ("18x24", "18_x_24_in"),
        ("24x36", "24_x_36_in"),
    ]

    lines = ["title,sku,productUid,fileUrl"]
    for size_label, gelato_size in sizes:
        for fmt, prefix in [("UNF", "poster"), ("FBK", "framed_poster_black"), ("FWH", "framed_poster_white")]:
            sku = f"GLC-FLOR-{fmt}-{size_label}"
            product_uid = f"{prefix}_{gelato_size}_170gsm-uncoated-matte"
            file_url = f"[DROPBOX_URL]/{slug}_florence/{slug}_{size_label}.png"
            title_field = f"{display_city} Colorful Map - {size_label}"
            lines.append(f'"{title_field}","{sku}","{product_uid}","{file_url}"')

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return str(out_path)


def main():
    parser = argparse.ArgumentParser(description="Florence post-processing")
    parser.add_argument("--city", default=None, help="Process a single city slug")
    args = parser.parse_args()

    if args.city:
        cities = [args.city]
    else:
        cities = get_florence_cities()

    print(f"\nFlorence Post-Processing — {len(cities)} cities")
    print(f"Output: {RENDERS_DIR}/{{slug}}_florence/\n")

    for i, slug in enumerate(cities, 1):
        print(f"[{i}/{len(cities)}] {slug}")

        # Detail crop
        dc = create_detail_crop(slug)
        if dc:
            print(f"  Detail crop: OK")

        # Size comparison
        sc = create_size_comparison(slug)
        if sc:
            print(f"  Size comparison: OK")

        # Mockups
        mockups = compose_mockups(slug)
        print(f"  Mockups: {len(mockups)} generated")

        # Listing text
        lt = generate_florence_listing_text(slug)
        if lt:
            print(f"  Listing text: OK")

        # Gelato CSV
        gc = generate_florence_gelato_csv(slug)
        if gc:
            print(f"  Gelato CSV: OK")

    print(f"\nDone! {len(cities)} cities processed.")


if __name__ == "__main__":
    main()
