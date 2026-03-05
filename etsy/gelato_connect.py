"""GeoLine Collective — Gelato API Product Connector.

Connects Etsy listing variants to Gelato products via API:
1. Matches each variant to the correct Gelato product UID
2. Uploads the print artwork file from Dropbox

Replaces the manual CSV upload workflow.

Usage:
    python -m etsy.gelato_connect --city seattle
    python -m etsy.gelato_connect --city seattle --dry-run
    python -m etsy.gelato_connect --all
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from etsy.city_list import ALL_CITIES, CityListing, get_city
from etsy.generate_gelato_csvs import (
    SIZES,
    product_uid_framed,
    product_uid_unframed,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

STORE_ID = "3e2b887f-ccb6-465d-9000-adfc312b0b1f"
BASE_URL = f"https://ecommerce.gelatoapis.com/v1/stores/{STORE_ID}"
RENDERS_DIR = Path(__file__).parent / "renders"


def _load_api_key() -> str:
    """Load Gelato API key from .env file."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        print("ERROR: .env file not found. Add GELATO_API_KEY to .env")
        sys.exit(1)
    for line in env_path.read_text().splitlines():
        if line.startswith("GELATO_API_KEY="):
            return line.split("=", 1)[1].strip()
    print("ERROR: GELATO_API_KEY not found in .env")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Gelato API
# ---------------------------------------------------------------------------

def gelato_api(api_key: str, method: str, endpoint: str,
               payload: dict | None = None) -> dict:
    """Call Gelato ecommerce API via curl."""
    url = f"{BASE_URL}/{endpoint}"
    cmd = [
        "curl", "-s", "-X", method, url,
        "-H", f"X-API-KEY: {api_key}",
        "-H", "Content-Type: application/json",
    ]
    if payload:
        cmd += ["-d", json.dumps(payload)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if not result.stdout.strip():
        return {}
    return json.loads(result.stdout)


def get_gelato_products(api_key: str) -> list[dict]:
    """Get all products from the Gelato store."""
    return gelato_api(api_key, "GET", "products").get("products", [])


def find_gelato_product(products: list[dict], city: CityListing) -> dict | None:
    """Find the Gelato product matching a city by searching title or external ID."""
    city_name = city.display_city or city.city
    for p in products:
        title = p.get("title", "")
        if city_name.lower() in title.lower():
            return p
    return None


# ---------------------------------------------------------------------------
# Variant matching
# ---------------------------------------------------------------------------

# Map variant title patterns to product UIDs
VARIANT_UID_MAP: dict[tuple[str, str], str] = {}
for size in SIZES:
    VARIANT_UID_MAP[("Unframed Print", size)] = product_uid_unframed(size)
    VARIANT_UID_MAP[("Framed Black", size)] = product_uid_framed(size, "black")
    VARIANT_UID_MAP[("Framed White", size)] = product_uid_framed(size, "white")


def parse_variant_title(title: str) -> tuple[str, str] | None:
    """Extract (format, size) from variant title like 'Format Framed Black, Size 16x20'."""
    try:
        parts = title.split(", ")
        fmt = parts[0].replace("Format ", "")
        size = parts[1].replace("Size ", "")
        return (fmt, size)
    except (IndexError, ValueError):
        return None


def get_file_url_for_variant(city: CityListing, size: str,
                             csv_urls: dict[str, str] | None) -> str | None:
    """Get the Dropbox file URL for a city+size from the CSV URL map."""
    if not csv_urls:
        return None
    # Try all format variants — they all use the same file
    for fmt in ["Unframed Print", "Framed Black", "Framed White"]:
        key = f"Format {fmt}, Size {size}"
        if key in csv_urls:
            return csv_urls[key]
    return None


def load_csv_urls(city: CityListing) -> dict[str, str]:
    """Load file URLs from the city's gelato_import.csv."""
    csv_path = RENDERS_DIR / city.slug / "gelato_import.csv"
    if not csv_path.exists():
        return {}
    urls: dict[str, str] = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            urls[row["Variant Title"]] = row["File URL"]
    return urls


# ---------------------------------------------------------------------------
# Connect workflow
# ---------------------------------------------------------------------------

def connect_city(api_key: str, city: CityListing, products: list[dict],
                 dry_run: bool = False) -> bool:
    """Connect all variants for a city to Gelato products and upload print files."""
    product = find_gelato_product(products, city)
    if not product:
        print(f"  NOT FOUND in Gelato — has the listing been synced?")
        return False

    product_id = product["id"]
    ext_id = product["externalId"]
    print(f"  Gelato product: {product_id}")
    print(f"  Etsy listing:   {ext_id}")

    # Load Dropbox URLs from CSV
    csv_urls = load_csv_urls(city)
    if not csv_urls:
        print(f"  ERROR: No gelato_import.csv found for {city.slug}")
        print(f"  Run: python -m etsy.generate_gelato_csvs --city {city.slug}")
        return False

    connected = 0
    skipped = 0
    errors = 0

    for v in product["variants"]:
        title = v["title"]
        parsed = parse_variant_title(title)
        if not parsed:
            continue

        fmt, size = parsed

        # Skip digital variants
        if "Digital" in fmt:
            continue

        uid = VARIANT_UID_MAP.get((fmt, size))
        if not uid:
            print(f"    SKIP {title} — no UID mapping")
            skipped += 1
            continue

        file_url = get_file_url_for_variant(city, size, csv_urls)
        if not file_url:
            print(f"    SKIP {title} — no file URL in CSV")
            skipped += 1
            continue

        if dry_run:
            print(f"    [DRY RUN] {title} -> {uid[:40]}...")
            connected += 1
            continue

        # Step 1: Set product UID
        gelato_api(api_key, "PATCH",
                   f"products/{product_id}/variants/{v['id']}",
                   {"productUid": uid})

        # Step 2: Upload print file
        result = gelato_api(api_key, "POST",
                            f"products/{product_id}/variants/{v['id']}/print-files",
                            {"type": "default", "fileUrl": file_url})

        if "id" in result:
            size_mb = result.get("fileSize", 0) / 1e6

            # Step 3: Mark variant as connected
            gelato_api(api_key, "PATCH",
                       f"products/{product_id}/variants/{v['id']}",
                       {"connectionStatus": "connected"})

            print(f"    OK {title:45s} ({size_mb:.1f} MB)")
            connected += 1
        else:
            msg = result.get("message", str(result))
            print(f"    ERR {title}: {msg}")
            errors += 1

        time.sleep(0.1)  # Light rate limiting

    print(f"  Result: {connected} connected, {skipped} skipped, {errors} errors")
    return errors == 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Connect Etsy listings to Gelato products via API")
    parser.add_argument("--city", help="City name or slug")
    parser.add_argument("--all", action="store_true",
                        help="Connect all cities that have CSVs")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without making changes")
    args = parser.parse_args()

    if not args.city and not args.all:
        parser.print_help()
        sys.exit(1)

    api_key = _load_api_key()
    print("Fetching Gelato products...")
    products = get_gelato_products(api_key)
    print(f"Found {len(products)} products in store\n")

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
        # Only cities that have a CSV
        cities = [c for c in ALL_CITIES
                  if (RENDERS_DIR / c.slug / "gelato_import.csv").exists()]

    for city in cities:
        print(f"[{city.city}]")
        connect_city(api_key, city, products, dry_run=args.dry_run)
        print()

    print("Done!")


if __name__ == "__main__":
    main()
