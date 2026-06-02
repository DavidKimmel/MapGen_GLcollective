"""Generate Gelato import CSVs for Florence listings.

Creates Dropbox shared links, then generates CSVs with correct product UIDs.

Usage:
    python scripts/generate_gelato_csvs_florence.py --token TOKEN
    python scripts/generate_gelato_csvs_florence.py --token TOKEN --city chicago
    python scripts/generate_gelato_csvs_florence.py --dry-run
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from etsy import r2_storage

SIZES = ["8x10", "11x14", "16x20", "18x24", "24x36"]
# Florence print + listing files live here after the POSTED reorg.
RENDERS_DIR = Path(PROJECT_ROOT) / "etsy" / "renders" / "POSTED" / "FlorenceMap_Posted"

# Gelato mm dimensions per size
SIZE_MM: dict[str, str] = {
    "8x10": "200x250", "11x14": "270x350", "16x20": "400x500",
    "18x24": "450x600", "24x36": "600x900",
}
SIZE_INCH_MM: dict[str, str] = {s: f"{s}-inch-{mm}-mm" for s, mm in SIZE_MM.items()}
SIZE_MM_INCH: dict[str, str] = {s: f"{mm}-mm-{s}-inch" for s, mm in SIZE_MM.items()}


def get_florence_cities() -> list[str]:
    slugs = []
    for d in sorted(RENDERS_DIR.iterdir()):
        if d.is_dir() and d.name.endswith("_florence"):
            slug = d.name.replace("_florence", "")
            if (d / f"{slug}_16x20.png").exists():
                slugs.append(slug)
    return slugs


def get_file_links(slug: str) -> dict[str, str]:
    """Permanent R2 URL per size, derived from the local print-file path."""
    links = {}
    for size in SIZES:
        local = RENDERS_DIR / f"{slug}_florence" / f"{slug}_{size}.png"
        if not local.exists():
            print(f"    WARN: missing render {local}")
        links[size] = r2_storage.render_url(local)
    return links


def product_uid_unframed(size: str) -> str:
    return f"flat_{SIZE_INCH_MM[size]}_170-gsm-65lb-uncoated_4-0_ver"


def product_uid_framed(size: str, color: str) -> str:
    mm_inch = SIZE_MM_INCH[size]
    return (
        f"framed_poster_mounted_premium_{mm_inch}_{color}_wood_w20xt20-mm"
        f"_plexiglass_{mm_inch}_200-gsm-80lb-uncoated_4-0_ver"
    )


def get_listing_title(slug: str) -> str:
    """Read title from the listing text file."""
    listing_file = RENDERS_DIR / f"{slug}_florence" / f"{slug}_listing.txt"
    if listing_file.exists():
        import re
        text = listing_file.read_text(encoding="utf-8")
        match = re.search(r"TITLE\n-+\n(.+?)(?:\n\n|\nTAGS)", text, re.DOTALL)
        if match:
            return match.group(1).strip()
    return f"{slug.replace('_', ' ').title()} Colorful Map Print"


def get_listing_id(slug: str) -> str:
    """Read listing ID from saved JSON."""
    id_file = RENDERS_DIR / f"{slug}_florence" / f"{slug}_etsy_listing.json"
    if id_file.exists():
        data = json.loads(id_file.read_text(encoding="utf-8"))
        return str(data.get("listing_id", ""))
    return ""


def generate_csv(slug: str, links: dict[str, str]) -> Path:
    title = get_listing_title(slug)
    listing_id = get_listing_id(slug)

    out_dir = RENDERS_DIR / f"{slug}_florence"
    csv_path = out_dir / f"{slug}_gelato.csv"

    headers = [
        "Product Title", "Product ID", "Variant Title",
        "Variant Option #1 Name", "Variant Option #1 Value",
        "Variant Option #2 Name", "Variant Option #2 Value",
        "Product UID", "File URL", "Production Partners", "SKU",
    ]

    rows = []
    formats = [
        ("Unframed Print", "UNF", lambda s: product_uid_unframed(s)),
        ("Framed Print - Black", "FBK", lambda s: product_uid_framed(s, "black")),
        ("Framed Print - White", "FWH", lambda s: product_uid_framed(s, "white")),
    ]

    for fmt_name, fmt_code, uid_fn in formats:
        for size in SIZES:
            size_code = size.upper()
            sku = f"GLC-FLOR-{fmt_code}-{size_code}"
            rows.append([
                title,
                listing_id,
                f"Format {fmt_name}, Size {size}",
                "Format", fmt_name,
                "Size", size,
                uid_fn(size),
                links[size],
                "Printed and shipped by our professional print partner",
                sku,
            ])

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(headers)
        writer.writerows(rows)

    return csv_path


def main():
    parser = argparse.ArgumentParser(description="Generate Gelato CSVs for Florence")
    parser.add_argument("--city", default=None, help="Single city slug")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.city:
        cities = [args.city]
    else:
        cities = get_florence_cities()

    print(f"\nGelato CSV Generator (Florence) — {len(cities)} cities\n")

    for i, slug in enumerate(cities, 1):
        print(f"[{i}/{len(cities)}] {slug}")
        if args.dry_run:
            title = get_listing_title(slug)
            lid = get_listing_id(slug)
            print(f"    Title: {title[:60]}...")
            print(f"    Listing ID: {lid}")
            print(f"    Would generate 15 rows (5 sizes x 3 formats)")
            continue

        links = get_file_links(slug)
        csv_path = generate_csv(slug, links)
        print(f"    -> {csv_path}\n")

    print("Done!")


if __name__ == "__main__":
    main()
