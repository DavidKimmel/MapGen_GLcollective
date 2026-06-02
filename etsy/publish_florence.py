"""Publish Florence-style listings to Etsy via API.

Creates draft listings, uploads images, sets up 20 variants per city.
Reads listing text from pre-generated files in etsy/renders/{slug}_florence/.

Usage:
    python -m etsy.publish_florence                    # All cities (dry run)
    python -m etsy.publish_florence --live              # Actually create listings
    python -m etsy.publish_florence --city chicago --live
    python -m etsy.publish_florence --city chicago --live --activate
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from etsy.api_client import EtsyClient, EtsyApiError

# ─── SHOP CONFIG (pulled from existing live listings) ─────────────────────────

SHOP_ID = 64614087
TAXONOMY_ID = 1029
SHIPPING_PROFILE_ID = 299396504426
RETURN_POLICY_ID = 1470278944285
SHOP_SECTION_ID = 57587152  # TODO: create a Florence section if desired
READINESS_STATE_ID = 1470278628937  # 3-5 days processing

# ─── PROPERTY IDS ─────────────────────────────────────────────────────────────
# From existing listings: Format=513, Size=514
PROP_FORMAT = 513
PROP_SIZE = 514

# ─── VARIANT DEFINITIONS ─────────────────────────────────────────────────────

SIZES = ["8x10", "11x14", "16x20", "18x24", "24x36"]

# Price matrix — same as 37th_parallel listings
PRICES: dict[str, dict[str, float]] = {
    "Digital Download": {
        "8x10": 4.20, "11x14": 5.04, "16x20": 5.88, "18x24": 6.72, "24x36": 7.80,
    },
    "Unframed Print": {
        "8x10": 34.83, "11x14": 39.85, "16x20": 46.35, "18x24": 51.37, "24x36": 62.45,
    },
    "Framed Print - Black": {
        "8x10": 78.07, "11x14": 87.50, "16x20": 119.62, "18x24": 131.12, "24x36": 216.17,
    },
    "Framed Print - White": {
        "8x10": 78.07, "11x14": 87.50, "16x20": 119.62, "18x24": 131.12, "24x36": 216.17,
    },
}

SKU_FORMAT_CODES: dict[str, str] = {
    "Digital Download": "DIG",
    "Unframed Print": "UNF",
    "Framed Print - Black": "FBK",
    "Framed Print - White": "FWH",
}

RENDERS_DIR = Path("etsy/renders")

# Image upload order — rank 1 is hero image
IMAGE_ORDER = [
    "{slug}_main.jpg",
    "{slug}_mockup4.jpg",
    "{slug}_once.jpg",
    "{slug}_vv1.jpg",
    "{slug}_2frames.jpg",
    "{slug}_cls4.jpg",
    "{slug}_framepsd.jpg",
    "{slug}_detail_crop.jpg",
    "{slug}_size_comparison.png",
]


def get_florence_cities() -> list[str]:
    """Find all city slugs with Florence renders."""
    slugs = []
    for d in sorted(RENDERS_DIR.iterdir()):
        if d.is_dir() and d.name.endswith("_florence"):
            slug = d.name.replace("_florence", "")
            if (d / f"{slug}_16x20.png").exists():
                slugs.append(slug)
    return slugs


def parse_listing_text(slug: str) -> dict:
    """Parse the pre-generated listing text file."""
    listing_file = RENDERS_DIR / f"{slug}_florence" / f"{slug}_listing.txt"
    if not listing_file.exists():
        raise FileNotFoundError(f"No listing text: {listing_file}")

    text = listing_file.read_text(encoding="utf-8")

    # Extract title
    title_match = re.search(r"TITLE\n-+\n(.+?)(?:\n\n|\nTAGS)", text, re.DOTALL)
    title = title_match.group(1).strip() if title_match else f"{slug} Colorful Map Print"

    # Extract tags
    tags_match = re.search(r"TAGS\n-+\n(.+?)(?:\n\n|\nDESCRIPTION)", text, re.DOTALL)
    tags = []
    if tags_match:
        raw_tags = [t.strip() for t in tags_match.group(1).strip().split(",")]
        # Etsy max 20 chars per tag, max 13 tags
        tags = [t for t in raw_tags if len(t) <= 20][:13]

    # Extract description
    desc_match = re.search(r"DESCRIPTION\n-+\n(.+?)(?:\nVARIATIONS)", text, re.DOTALL)
    description = desc_match.group(1).strip() if desc_match else ""

    return {"title": title, "tags": tags, "description": description}


def build_products(slug: str) -> list[dict]:
    """Build the 20-variant products array for updateListingInventory."""
    city_code = slug.upper().replace("_", "")
    products = []

    for fmt_name, fmt_code in SKU_FORMAT_CODES.items():
        for size in SIZES:
            size_code = size.upper().replace("X", "X")
            sku = f"GLC-FLOR-{fmt_code}-{size_code}"

            price = PRICES[fmt_name][size]

            product = {
                "sku": sku,
                "property_values": [
                    {
                        "property_id": PROP_FORMAT,
                        "property_name": "Format",
                        "scale_id": None,
                        "value_ids": [],
                        "values": [fmt_name],
                    },
                    {
                        "property_id": PROP_SIZE,
                        "property_name": "Size",
                        "scale_id": None,
                        "value_ids": [],
                        "values": [size],
                    },
                ],
                "offerings": [
                    {
                        "price": price,
                        "quantity": 999,
                        "is_enabled": True,
                        "readiness_state_id": READINESS_STATE_ID,
                    }
                ],
            }
            products.append(product)

    return products


def publish_city(client: EtsyClient, slug: str, live: bool = False,
                 activate: bool = False) -> dict | None:
    """Publish a single Florence city listing.

    Steps:
      1. Create draft listing
      2. Upload images (up to 9)
      3. Set up 20 variants via updateListingInventory
      4. Optionally activate

    Returns listing data or None on failure.
    """
    city_dir = RENDERS_DIR / f"{slug}_florence"
    if not city_dir.exists():
        print(f"  SKIP: no render dir {city_dir}")
        return None

    # Parse listing text
    listing_data = parse_listing_text(slug)
    title = listing_data["title"]
    tags = listing_data["tags"]
    description = listing_data["description"]

    print(f"  Title: {title[:80]}...")
    print(f"  Tags: {len(tags)}")
    print(f"  Description: {len(description)} chars")

    if not live:
        print("  [DRY RUN] Would create draft listing")
        products = build_products(slug)
        print(f"  [DRY RUN] Would set up {len(products)} variants")
        images = [city_dir / f.format(slug=slug) for f in IMAGE_ORDER]
        images = [img for img in images if img.exists()]
        print(f"  [DRY RUN] Would upload {len(images)} images")
        return None

    # 1. Create draft listing
    print("  Creating draft listing...")
    base_price = PRICES["Digital Download"]["8x10"]  # Lowest price as base
    listing = client.create_draft_listing(
        shop_id=SHOP_ID,
        title=title,
        description=description,
        price=base_price,
        quantity=999,
        tags=tags,
        who_made="i_did",
        when_made="made_to_order",
        taxonomy_id=TAXONOMY_ID,
        listing_type="physical",
        shipping_profile_id=SHIPPING_PROFILE_ID,
        return_policy_id=RETURN_POLICY_ID,
        shop_section_id=SHOP_SECTION_ID,
        is_supply=False,
        should_auto_renew=True,
        is_taxable=True,
        readiness_state_id=READINESS_STATE_ID,
    )
    listing_id = listing["listing_id"]
    print(f"  Draft created: listing_id={listing_id}")

    # 2. Upload images
    images = []
    for fname_template in IMAGE_ORDER:
        fname = fname_template.format(slug=slug)
        img_path = city_dir / fname
        if img_path.exists():
            images.append(img_path)

    print(f"  Uploading {len(images)} images...")
    for rank, img_path in enumerate(images, 1):
        try:
            alt = f"{slug.replace('_', ' ').title()} colorful map art print"
            client.upload_listing_image(
                shop_id=SHOP_ID,
                listing_id=listing_id,
                image_path=str(img_path),
                rank=rank,
                alt_text=alt,
            )
            print(f"    [{rank}] {img_path.name}")
        except EtsyApiError as e:
            print(f"    [{rank}] FAILED: {e}")

    # 3. Set up variants
    print("  Setting up 20 variants...")
    products = build_products(slug)
    try:
        client.update_listing_inventory(
            listing_id=listing_id,
            products=products,
            price_on_property=[PROP_FORMAT, PROP_SIZE],
            quantity_on_property=[],
            sku_on_property=[PROP_FORMAT, PROP_SIZE],
        )
        print(f"  Variants set: {len(products)} products")
    except EtsyApiError as e:
        print(f"  Variant setup FAILED: {e}")

    # 4. Optionally activate
    if activate:
        try:
            client.activate_listing(SHOP_ID, listing_id)
            print(f"  ACTIVATED: listing_id={listing_id}")
        except EtsyApiError as e:
            print(f"  Activation FAILED: {e}")

    # Save listing ID for reference
    id_file = city_dir / f"{slug}_etsy_listing.json"
    id_file.write_text(json.dumps({
        "listing_id": listing_id,
        "title": title,
        "slug": slug,
        "theme": "florence",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
    }, indent=2), encoding="utf-8")

    return listing


def main():
    parser = argparse.ArgumentParser(description="Publish Florence listings to Etsy")
    parser.add_argument("--city", default=None, help="Publish a single city slug")
    parser.add_argument("--live", action="store_true",
                        help="Actually create listings (default is dry run)")
    parser.add_argument("--activate", action="store_true",
                        help="Activate listings after creation")
    args = parser.parse_args()

    if args.city:
        cities = [args.city]
    else:
        cities = get_florence_cities()

    mode = "LIVE" if args.live else "DRY RUN"
    print(f"\nFlorence Etsy Publisher — {len(cities)} cities [{mode}]")
    print(f"Shop: {SHOP_ID} | Taxonomy: {TAXONOMY_ID}")
    print(f"Shipping: {SHIPPING_PROFILE_ID} | Return: {RETURN_POLICY_ID}\n")

    if args.live:
        client = EtsyClient()
        # Verify auth
        me = client.get_me()
        print(f"Authenticated as user_id={me['user_id']}\n")
    else:
        client = None

    ok_count = 0
    fail_count = 0

    for i, slug in enumerate(cities, 1):
        print(f"[{i}/{len(cities)}] {slug}")
        try:
            result = publish_city(client, slug, live=args.live, activate=args.activate)
            if args.live and result:
                ok_count += 1
            elif not args.live:
                ok_count += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            fail_count += 1
        print()

    print(f"Done! {ok_count} ok, {fail_count} failed")


if __name__ == "__main__":
    main()
