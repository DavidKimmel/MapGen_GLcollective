"""
Update Etsy listing images for cities that have outdated mockups.

Finds each city's listing by SKU prefix, deletes all existing images,
and uploads the current mockup set in the correct order.

Usage:
    # Dry run (shows what would happen, no API calls to modify)
    python scripts/update_listing_images.py --dry-run

    # Update a single city
    python scripts/update_listing_images.py --city seattle

    # Update all 10 cities
    python scripts/update_listing_images.py
"""

from __future__ import annotations

import argparse
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from etsy.api_client import EtsyClient, EtsyApiError

RENDERS_DIR = r"C:\MapGen_GLcollective\etsy\renders\POSTED\DefaultMap_Posted"

# Cities to update, mapped to their SKU prefix for listing lookup
CITIES: dict[str, str] = {
    "washington_dc": "GLC-WASHINGTON_DC",
    "savannah": "GLC-SAVANNAH",
    "seattle": "GLC-SEATTLE",
    "san_francisco": "GLC-SAN_FRANCISCO",
    "richmond": "GLC-RICHMOND",
    "nashville": "GLC-NASHVILLE",
    "minneapolis": "GLC-MINNEAPOLIS",
    "denver": "GLC-DENVER",
    "chicago": "GLC-CHICAGO",
    "charleston": "GLC-CHARLESTON",
}

# Image upload order (rank 1 = hero)
IMAGE_ORDER: list[str] = [
    "{slug}_main.jpg",
    "{slug}_mockup4.jpg",
    "{slug}_once.jpg",
    "{slug}_vv1.jpg",
    "{slug}_2frames.jpg",
    "{slug}_cls4.jpg",
    "{slug}_framepsd.jpg",
    "{slug}_detail_crop.jpg",
]


def find_listing_ids(client: EtsyClient, shop_id: int) -> dict[str, int]:
    """Find listing IDs for target cities by matching SKU prefixes."""
    city_to_listing: dict[str, int] = {}
    offset = 0
    limit = 100

    print("Scanning shop listings to find target cities...")
    while True:
        resp = client.get_listings_by_shop(shop_id, state="active", limit=limit, offset=offset)
        results = resp.get("results", [])
        if not results:
            break

        for listing in results:
            listing_id = listing["listing_id"]
            # Check SKUs in inventory
            try:
                inv = client.get_listing_inventory(listing_id)
                products = inv.get("products", [])
                for product in products:
                    for sku in product.get("sku", "").split(","):
                        sku = sku.strip()
                        for slug, prefix in CITIES.items():
                            if slug not in city_to_listing and sku.startswith(prefix):
                                city_to_listing[slug] = listing_id
                                print(f"  Found {slug} -> listing {listing_id}")
            except EtsyApiError:
                pass

            if len(city_to_listing) == len(CITIES):
                return city_to_listing

        offset += limit
        count = resp.get("count", 0)
        if offset >= count:
            break

    return city_to_listing


def update_city_images(
    client: EtsyClient,
    shop_id: int,
    slug: str,
    listing_id: int,
    dry_run: bool = False,
) -> bool:
    """Delete old images and upload new ones for a single city listing."""
    city_dir = os.path.join(RENDERS_DIR, slug)
    images = [os.path.join(city_dir, f.format(slug=slug)) for f in IMAGE_ORDER]

    # Verify all images exist
    missing = [img for img in images if not os.path.exists(img)]
    if missing:
        print(f"  ERROR: Missing images:")
        for m in missing:
            print(f"    {os.path.basename(m)}")
        return False

    print(f"  {len(images)} images ready for upload")

    if dry_run:
        for rank, img in enumerate(images, 1):
            print(f"    [{rank}] {os.path.basename(img)}")
        return True

    # Step 1: Get current image IDs (to delete after uploading new ones)
    old_images = client.get_listing_images(shop_id, listing_id)
    old_image_ids = [img["listing_image_id"] for img in old_images]
    print(f"  Found {len(old_image_ids)} existing images to replace")

    # Step 2: Upload new images first (Etsy requires at least 1 image at all times)
    print(f"  Uploading {len(images)} new images...")
    for rank, img_path in enumerate(images, 1):
        try:
            client.upload_listing_image(shop_id, listing_id, img_path, rank=rank)
            print(f"    [{rank}] {os.path.basename(img_path)} OK")
        except EtsyApiError as e:
            print(f"    [{rank}] {os.path.basename(img_path)} FAILED: {e}")
            return False

    # Step 3: Delete old images (now safe since new ones are uploaded)
    print(f"  Deleting {len(old_image_ids)} old images...")
    for image_id in old_image_ids:
        try:
            client.delete_listing_image(shop_id, listing_id, image_id)
        except EtsyApiError as e:
            print(f"    WARNING: Could not delete image {image_id}: {e}")

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Update Etsy listing images")
    parser.add_argument("--city", type=str, help="Update a single city (slug)")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without making changes")
    parser.add_argument("--listing-id", type=int, help="Specify listing ID directly (use with --city)")
    args = parser.parse_args()

    target_cities = {args.city: CITIES[args.city]} if args.city else CITIES

    # Verify all image files exist before touching the API
    print(f"\nVerifying image files for {len(target_cities)} cities...")
    all_ok = True
    for slug in target_cities:
        city_dir = os.path.join(RENDERS_DIR, slug)
        images = [os.path.join(city_dir, f.format(slug=slug)) for f in IMAGE_ORDER]
        missing = [img for img in images if not os.path.exists(img)]
        if missing:
            print(f"  {slug}: MISSING {len(missing)} images")
            for m in missing:
                print(f"    {os.path.basename(m)}")
            all_ok = False
        else:
            print(f"  {slug}: {len(images)} images OK")

    if not all_ok:
        print("\nAborting — fix missing images first.")
        return

    if args.dry_run:
        print("\n=== DRY RUN — no API calls will be made ===\n")
        for slug in target_cities:
            print(f"\n{slug}:")
            city_dir = os.path.join(RENDERS_DIR, slug)
            images = [os.path.join(city_dir, f.format(slug=slug)) for f in IMAGE_ORDER]
            for rank, img in enumerate(images, 1):
                print(f"  [{rank}] {os.path.basename(img)}")
        return

    client = EtsyClient()
    shop_id = client.get_shop_id()
    print(f"Shop ID: {shop_id}")

    # Find listing IDs
    if args.listing_id and args.city:
        city_listings = {args.city: args.listing_id}
    else:
        city_listings = find_listing_ids(client, shop_id)

    not_found = set(target_cities.keys()) - set(city_listings.keys())
    if not_found:
        print(f"\nWARNING: Could not find listings for: {', '.join(not_found)}")

    # Update each city
    print(f"\n{'=' * 50}")
    print(f"Updating {len(city_listings)} listings")
    print(f"{'=' * 50}")

    results: dict[str, str] = {}
    for slug, listing_id in city_listings.items():
        print(f"\n--- {slug} (listing {listing_id}) ---")
        success = update_city_images(client, shop_id, slug, listing_id, dry_run=False)
        results[slug] = "OK" if success else "FAILED"

    # Summary
    print(f"\n{'=' * 50}")
    print("Summary:")
    for slug, status in results.items():
        print(f"  {slug}: {status}")


if __name__ == "__main__":
    main()
