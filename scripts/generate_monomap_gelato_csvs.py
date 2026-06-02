"""GeoLine Collective — MonoMap Gelato CSV Generator.

Generates Gelato import CSVs for all MonoMap listings using a placeholder
image URL. These are variant listings (color chosen at checkout), so all
physical variants point to the same placeholder file.

After Etsy drafts are synced to Gelato, run gelato_connect to push these CSVs.

Usage:
    python scripts/generate_monomap_gelato_csvs.py                # All cities
    python scripts/generate_monomap_gelato_csvs.py --city austin  # Single city
    python scripts/generate_monomap_gelato_csvs.py --dry-run      # Preview
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from etsy.style_config import GELATO_UIDS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RENDERS_DIR = Path(__file__).parent.parent / "etsy" / "renders"

# Placeholder image for variant listings — actual art uploaded per-order
PLACEHOLDER_URL = "https://geoline.neodigitalventures.com/_assets/placeholder.png"

SIZES = ["8x10", "11x14", "16x20", "18x24", "24x36"]

FORMATS: list[tuple[str, str]] = [
    ("Unframed Print", "unframed"),
    ("Framed - Black", "framed_black"),
    ("Framed - White", "framed_white"),
]

SKU_FMT_CODES: dict[str, str] = {
    "Unframed Print": "UNF",
    "Framed - Black": "FBK",
    "Framed - White": "FWH",
}

PUBLISH_LOG = RENDERS_DIR / "_monomap_publish_log.csv"


# ---------------------------------------------------------------------------
# Discover cities + read listing IDs from publish log
# ---------------------------------------------------------------------------


def discover_monomap_cities() -> list[str]:
    """Find all *_monomap folders with listing.txt."""
    slugs: list[str] = []
    for d in sorted(RENDERS_DIR.iterdir()):
        if d.is_dir() and d.name.endswith("_monomap"):
            slug = d.name.replace("_monomap", "")
            if (d / f"{slug}_listing.txt").exists():
                slugs.append(slug)
    return slugs


def load_listing_ids() -> dict[str, str]:
    """Load {slug: listing_id} from the monomap publish log."""
    log_path = Path(__file__).parent.parent / "etsy" / "monomap_publish_log.csv"
    ids: dict[str, str] = {}
    if not log_path.exists():
        return ids
    with open(log_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("listing_id") and row.get("status") == "draft_created":
                ids[row["city"]] = row["listing_id"]
    return ids


def parse_title_from_listing(slug: str) -> str:
    """Extract the Etsy title from the listing.txt file."""
    path = RENDERS_DIR / f"{slug}_monomap" / f"{slug}_listing.txt"
    text = path.read_text(encoding="utf-8")
    match = re.search(r"TITLE\n[—]+\n(.+)", text)
    return match.group(1).strip() if match else f"{slug} MonoMap Print"


# ---------------------------------------------------------------------------
# CSV generation
# ---------------------------------------------------------------------------


def generate_csv(slug: str, listing_id: str = "", dry_run: bool = False) -> Path:
    """Generate gelato_import.csv for a MonoMap city."""
    title = parse_title_from_listing(slug)
    output_dir = RENDERS_DIR / f"{slug}_monomap"
    csv_path = output_dir / "gelato_import.csv"

    headers = [
        "Product Title", "Product ID", "Variant Title",
        "Variant Option #1 Name", "Variant Option #1 Value",
        "Variant Option #2 Name", "Variant Option #2 Value",
        "Product UID", "File URL", "Production Partners", "SKU",
    ]

    rows: list[list[str]] = []
    for fmt_name, gelato_key in FORMATS:
        for size in SIZES:
            uid = GELATO_UIDS[gelato_key][size]
            sku_code = SKU_FMT_CODES[fmt_name]
            size_code = size.upper().replace("X", "X")
            sku = f"GLC-MONO-{sku_code}-{size_code}"

            rows.append([
                title,
                listing_id,
                f"Format {fmt_name}, Size {size}",
                "Format", fmt_name,
                "Size", size,
                uid,
                PLACEHOLDER_URL,
                "Printed and shipped by our professional print partner",
                sku,
            ])

    if dry_run:
        print(f"  {slug}: {len(rows)} variants -> {csv_path.name}")
        print(f"    Title: {title}")
        print(f"    Listing ID: {listing_id or '(not yet created)'}")
        return csv_path

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"  {slug}: {len(rows)} variants -> {csv_path}")
    return csv_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate MonoMap Gelato CSVs")
    parser.add_argument("--city", help="Single city slug")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    all_slugs = discover_monomap_cities()
    listing_ids = load_listing_ids()

    if args.city:
        if args.city not in all_slugs:
            print(f"City not found: {args.city}")
            sys.exit(1)
        slugs = [args.city]
    else:
        slugs = all_slugs

    print(f"Generating Gelato CSVs for {len(slugs)} MonoMap cities")
    print(f"  Placeholder URL: {PLACEHOLDER_URL[:60]}...")
    print(f"  Listing IDs loaded: {len(listing_ids)}\n")

    for slug in slugs:
        lid = listing_ids.get(slug, "")
        generate_csv(slug, listing_id=lid, dry_run=args.dry_run)

    print(f"\nDone! Generated {len(slugs)} CSVs.")
    if not listing_ids:
        print("  NOTE: No listing IDs found yet. Run publish_monomap_drafts.py first,")
        print("  then re-run this to embed listing IDs in the CSVs.")


if __name__ == "__main__":
    main()
