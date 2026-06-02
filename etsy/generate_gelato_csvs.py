"""GeoLine Collective — Gelato CSV Generator.

Creates shared links via Dropbox API for all city poster files,
then generates Gelato import CSVs for each city.

Usage:
    python -m etsy.generate_gelato_csvs --token <DROPBOX_TOKEN>
    python -m etsy.generate_gelato_csvs --token <DROPBOX_TOKEN> --city seattle
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from etsy import r2_storage
from etsy.city_list import ALL_CITIES, CityListing, get_city

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SIZES = ["8x10", "11x14", "16x20", "18x24", "24x36"]

# Gelato Product UIDs per size (mm dimensions)
SIZE_MM: dict[str, str] = {
    "8x10":  "200x250",
    "11x14": "270x350",
    "16x20": "400x500",
    "18x24": "450x600",
    "24x36": "600x900",
}

# inch-mm format used in product UIDs
SIZE_INCH_MM: dict[str, str] = {
    size: f"{size}-inch-{mm}-mm" for size, mm in SIZE_MM.items()
}

# Reversed mm-inch format used in framed UIDs
SIZE_MM_INCH: dict[str, str] = {
    size: f"{mm}-mm-{size}-inch" for size, mm in SIZE_MM.items()
}

RENDERS_DIR = Path(__file__).parent / "renders"
# Classic (37th_parallel) print files live here after the POSTED reorg.
CLASSIC_DIR = RENDERS_DIR / "POSTED" / "DefaultMap_Posted"


# ---------------------------------------------------------------------------
# R2 file URLs
# ---------------------------------------------------------------------------

def get_file_links_for_city(city: CityListing) -> dict[str, str]:
    """Return the permanent R2 URL for all 5 sizes of a city. Returns {size: url}.

    The print file's R2 key is its path relative to etsy/renders/, so the URL
    resolves once the file is seeded (scripts/r2_seed.sh)."""
    links: dict[str, str] = {}
    for size in SIZES:
        local = CLASSIC_DIR / city.slug / f"{city.slug}_{size}.png"
        if not local.exists():
            print(f"  WARN: missing render {local}")
        links[size] = r2_storage.render_url(local)
    return links


# ---------------------------------------------------------------------------
# Gelato CSV generation
# ---------------------------------------------------------------------------

def product_uid_unframed(size: str) -> str:
    return f"flat_{SIZE_INCH_MM[size]}_170-gsm-65lb-uncoated_4-0_ver"


def product_uid_framed(size: str, color: str) -> str:
    mm_inch = SIZE_MM_INCH[size]
    return (
        f"framed_poster_mounted_premium_{mm_inch}_{color}_wood_w20xt20-mm"
        f"_plexiglass_{mm_inch}_200-gsm-80lb-uncoated_4-0_ver"
    )


def sku(city: CityListing, fmt: str, size: str) -> str:
    """Generate SKU like GLC-SEATTLE-UNF-16X20."""
    fmt_codes = {"Unframed Print": "UNF", "Framed Black": "FRB", "Framed White": "FRW"}
    size_code = size.upper().replace("X", "X")
    return f"GLC-{city.slug.upper()}-{fmt_codes[fmt]}-{size_code}"


def generate_csv_for_city(
    city: CityListing,
    links: dict[str, str],
    title: str,
    listing_id: str = "",
) -> Path:
    """Generate a Gelato import CSV for a city. Returns path to CSV."""
    output_dir = RENDERS_DIR / city.slug
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "gelato_import.csv"

    headers = [
        "Product Title", "Product ID", "Variant Title",
        "Variant Option #1 Name", "Variant Option #1 Value",
        "Variant Option #2 Name", "Variant Option #2 Value",
        "Product UID", "File URL", "Production Partners", "SKU",
    ]

    rows: list[list[str]] = []
    formats = [
        ("Unframed Print", lambda s: product_uid_unframed(s)),
        ("Framed Black", lambda s: product_uid_framed(s, "black")),
        ("Framed White", lambda s: product_uid_framed(s, "white")),
    ]

    for fmt_name, uid_fn in formats:
        for size in SIZES:
            rows.append([
                title,
                listing_id,
                f"Format {fmt_name}, Size {size}",
                "Format", fmt_name,
                "Size", size,
                uid_fn(size),
                links[size],
                "Printed and shipped by our professional print partner",
                sku(city, fmt_name, size),
            ])

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(headers)
        writer.writerows(rows)

    return csv_path


# ---------------------------------------------------------------------------
# Listing title helper
# ---------------------------------------------------------------------------

def listing_title(city: CityListing) -> str:
    """Generate the Etsy listing title for a city."""
    display = city.display_city or city.city
    return (
        f"{display} Map Print - High Quality City Map Poster"
        " | Anniversary Gift | City Wall Art"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Gelato CSVs for all cities")
    parser.add_argument("--city", help="Generate for a single city (slug or name)")
    parser.add_argument("--listing-id", default="", help="Etsy listing ID (optional)")
    parser.add_argument("--title", default="", help="Override listing title (must match Etsy exactly)")
    args = parser.parse_args()

    if args.city:
        city = get_city(args.city)
        if not city:
            # Try slug match
            for c in ALL_CITIES:
                if c.slug == args.city.lower().replace(" ", "_"):
                    city = c
                    break
        if not city:
            print(f"City not found: {args.city}")
            sys.exit(1)
        cities = [city]
    else:
        cities = ALL_CITIES

    print(f"Generating Gelato CSVs for {len(cities)} cities...\n")

    for city in cities:
        print(f"[{city.city}]")
        links = get_file_links_for_city(city)
        title = args.title if args.title else listing_title(city)
        csv_path = generate_csv_for_city(city, links, title, args.listing_id)
        print(f"  -> {csv_path}\n")

    print("Done!")


if __name__ == "__main__":
    main()
