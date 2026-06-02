"""Connect Florence Etsy listings to Gelato products via API.

3-step process per variant:
  1. PATCH variant with productUid
  2. POST print-file with Dropbox URL
  3. PATCH variant with connectionStatus: "connected"

Usage:
    python scripts/gelato_connect_florence.py                  # All cities
    python scripts/gelato_connect_florence.py --city chicago
    python scripts/gelato_connect_florence.py --dry-run
"""

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

STORE_ID = "3e2b887f-ccb6-465d-9000-adfc312b0b1f"
BASE_URL = f"https://ecommerce.gelatoapis.com/v1/stores/{STORE_ID}"
RENDERS_DIR = Path("etsy/renders")

SIZES = ["8x10", "11x14", "16x20", "18x24", "24x36"]

# Same product UID functions as the CSV generator
SIZE_MM = {
    "8x10": "200x250", "11x14": "270x350", "16x20": "400x500",
    "18x24": "450x600", "24x36": "600x900",
}
SIZE_INCH_MM = {s: f"{s}-inch-{mm}-mm" for s, mm in SIZE_MM.items()}
SIZE_MM_INCH = {s: f"{mm}-mm-{s}-inch" for s, mm in SIZE_MM.items()}


def product_uid_unframed(size: str) -> str:
    return f"flat_{SIZE_INCH_MM[size]}_170-gsm-65lb-uncoated_4-0_ver"


def product_uid_framed(size: str, color: str) -> str:
    mm_inch = SIZE_MM_INCH[size]
    return (
        f"framed_poster_mounted_premium_{mm_inch}_{color}_wood_w20xt20-mm"
        f"_plexiglass_{mm_inch}_200-gsm-80lb-uncoated_4-0_ver"
    )


# Variant format -> product UID mapping
VARIANT_UID_MAP: dict[tuple[str, str], str] = {}
for _size in SIZES:
    VARIANT_UID_MAP[("Unframed Print", _size)] = product_uid_unframed(_size)
    VARIANT_UID_MAP[("Framed Print - Black", _size)] = product_uid_framed(_size, "black")
    VARIANT_UID_MAP[("Framed Print - White", _size)] = product_uid_framed(_size, "white")


def _load_api_key() -> str:
    env_path = Path(".env")
    if not env_path.exists():
        print("ERROR: .env file not found. Add GELATO_API_KEY to .env")
        sys.exit(1)
    for line in env_path.read_text().splitlines():
        if line.startswith("GELATO_API_KEY="):
            return line.split("=", 1)[1].strip()
    print("ERROR: GELATO_API_KEY not found in .env")
    sys.exit(1)


def gelato_api(api_key: str, method: str, endpoint: str,
               payload: dict | None = None) -> dict:
    url = f"{BASE_URL}/{endpoint}"
    cmd = [
        "curl", "-s", "--max-time", "120", "-X", method, url,
        "-H", f"X-API-KEY: {api_key}",
        "-H", "Content-Type: application/json",
    ]
    if payload:
        cmd += ["-d", json.dumps(payload)]

    for attempt in range(3):
        result = subprocess.run(cmd, capture_output=True, text=True)
        stdout = result.stdout.strip()
        if not stdout:
            return {}
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            if attempt < 2:
                time.sleep(3)
                continue
            raise RuntimeError(f"Invalid JSON from Gelato: {stdout[:200]}")


def get_gelato_products(api_key: str) -> list[dict]:
    return gelato_api(api_key, "GET", "products").get("products", [])


def get_florence_cities() -> list[str]:
    slugs = []
    for d in sorted(RENDERS_DIR.iterdir()):
        if d.is_dir() and d.name.endswith("_florence"):
            slug = d.name.replace("_florence", "")
            csv_path = d / f"{slug}_gelato.csv"
            if csv_path.exists():
                slugs.append(slug)
    return slugs


def load_csv_urls(slug: str) -> dict[str, str]:
    """Load file URLs from the Florence gelato CSV. Returns {variant_title: url}."""
    csv_path = RENDERS_DIR / f"{slug}_florence" / f"{slug}_gelato.csv"
    if not csv_path.exists():
        return {}
    urls = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            urls[row["Variant Title"]] = row["File URL"]
    return urls


def find_gelato_product(products: list[dict], slug: str) -> dict | None:
    """Find Gelato product matching a Florence city.

    Matches by searching for the city name or 'Colorful' in the product title.
    """
    # Get the listing title from the etsy_listing.json
    id_file = RENDERS_DIR / f"{slug}_florence" / f"{slug}_etsy_listing.json"
    if id_file.exists():
        data = json.loads(id_file.read_text(encoding="utf-8"))
        listing_id = str(data.get("listing_id", ""))
        # Match by external ID (Etsy listing ID)
        for p in products:
            if str(p.get("externalId", "")) == listing_id:
                return p

    # Fallback: match by city name in title
    city_name = slug.replace("_", " ").title()
    for p in products:
        title = p.get("title", "")
        if city_name.lower() in title.lower() and "colorful" in title.lower():
            return p

    return None


def parse_variant(title: str) -> tuple[str, str] | None:
    """Extract (format, size) from 'Format X, Size Y'."""
    try:
        parts = title.split(", ")
        fmt = parts[0].replace("Format ", "")
        size = parts[1].replace("Size ", "")
        return (fmt, size)
    except (IndexError, ValueError):
        return None


def connect_city(api_key: str, slug: str, products: list[dict],
                 dry_run: bool = False) -> bool:
    product = find_gelato_product(products, slug)
    if not product:
        print(f"  NOT FOUND in Gelato — has the listing synced?")
        return False

    product_id = product["id"]
    print(f"  Gelato product: {product_id}")
    print(f"  Etsy listing:   {product.get('externalId', '?')}")

    csv_urls = load_csv_urls(slug)
    if not csv_urls:
        print(f"  ERROR: No gelato CSV found")
        return False

    connected = 0
    skipped = 0
    errors = 0

    for v in product.get("variants", []):
        title = v.get("title", "")
        parsed = parse_variant(title)
        if not parsed:
            continue

        fmt, size = parsed

        # Skip digital variants
        if "Digital" in fmt:
            skipped += 1
            continue

        uid = VARIANT_UID_MAP.get((fmt, size))
        if not uid:
            print(f"    SKIP {title} — no UID mapping")
            skipped += 1
            continue

        # Get file URL from CSV
        variant_key = f"Format {fmt}, Size {size}"
        file_url = csv_urls.get(variant_key)
        if not file_url:
            print(f"    SKIP {title} — no file URL")
            skipped += 1
            continue

        if dry_run:
            print(f"    [DRY] {title}")
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
            # Step 3: Mark connected
            gelato_api(api_key, "PATCH",
                       f"products/{product_id}/variants/{v['id']}",
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
    parser = argparse.ArgumentParser(description="Connect Florence listings to Gelato")
    parser.add_argument("--city", default=None, help="Single city slug")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    api_key = _load_api_key()
    print("Fetching Gelato products...")
    products = get_gelato_products(api_key)
    print(f"Found {len(products)} products in store\n")

    if args.city:
        cities = [args.city]
    else:
        cities = get_florence_cities()

    ok = 0
    fail = 0
    for i, slug in enumerate(cities, 1):
        print(f"[{i}/{len(cities)}] {slug}")
        success = connect_city(api_key, slug, products, dry_run=args.dry_run)
        if success:
            ok += 1
        else:
            fail += 1
        print()

    print(f"Done! {ok} ok, {fail} failed")


if __name__ == "__main__":
    main()
