"""Etsy Listing Bot — Playwright automation for creating city map listings.

Copies the most recent listing, replaces images/title/description/tags/SKUs,
and saves as draft. Processes one or many cities.

First run: logs you into Etsy (manual login, cookies persist).
Subsequent runs: fully automated.

Usage:
    python scripts/etsy_listing_bot.py --city boston
    python scripts/etsy_listing_bot.py --tier 5
    python scripts/etsy_listing_bot.py --cities boston,miami,new_york
    python scripts/etsy_listing_bot.py --city boston --dry-run
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

# Ensure project root on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout

from etsy.city_list import ALL_CITIES, CityListing, get_city, get_cities_by_tier
from etsy.listing_generator import generate_listing

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

RENDERS_DIR = Path("etsy/renders")
CHROME_USER_DATA = Path(os.path.expanduser("~")) / "AppData/Local/Google/Chrome/User Data"
LISTINGS_URL = "https://www.etsy.com/your/shops/me/tools/listings"

# Source listing to copy from (Austin — first in the list)
# We always copy the first listing on the page (most recent)

# Image upload order (mockup_composer output)
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

# The 4 city-specific tag patterns to replace (always first 4 tags)
# Old tags: "{old_city} map print", "{old_city} wall art", "{old_city} poster", "{old_city} gift"

# SKU pattern: GLC-{CITY_SLUG}-{FORMAT}-{SIZE}
SKU_PATTERN = re.compile(r"GLC-([A-Z_]+)-(DIG|UNF|FRB|FRW)-(\d+X\d+)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_city_images(city: CityListing) -> list[str]:
    """Return list of image file paths for a city, in upload order."""
    city_dir = RENDERS_DIR / city.slug
    images = []
    for template in IMAGE_ORDER:
        fname = template.format(slug=city.slug)
        fpath = city_dir / fname
        if fpath.exists():
            images.append(str(fpath.resolve()))
        else:
            print(f"  WARNING: Missing image {fpath}")
    return images


def parse_listing_data(city: CityListing) -> dict:
    """Generate all the listing data we need for a city."""
    listing = generate_listing(city)
    # City-specific tags are first 4
    city_tags = [
        f"{city.city.lower()} map print",
        f"{city.city.lower()} wall art",
        f"{city.city.lower()} poster",
        f"{city.city.lower()} gift",
    ]
    # SKU prefix
    sku_prefix = f"GLC-{city.slug.upper().replace(' ', '_')}"

    return {
        "title": listing["title"],
        "intro": listing["description"],  # Just the intro paragraph
        "city_tags": city_tags,
        "sku_prefix": sku_prefix,
        "slug_upper": city.slug.upper(),
    }


# ---------------------------------------------------------------------------
# Playwright automation steps
# ---------------------------------------------------------------------------

def wait_for_editor(page: Page) -> None:
    """Wait for the listing editor to fully load."""
    page.wait_for_load_state("networkidle", timeout=30000)
    # Wait for the title input to appear
    page.wait_for_selector("input[name='title']", timeout=15000)
    time.sleep(1)  # Extra buffer for React hydration


def step_copy_listing(page: Page) -> None:
    """Navigate to listings and copy the first (most recent) listing."""
    print("  [1/6] Copying most recent listing...")
    page.goto(LISTINGS_URL, wait_until="networkidle", timeout=30000)
    time.sleep(2)

    # Click the gear/manage button on the first listing
    manage_buttons = page.locator("button:has-text('Manage this listing')")
    manage_buttons.first.click()
    time.sleep(1)

    # Click "Copy" in the dropdown
    page.locator("button:has-text('Copy'), a:has-text('Copy')").first.click()
    time.sleep(3)

    # Wait for editor to load
    wait_for_editor(page)
    print("    Listing copied, editor loaded.")


def step_delete_and_upload_photos(page: Page, image_paths: list[str]) -> None:
    """Delete all existing photos and upload new ones."""
    print(f"  [2/6] Uploading {len(image_paths)} images...")

    # Click "Delete all" if it exists
    delete_all = page.locator("button:has-text('Delete all'), a:has-text('Delete all')")
    if delete_all.count() > 0:
        delete_all.first.click()
        time.sleep(1)
        # Confirm the dialog
        confirm = page.locator("button:has-text('Delete all')")
        if confirm.count() > 1:
            confirm.last.click()
        elif confirm.count() > 0:
            confirm.first.click()
        time.sleep(2)

    # Find the file input and upload all images
    file_input = page.locator("input[type='file']").first
    file_input.set_input_files(image_paths)
    print(f"    Uploaded {len(image_paths)} files, waiting for processing...")
    time.sleep(5)  # Wait for images to process


def step_update_title(page: Page, new_title: str) -> None:
    """Replace the listing title."""
    print(f"  [3/6] Setting title: {new_title[:60]}...")
    title_input = page.locator("input[name='title']")
    title_input.click()
    title_input.fill("")
    title_input.fill(new_title)
    time.sleep(0.5)


def step_update_description(page: Page, new_intro: str) -> None:
    """Replace only the first paragraph (intro) of the description."""
    print("  [4/6] Updating description intro...")
    desc = page.locator("textarea[name='description']")
    current_text = desc.input_value()

    # The description starts with an emoji + the intro paragraph.
    # Find the end of the first paragraph (double newline or "WHAT YOU GET")
    # Pattern: everything before the first section header
    markers = ["✦ WHAT YOU GET", "❖ WHAT YOU GET", "WHAT YOU GET"]
    split_pos = -1
    for marker in markers:
        pos = current_text.find(marker)
        if pos != -1:
            split_pos = pos
            break

    if split_pos == -1:
        # Fallback: replace everything before double newline
        parts = current_text.split("\n\n", 1)
        if len(parts) > 1:
            new_text = f"📍 {new_intro}\n\n{parts[1]}"
        else:
            new_text = f"📍 {new_intro}"
    else:
        # Replace everything before the marker
        new_text = f"📍 {new_intro}\n\n{current_text[split_pos:]}"

    desc.click()
    desc.fill("")
    desc.fill(new_text)
    time.sleep(0.5)


def step_update_tags(page: Page, new_city_tags: list[str], old_city_name: str) -> None:
    """Remove old city-specific tags (first 4) and add new ones."""
    print(f"  [5/6] Updating tags ({', '.join(new_city_tags[:2])}, ...)...")

    # Scroll to tags section
    tags_section = page.locator("text=Tags")
    if tags_section.count() > 0:
        tags_section.first.scroll_into_view_if_needed()
        time.sleep(1)

    # Find tag remove buttons — they're X buttons on tag chips
    # The old city tags contain the old city name
    old_city_lower = old_city_name.lower()
    tag_patterns = [
        f"{old_city_lower} map print",
        f"{old_city_lower} wall art",
        f"{old_city_lower} poster",
        f"{old_city_lower} gift",
    ]

    # Remove old city tags by clicking X on matching tags
    for pattern in tag_patterns:
        # Find the tag chip containing this text and click its remove button
        tag_chip = page.locator(f"button[aria-label*='{pattern}'], button:has-text('{pattern}')")
        if tag_chip.count() > 0:
            tag_chip.first.click()
            time.sleep(0.3)
        else:
            # Try finding by partial text in the tag area
            remove_btn = page.locator(f"[aria-label*='Remove {pattern}'], [aria-label*='remove {pattern}']")
            if remove_btn.count() > 0:
                remove_btn.first.click()
                time.sleep(0.3)

    # Add new city tags
    tag_input = page.locator("input[placeholder*='Shape'], input[placeholder*='search']").first
    for tag in new_city_tags:
        tag_input.fill(tag)
        time.sleep(0.3)
        # Press Enter or click Add
        tag_input.press("Enter")
        time.sleep(0.3)

    time.sleep(0.5)


def step_update_skus(page: Page, old_slug_upper: str, new_slug_upper: str) -> None:
    """Replace city slug in all 20 SKU fields."""
    print(f"  [6/6] Updating SKUs: {old_slug_upper} → {new_slug_upper}...")

    # Scroll to Item Options section
    item_options = page.locator("text=Item options")
    if item_options.count() > 0:
        item_options.first.scroll_into_view_if_needed()
        time.sleep(1)

    # Find all SKU input fields
    sku_inputs = page.locator("input[name*='sku'], input[class*='sku']")
    count = sku_inputs.count()

    if count == 0:
        # Try alternative selectors — the SKU fields in the variations table
        # They contain text like GLC-AUSTIN-DIG-8X10
        sku_inputs = page.locator("input[value*='GLC-']")
        count = sku_inputs.count()

    updated = 0
    for i in range(count):
        inp = sku_inputs.nth(i)
        current_val = inp.input_value()
        if old_slug_upper in current_val:
            new_val = current_val.replace(old_slug_upper, new_slug_upper)
            inp.click()
            inp.fill("")
            inp.fill(new_val)
            updated += 1
            time.sleep(0.1)

    print(f"    Updated {updated}/{count} SKU fields.")


def step_save_draft(page: Page) -> None:
    """Click 'Save as draft' button."""
    print("  Saving as draft...")
    save_btn = page.locator("button:has-text('Save as draft')")
    if save_btn.count() > 0:
        save_btn.first.click()
        time.sleep(3)
        page.wait_for_load_state("networkidle", timeout=15000)
        print("    Draft saved!")
    else:
        print("    WARNING: 'Save as draft' button not found!")


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

def detect_source_city(page: Page) -> str:
    """Detect which city the copied listing belongs to from the title."""
    title_input = page.locator("input[name='title']")
    current_title = title_input.input_value()

    # Try to match against known cities
    for city in ALL_CITIES:
        if city.city.lower() in current_title.lower():
            return city.city
    return "Austin"  # Default fallback


def process_city(page: Page, city: CityListing, dry_run: bool = False) -> bool:
    """Full pipeline for one city listing."""
    print(f"\n{'='*60}")
    print(f"Processing: {city.city}, {city.state}")
    print(f"{'='*60}")

    # Check images exist
    images = get_city_images(city)
    if len(images) < 7:
        print(f"  SKIP — only {len(images)} images found (need at least 7)")
        return False

    # Generate listing data
    data = parse_listing_data(city)

    if dry_run:
        print(f"  [DRY RUN] Would create listing:")
        print(f"    Title: {data['title']}")
        print(f"    Tags: {', '.join(data['city_tags'])}")
        print(f"    SKU prefix: {data['sku_prefix']}")
        print(f"    Images: {len(images)}")
        return True

    try:
        # Step 1: Copy the most recent listing
        step_copy_listing(page)

        # Detect source city for tag/SKU replacement
        source_city = detect_source_city(page)
        source_slug_upper = source_city.upper().replace(" ", "_")

        # Step 2: Delete old photos, upload new ones
        step_delete_and_upload_photos(page, images)

        # Step 3: Update title
        step_update_title(page, data["title"])

        # Step 4: Update description intro
        step_update_description(page, data["intro"])

        # Step 5: Update tags
        step_update_tags(page, data["city_tags"], source_city)

        # Step 6: Update SKUs
        step_update_skus(page, source_slug_upper, data["slug_upper"])

        # Save as draft
        step_save_draft(page)

        print(f"\n  DONE — {city.city} saved as draft!")
        return True

    except PWTimeout as e:
        print(f"\n  TIMEOUT ERROR: {e}")
        return False
    except Exception as e:
        print(f"\n  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Etsy listing automation via Playwright")
    parser.add_argument("--city", help="Single city name or slug")
    parser.add_argument("--cities", help="Comma-separated city names/slugs")
    parser.add_argument("--tier", type=int, help="Process all cities in a tier")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    parser.add_argument("--headed", action="store_true", default=True,
                        help="Show browser window (default: True)")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    args = parser.parse_args()

    # Build city list
    cities: list[CityListing] = []
    if args.city:
        c = get_city(args.city)
        if not c:
            # Try slug match
            for cc in ALL_CITIES:
                if cc.slug == args.city.lower().replace(" ", "_"):
                    c = cc
                    break
        if not c:
            print(f"City not found: {args.city}")
            sys.exit(1)
        cities = [c]
    elif args.cities:
        for name in args.cities.split(","):
            name = name.strip()
            c = get_city(name)
            if not c:
                for cc in ALL_CITIES:
                    if cc.slug == name.lower().replace(" ", "_"):
                        c = cc
                        break
            if c:
                cities.append(c)
            else:
                print(f"  WARNING: City not found: {name}")
    elif args.tier:
        cities = get_cities_by_tier(args.tier)
    else:
        print("Specify --city, --cities, or --tier")
        sys.exit(1)

    if not cities:
        print("No cities to process!")
        sys.exit(1)

    headless = args.headless and not args.headed
    print(f"\nEtsy Listing Bot — {len(cities)} cities")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")

    # Dry run: just print what would happen, no browser needed
    if args.dry_run:
        for i, city in enumerate(cities):
            images = get_city_images(city)
            data = parse_listing_data(city)
            print(f"\n[{i+1}/{len(cities)}] {city.city}, {city.state}")
            print(f"  Title: {data['title']}")
            print(f"  Tags: {', '.join(data['city_tags'])}")
            print(f"  SKU prefix: {data['sku_prefix']}")
            print(f"  Images: {len(images)}")
            if len(images) < 7:
                print(f"  WARNING: Only {len(images)} images found!")
        print(f"\nDry run complete — {len(cities)} cities ready.")
        sys.exit(0)

    pw_profile = Path("etsy/.playwright_profile")
    pw_profile.mkdir(parents=True, exist_ok=True)

    # Copy Chrome cookies/session to Playwright profile if not already done
    chrome_default = CHROME_USER_DATA / "Default"
    pw_default = pw_profile / "Default"
    if chrome_default.exists() and not (pw_default / "Cookies").exists():
        print("Copying Chrome session cookies...")
        import shutil
        pw_default.mkdir(parents=True, exist_ok=True)
        # Copy essential session files
        for fname in ["Cookies", "Cookies-journal",
                      "Login Data", "Login Data-journal",
                      "Web Data", "Web Data-journal",
                      "Preferences", "Secure Preferences"]:
            src = chrome_default / fname
            if src.exists():
                shutil.copy2(str(src), str(pw_default / fname))
                print(f"  Copied {fname}")
        # Copy Local State from parent
        local_state = CHROME_USER_DATA / "Local State"
        if local_state.exists():
            shutil.copy2(str(local_state), str(pw_profile / "Local State"))
            print("  Copied Local State")
        print("  Session copied!")

    print(f"Profile: {pw_profile.resolve()}")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(pw_profile.resolve()),
            headless=False,
            channel="chrome",
            viewport={"width": 1400, "height": 900},
            slow_mo=150,
        )

        page = context.pages[0] if context.pages else context.new_page()

        # Check if logged in
        page.goto(LISTINGS_URL, wait_until="networkidle", timeout=30000)
        time.sleep(2)

        if "sign-in" in page.url.lower() or "signin" in page.url.lower():
            print("\n" + "="*60)
            print("NOT LOGGED IN — Please log into Etsy in the browser window.")
            print("The script will continue once you reach the listings page.")
            print("="*60 + "\n")
            # Wait for user to log in (up to 5 minutes)
            page.wait_for_url("**/tools/listings**", timeout=300000)
            print("  Logged in! Continuing...\n")

        ok = 0
        fail = 0
        for i, city in enumerate(cities):
            print(f"\n[{i+1}/{len(cities)}]", end="")
            success = process_city(page, city, dry_run=args.dry_run)
            if success:
                ok += 1
            else:
                fail += 1

        print(f"\n{'='*60}")
        print(f"DONE — {ok} succeeded, {fail} failed")
        print(f"{'='*60}")

        context.close()


if __name__ == "__main__":
    main()
