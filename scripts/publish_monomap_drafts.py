"""GeoLine Collective — MonoMap Batch Draft Publisher.

Creates draft Etsy listings for all 64 MonoMap cities with:
  - 10 mockup images per listing (Etsy max)
  - Rotating hero image (main, mockup4, frame8) across listings
  - Listing text from {city}_listing.txt files
  - Inventory variants (20 SKUs: digital + unframed + framed B/W)

Usage:
    python scripts/publish_monomap_drafts.py --dry-run          # Preview without API calls
    python scripts/publish_monomap_drafts.py                    # Push all 64 as drafts
    python scripts/publish_monomap_drafts.py --city austin      # Single city
    python scripts/publish_monomap_drafts.py --start-from denver  # Resume from a city
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from etsy.api_client import EtsyClient, EtsyApiError
from etsy.style_config import (
    SHOP_ID, SHIPPING_PROFILE_ID, RETURN_POLICY_ID,
    READINESS_STATE_ID, TAXONOMY_ID, SECTION_CITY_MAPS, MONOMAP,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RENDERS_DIR = Path(__file__).parent.parent / "etsy" / "renders"
PUBLISH_LOG = Path(__file__).parent.parent / "etsy" / "monomap_publish_log.csv"

# Hero images rotate: listing index % 3 determines which leads
HERO_OPTIONS = ["main", "mockup4", "frame8"]

# Fixed images in every listing (slots after hero trio)
# Order: single, 3-frame, single, 2-frame, 6-color, single, single
FIXED_IMAGES = [
    "frame9",           # single
    "cls4",             # 3-frame
    "frame30",          # single
    "framepsd",         # 2-frame
    "6color_labeled",   # 6-color showcase
    "frame40",          # single
    "frame44",          # single
]

# ---------------------------------------------------------------------------
# Discover monomap city folders
# ---------------------------------------------------------------------------


def discover_monomap_cities() -> list[str]:
    """Find all *_monomap folders and return sorted list of slugs."""
    slugs: list[str] = []
    for d in sorted(RENDERS_DIR.iterdir()):
        if d.is_dir() and d.name.endswith("_monomap"):
            slug = d.name.replace("_monomap", "")
            listing_txt = d / f"{slug}_listing.txt"
            if listing_txt.exists():
                slugs.append(slug)
            else:
                print(f"  WARN: {d.name} missing listing.txt — skipping")
    return slugs


# ---------------------------------------------------------------------------
# Parse listing text
# ---------------------------------------------------------------------------


def parse_listing_txt(slug: str) -> dict[str, str | list[str]]:
    """Parse a {slug}_listing.txt into title, description, tags."""
    path = RENDERS_DIR / f"{slug}_monomap" / f"{slug}_listing.txt"
    text = path.read_text(encoding="utf-8")

    # Extract title
    title_match = re.search(r"TITLE\n[—]+\n(.+)", text)
    title = title_match.group(1).strip() if title_match else f"{slug} MonoMap Print"

    # Extract tags
    tags_match = re.search(r"TAGS\n[—]+\n(.+)", text)
    tags_str = tags_match.group(1).strip() if tags_match else ""
    tags = [t.strip() for t in tags_str.split(",") if t.strip()][:13]

    # Description = everything before the TITLE section
    desc_end = text.find("\n———————————————————————\nTITLE")
    description = text[:desc_end].strip() if desc_end > 0 else text[:2000]

    return {"title": title, "description": description, "tags": tags}


# ---------------------------------------------------------------------------
# Build image list with hero rotation
# ---------------------------------------------------------------------------


def build_image_list(slug: str, city_index: int) -> list[str]:
    """Build the ordered list of 10 images for a listing.

    Hero rotates based on city_index % 3:
      0 -> main leads,   remaining: mockup4, frame8
      1 -> mockup4 leads, remaining: main, frame8
      2 -> frame8 leads,  remaining: main, mockup4
    """
    city_dir = RENDERS_DIR / f"{slug}_monomap"
    hero_idx = city_index % 3
    hero = HERO_OPTIONS[hero_idx]
    others = [h for i, h in enumerate(HERO_OPTIONS) if i != hero_idx]

    # Build ordered list: hero, single, 3-frame, other hero, 2-frame, 6-color, singles, other hero
    # Interleave single/multi so it's not uniform
    ordered_names = [
        hero,               # 1: hero
        "frame9",           # 2: single
        "cls4",             # 3: 3-frame
        others[0],          # 4: single (hero option)
        "frame30",          # 5: single
        "framepsd",         # 6: 2-frame
        "6color_labeled",   # 7: 6-color showcase
        "frame40",          # 8: single
        "frame44",          # 9: single
        others[1],          # 10: single (hero option)
    ]

    images: list[str] = []
    for name in ordered_names:
        img_path = city_dir / f"{slug}_{name}.jpg"
        if img_path.exists():
            images.append(str(img_path))
        else:
            print(f"    WARN: missing {img_path.name}")

    return images[:10]


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _log_result(result: dict) -> None:
    """Append result to CSV log."""
    file_exists = PUBLISH_LOG.exists()
    fieldnames = [
        "timestamp", "city", "status", "listing_id",
        "title", "hero", "images", "error",
    ]
    with open(PUBLISH_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            **{k: result.get(k, "") for k in fieldnames if k != "timestamp"},
        })


# ---------------------------------------------------------------------------
# Publish one city
# ---------------------------------------------------------------------------


def publish_monomap(
    client: EtsyClient,
    shop_id: int,
    slug: str,
    city_index: int,
    dry_run: bool = False,
) -> dict:
    """Create a draft MonoMap listing with 10 images."""
    result: dict = {
        "city": slug,
        "status": "pending",
        "listing_id": "",
        "title": "",
        "hero": HERO_OPTIONS[city_index % 3],
        "images": 0,
        "error": "",
    }

    print(f"\n{'=' * 55}")
    print(f"  [{city_index + 1}] {slug} (hero: {result['hero']})")
    print(f"{'=' * 55}")

    # Parse listing text
    listing = parse_listing_txt(slug)
    result["title"] = listing["title"]
    print(f"  Title: {listing['title']}")
    print(f"  Tags:  {len(listing['tags'])}")

    # Build image list
    images = build_image_list(slug, city_index)
    result["images"] = len(images)
    print(f"  Images: {len(images)}")
    for i, img in enumerate(images, 1):
        print(f"    [{i}] {os.path.basename(img)}")

    if dry_run:
        result["status"] = "dry_run"
        _log_result(result)
        return result

    # Create draft listing
    try:
        created = client.create_draft_listing(
            shop_id=shop_id,
            title=listing["title"],
            description=listing["description"],
            price=4.20,  # Base price (digital 8x10)
            quantity=999,
            tags=listing["tags"],
            who_made="i_did",
            when_made="made_to_order",
            taxonomy_id=TAXONOMY_ID,
            listing_type="physical",
            shipping_profile_id=SHIPPING_PROFILE_ID,
            return_policy_id=RETURN_POLICY_ID,
            shop_section_id=SECTION_CITY_MAPS,
            readiness_state_id=READINESS_STATE_ID,
        )
        listing_id = created.get("listing_id")
        result["listing_id"] = str(listing_id)
        print(f"  Draft created: {listing_id}")

        # Upload images
        for rank, img_path in enumerate(images, 1):
            try:
                client.upload_listing_image(shop_id, listing_id, img_path, rank=rank)
                print(f"    Uploaded [{rank}]: {os.path.basename(img_path)}")
            except EtsyApiError as e:
                print(f"    [!] Image upload failed [{rank}]: {e}")

        result["status"] = "draft_created"
        print(f"  SUCCESS — https://www.etsy.com/your/shops/me/tools/listings/{listing_id}")

    except EtsyApiError as e:
        result["status"] = "api_error"
        result["error"] = str(e)
        print(f"  ERROR: {e}")

    _log_result(result)
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish MonoMap drafts to Etsy")
    parser.add_argument("--dry-run", action="store_true", help="Preview without API calls")
    parser.add_argument("--city", help="Single city slug (e.g., austin)")
    parser.add_argument("--start-from", help="Resume from this city slug")
    args = parser.parse_args()

    all_slugs = discover_monomap_cities()
    print(f"Found {len(all_slugs)} MonoMap cities\n")

    if args.city:
        if args.city not in all_slugs:
            print(f"City not found: {args.city}")
            print(f"Available: {', '.join(all_slugs[:10])}...")
            sys.exit(1)
        slugs = [args.city]
        # Preserve the city's index for consistent hero rotation
        start_idx = all_slugs.index(args.city)
    elif args.start_from:
        if args.start_from not in all_slugs:
            print(f"City not found: {args.start_from}")
            sys.exit(1)
        start_idx = all_slugs.index(args.start_from)
        slugs = all_slugs[start_idx:]
    else:
        slugs = all_slugs
        start_idx = 0

    mode = "DRY RUN" if args.dry_run else "LIVE"
    print(f"{'#' * 60}")
    print(f"  MonoMap Batch Publisher — {mode}")
    print(f"  Cities: {len(slugs)}")
    print(f"{'#' * 60}")

    client: EtsyClient | None = None
    shop_id = SHOP_ID

    if not args.dry_run:
        client = EtsyClient()
        # Verify auth
        try:
            me = client.get_me()
            print(f"  Authenticated as: {me.get('login_name', 'unknown')}")
        except EtsyApiError as e:
            print(f"  AUTH ERROR: {e}")
            print("  Run: python -m etsy.auth")
            sys.exit(1)

    t0 = time.time()
    results: list[dict] = []

    for i, slug in enumerate(slugs):
        city_index = start_idx + i if args.start_from or not args.city else all_slugs.index(slug)
        result = publish_monomap(
            client=client,  # type: ignore[arg-type]
            shop_id=shop_id,
            slug=slug,
            city_index=city_index,
            dry_run=args.dry_run,
        )
        results.append(result)

    elapsed = time.time() - t0
    ok = sum(1 for r in results if r["status"] in ("draft_created", "dry_run"))
    errors = sum(1 for r in results if r["status"] == "api_error")

    print(f"\n{'#' * 60}")
    print(f"  Complete in {elapsed:.0f}s")
    print(f"  Success: {ok}  Errors: {errors}")
    if PUBLISH_LOG.exists():
        print(f"  Log: {PUBLISH_LOG}")
    print(f"{'#' * 60}")


if __name__ == "__main__":
    main()
