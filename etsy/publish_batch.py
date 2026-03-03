"""GeoLine Collective — Batch Listing Publisher.

End-to-end orchestrator that:
  1. Generates listing content (titles, descriptions, tags)
  2. Verifies poster renders exist (or triggers rendering)
  3. Generates automated listing images (detail crop, size comparison)
  4. Creates draft listings via Etsy API
  5. Uploads all images
  6. Logs results to publish_log.csv

Usage:
    python -m etsy.publish_batch --tier 1                # Publish Tier 1 as drafts
    python -m etsy.publish_batch --city Chicago           # Single city
    python -m etsy.publish_batch --tier 1 --dry-run       # Preview without API calls
    python -m etsy.publish_batch --tier 1 --render-only   # Just render, no API
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from etsy.city_list import ALL_CITIES, CityListing, get_cities_by_tier, get_city
from etsy.listing_generator import generate_listing
from etsy.batch_etsy_render import render_etsy_city, RENDERS_DIR
from etsy.image_composer import generate_all_images

PUBLISH_LOG = os.path.join(os.path.dirname(__file__), "publish_log.csv")


def _log_result(result: dict) -> None:
    """Append a result row to the publish log CSV."""
    file_exists = os.path.exists(PUBLISH_LOG)
    fieldnames = [
        "timestamp", "city", "tier", "status", "listing_id",
        "title", "render_path", "images_generated", "error",
    ]
    with open(PUBLISH_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            **{k: result.get(k, "") for k in fieldnames if k != "timestamp"},
        })


def _check_render(city: CityListing) -> str | None:
    """Check if a render exists for this city. Returns path or None."""
    path = os.path.join(RENDERS_DIR, city.slug, f"{city.slug}_16x20.png")
    return path if os.path.exists(path) else None


def _collect_images(city: CityListing) -> list[str]:
    """Collect all available listing images for a city, ordered by rank."""
    slug = city.slug
    city_dir = os.path.join(RENDERS_DIR, slug)
    images: list[str] = []

    # 1. Hero image = the main rendered poster
    hero = os.path.join(city_dir, f"{slug}_16x20.png")
    if os.path.exists(hero):
        images.append(hero)

    # 2. Detail crop
    detail = os.path.join(city_dir, f"{slug}_detail_crop.png")
    if os.path.exists(detail):
        images.append(detail)

    # 3. Size comparison
    sizes = os.path.join(city_dir, f"{slug}_size_comparison.png")
    if os.path.exists(sizes):
        images.append(sizes)

    # 4. Style grid (if multiple styles rendered)
    grid = os.path.join(city_dir, f"{slug}_style_grid.png")
    if os.path.exists(grid):
        images.append(grid)

    # 5. Any manually added mockup images (mockup_*.png)
    for f in sorted(Path(city_dir).glob("mockup_*.png")):
        images.append(str(f))

    return images


def publish_city(
    city: CityListing,
    dry_run: bool = False,
    render_only: bool = False,
) -> dict:
    """Publish a single city listing end-to-end.

    Returns a result dict for logging.
    """
    result: dict = {
        "city": city.city,
        "tier": city.tier,
        "status": "pending",
        "listing_id": "",
        "title": "",
        "render_path": "",
        "images_generated": 0,
        "error": "",
    }

    print(f"\n{'=' * 50}")
    print(f"Publishing: {city.city}, {city.state} (Tier {city.tier})")
    print(f"{'=' * 50}")

    # Step 1: Check/create render
    render_path = _check_render(city)
    if not render_path:
        print(f"  [1/5] Rendering poster...")
        render_result = render_etsy_city(city)
        if render_result["status"] == "ok":
            render_path = render_result["path"]
            print(f"    OK: {render_path}")
        else:
            result["status"] = "render_error"
            result["error"] = render_result.get("error", "Unknown render error")
            print(f"    ERROR: {result['error']}")
            _log_result(result)
            return result
    else:
        print(f"  [1/5] Render exists: {render_path}")

    result["render_path"] = render_path

    # Step 2: Generate listing content
    print(f"  [2/5] Generating listing content...")
    listing_data = generate_listing(city)
    result["title"] = listing_data["title"]
    print(f"    Title: {listing_data['title']}")
    print(f"    Tags: {len(listing_data['tags'])}")
    print(f"    Price: ${listing_data['base_price']}")

    # Step 3: Generate automated images
    print(f"  [3/5] Generating listing images...")
    img_results = generate_all_images(city.slug)
    images_count = sum(1 for v in img_results.values() if v is not None)
    result["images_generated"] = images_count
    print(f"    Generated {images_count} automated images")

    if render_only:
        result["status"] = "rendered"
        print(f"\n  RENDER ONLY — skipping API upload")
        _log_result(result)
        return result

    # Step 4: Collect all images for upload
    all_images = _collect_images(city)
    print(f"  [4/5] Found {len(all_images)} total images for upload")

    if dry_run:
        result["status"] = "dry_run"
        print(f"\n  DRY RUN — would create draft listing:")
        print(f"    Title: {listing_data['title']}")
        print(f"    Description: {listing_data['description'][:100]}...")
        print(f"    Tags: {listing_data['tags']}")
        print(f"    Price: ${listing_data['base_price']}")
        print(f"    Images: {len(all_images)}")
        for i, img in enumerate(all_images, 1):
            print(f"      [{i}] {os.path.basename(img)}")
        _log_result(result)
        return result

    # Step 5: Create draft listing via API
    print(f"  [5/5] Creating draft listing via Etsy API...")
    try:
        from etsy.api_client import EtsyClient

        client = EtsyClient()
        shop_id = client.get_shop_id()

        # Create the draft listing
        created = client.create_draft_listing(
            shop_id=shop_id,
            title=listing_data["title"],
            description=listing_data["description"],
            price=listing_data["base_price"],
            tags=listing_data["tags"],
            is_digital=True,
        )
        listing_id = created.get("listing_id")
        result["listing_id"] = str(listing_id)
        print(f"    Draft created: listing_id={listing_id}")

        # Upload images
        for rank, img_path in enumerate(all_images, 1):
            try:
                client.upload_listing_image(shop_id, listing_id, img_path, rank=rank)
                print(f"    Uploaded image [{rank}]: {os.path.basename(img_path)}")
            except Exception as e:
                print(f"    [!] Image upload failed [{rank}]: {e}")

        result["status"] = "draft_created"
        print(f"\n  SUCCESS — Draft listing created (ID: {listing_id})")
        print(f"  Review at: https://www.etsy.com/your/shops/me/tools/listings/{listing_id}")

    except ImportError:
        result["status"] = "api_unavailable"
        result["error"] = "Etsy API client not configured"
        print(f"    ERROR: {result['error']}")
    except Exception as e:
        result["status"] = "api_error"
        result["error"] = str(e)
        print(f"    ERROR: {result['error']}")

    _log_result(result)
    return result


def publish_batch(
    cities: list[CityListing],
    dry_run: bool = False,
    render_only: bool = False,
) -> list[dict]:
    """Publish multiple cities."""
    print(f"\n{'#' * 60}")
    print(f"GeoLine Collective — Batch Publisher")
    print(f"  Cities: {len(cities)}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'RENDER ONLY' if render_only else 'LIVE'}")
    print(f"{'#' * 60}")

    results: list[dict] = []
    t0 = time.time()

    for i, city in enumerate(cities, 1):
        print(f"\n[{i}/{len(cities)}]")
        result = publish_city(city, dry_run=dry_run, render_only=render_only)
        results.append(result)

    elapsed = time.time() - t0

    # Summary
    ok = sum(1 for r in results if r["status"] in ("draft_created", "rendered", "dry_run"))
    errors = sum(1 for r in results if "error" in r["status"])
    print(f"\n{'#' * 60}")
    print(f"Batch complete in {elapsed:.0f}s")
    print(f"  Success: {ok}")
    print(f"  Errors: {errors}")
    if os.path.exists(PUBLISH_LOG):
        print(f"  Log: {PUBLISH_LOG}")
    print(f"{'#' * 60}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Batch publish Etsy listings")
    parser.add_argument("--tier", type=int, default=None, help="Tier to publish (1/2/3)")
    parser.add_argument("--city", type=str, default=None, help="Single city to publish")
    parser.add_argument("--all", action="store_true", help="Publish all 25 cities")
    parser.add_argument("--dry-run", action="store_true", help="Preview without API calls")
    parser.add_argument("--render-only", action="store_true", help="Just render + images, no API")
    args = parser.parse_args()

    if args.city:
        city = get_city(args.city)
        if not city:
            print(f"City not found: {args.city}")
            sys.exit(1)
        cities = [city]
    elif args.all:
        cities = ALL_CITIES
    elif args.tier:
        cities = get_cities_by_tier(args.tier)
    else:
        print("Specify --tier, --city, or --all")
        sys.exit(1)

    if not cities:
        print("No cities found")
        sys.exit(1)

    publish_batch(
        cities,
        dry_run=args.dry_run,
        render_only=args.render_only,
    )


if __name__ == "__main__":
    main()
