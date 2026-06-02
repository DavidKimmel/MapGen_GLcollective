"""Connect Blueprint Etsy listings to Gelato products.

Reads gelato_import.csv from each Blueprint city folder and connects
variants via the Gelato API (3-step: set productUid, upload print file, mark connected).

Usage:
    python scripts/gelato_connect_blueprint.py --dry-run
    python scripts/gelato_connect_blueprint.py
    python scripts/gelato_connect_blueprint.py --city chicago
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

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

STORE_ID = "3e2b887f-ccb6-465d-9000-adfc312b0b1f"
BASE_URL = f"https://ecommerce.gelatoapis.com/v1/stores/{STORE_ID}"
RENDERS_DIR = Path("etsy/renders")
SKIP = {"asheville", "boise", "charleston", "honolulu", "seattle", "san_francisco", "lisbon", "copenhagen"}


def load_api_key() -> str:
    env_path = Path(".env")
    if not env_path.exists():
        print("ERROR: .env not found")
        sys.exit(1)
    for line in env_path.read_text().splitlines():
        if line.startswith("GELATO_API_KEY="):
            return line.split("=", 1)[1].strip()
    print("ERROR: GELATO_API_KEY not in .env")
    sys.exit(1)


def gelato_api(api_key: str, method: str, endpoint: str, payload: dict | None = None) -> dict:
    url = f"{BASE_URL}/{endpoint}"
    cmd = ["curl", "-s", "--max-time", "120", "-X", method, url,
           "-H", f"X-API-KEY: {api_key}", "-H", "Content-Type: application/json"]
    if payload:
        cmd += ["-d", json.dumps(payload)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if not result.stdout.strip():
        return {}
    return json.loads(result.stdout)


def get_all_products(api_key: str) -> list[dict]:
    return gelato_api(api_key, "GET", "products").get("products", [])


def find_product_by_listing_id(products: list[dict], listing_id: str) -> dict | None:
    """Match Gelato product by Etsy listing ID (externalId)."""
    for p in products:
        if str(p.get("externalId", "")) == str(listing_id):
            return p
    return None


def connect_city(api_key: str, slug: str, products: list[dict], dry_run: bool = False) -> bool:
    folder = RENDERS_DIR / f"{slug}_blueprint"
    csv_path = folder / "gelato_import.csv"

    if not csv_path.exists():
        print(f"  No gelato_import.csv")
        return False

    # Read CSV
    rows = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        return False

    listing_id = rows[0]["Product ID"]
    if not listing_id:
        print(f"  No listing ID in CSV")
        return False

    # Find in Gelato by listing ID
    product = find_product_by_listing_id(products, listing_id)
    if not product:
        print(f"  NOT FOUND in Gelato (listing_id={listing_id})")
        return False

    product_id = product["id"]
    print(f"  Gelato product: {product_id} | Etsy: {listing_id}")

    # Build URL map from CSV
    url_map: dict[str, tuple[str, str]] = {}  # variant_title -> (product_uid, file_url)
    for row in rows:
        url_map[row["Variant Title"]] = (row["Product UID"], row["File URL"])

    connected = skipped = errors = 0

    for v in product.get("variants", []):
        title = v.get("title", "")

        # Skip digital
        if "Digital" in title:
            skipped += 1
            continue

        # Match variant title to CSV
        if title not in url_map:
            # Try normalizing — Gelato might use slightly different format
            # Our CSV: "Format Unframed Print, Size 8x10"
            # Gelato: "Format Unframed Print, Size 8x10" (should match)
            print(f"    SKIP {title} — not in CSV")
            skipped += 1
            continue

        uid, file_url = url_map[title]
        if not file_url:
            print(f"    SKIP {title} — no file URL")
            skipped += 1
            continue

        if dry_run:
            print(f"    [DRY] {title} -> {uid[:50]}...")
            connected += 1
            continue

        variant_id = v["id"]

        # Step 1: Set product UID
        gelato_api(api_key, "PATCH", f"products/{product_id}/variants/{variant_id}",
                   {"productUid": uid})

        # Step 2: Upload print file
        result = gelato_api(api_key, "POST",
                            f"products/{product_id}/variants/{variant_id}/print-files",
                            {"type": "default", "fileUrl": file_url})

        if "id" in result:
            # Step 3: Mark connected
            gelato_api(api_key, "PATCH", f"products/{product_id}/variants/{variant_id}",
                       {"connectionStatus": "connected"})
            print(f"    OK {title}")
            connected += 1
        else:
            msg = result.get("message", str(result))
            print(f"    ERR {title}: {msg}")
            errors += 1

        time.sleep(0.1)

    print(f"  Result: {connected} connected, {skipped} skipped, {errors} errors")
    return errors == 0


def main():
    parser = argparse.ArgumentParser(description="Connect Blueprint listings to Gelato")
    parser.add_argument("--city", help="Single city slug")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    api_key = load_api_key()
    print("Fetching Gelato products...")
    products = get_all_products(api_key)
    print(f"Found {len(products)} products\n")

    if args.city:
        slugs = [args.city.lower().replace(" ", "_")]
    else:
        slugs = []
        for d in sorted(os.listdir(RENDERS_DIR)):
            if not d.endswith("_blueprint"):
                continue
            slug = d.replace("_blueprint", "")
            if slug in SKIP:
                continue
            if (RENDERS_DIR / d / "gelato_import.csv").exists():
                slugs.append(slug)

    print(f"Connecting {len(slugs)} cities\n")

    ok = err = 0
    for i, slug in enumerate(slugs, 1):
        print(f"[{i}/{len(slugs)}] {slug}")
        success = connect_city(api_key, slug, products, dry_run=args.dry_run)
        if success:
            ok += 1
        else:
            err += 1
        print()

    print(f"Done: {ok} ok, {err} errors")


if __name__ == "__main__":
    main()
