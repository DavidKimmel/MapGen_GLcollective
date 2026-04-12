"""Publish AtlasMap draft listings to Etsy — one digital, one print.

Creates two draft listings with curated mockup images showing a mix of
portrait and landscape states. Buyer selects state via personalization.

Usage:
    python -m scripts.publish_atlasmap_drafts --dry-run
    python -m scripts.publish_atlasmap_drafts --live
    python -m scripts.publish_atlasmap_drafts --live --listing digital
    python -m scripts.publish_atlasmap_drafts --live --listing print
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from etsy.api_client import EtsyClient, EtsyApiError
from etsy.style_config import (
    SHOP_ID, SHIPPING_PROFILE_ID, RETURN_POLICY_ID,
    READINESS_STATE_ID, TAXONOMY_ID, SECTION_CITY_MAPS,
)

ATLAS_DIR = Path(r"C:\MapGen_GLcollective\etsy\renders\AtlasMap")
MOCKUPS_DIR = ATLAS_DIR / "new_mockups_fill"
PRINT_READY = ATLAS_DIR / "print_ready"

# ── Listing text ────────────────────────────────────────────────────

DIGITAL_TITLE = "State Topographic Map Digital Download | Elevation Relief Art, US State Map Print, Terrain Wall Art, Geography Gift"

PRINT_TITLE = "State Topographic Map Print | Elevation Relief Wall Art, US State Poster, Terrain Map, Geography Gift"

TAGS = [
    "topographic map",       # 15
    "elevation map print",   # 19
    "topographic wall art",  # 19
    "relief map poster",     # 17
    "state map art",         # 13
    "terrain map print",     # 17
    "geography gift",        # 14
    "state elevation art",   # 19
    "topography print",      # 16
    "housewarming gift",     # 17
    "US state poster",       # 15
    "mountain map art",      # 16
    "custom-map",            # 10
]


def load_description(listing_type: str) -> str:
    """Load description from the listing text file (everything before the TITLE section)."""
    filename = "listing_digital.txt" if listing_type == "digital" else "listing_print.txt"
    path = ATLAS_DIR / filename
    text = path.read_text(encoding="utf-8")
    # Everything before the TITLE marker is the description
    marker = "———————————————————————\nTITLE"
    idx = text.find(marker)
    if idx > 0:
        return text[:idx].strip()
    return text.strip()


# ── Image sets ──────────────────────────────────────────────────────
# Curated mix of portrait + landscape states for the listing photos.
# These pull from per-state mockup folders to show variety.

def build_digital_images() -> list[Path]:
    """Build image list for the digital listing."""
    return [
        # Hero: landscape state in white frame
        PRINT_READY / "Colorado" / "mockups" / "colorado_h6.jpg",
        # Portrait state lifestyle
        PRINT_READY / "California" / "mockups" / "california_frame_wall.jpg",
        # 3-frame set
        PRINT_READY / "California" / "mockups" / "california_cls4.jpg",
        # Landscape lifestyle
        PRINT_READY / "Colorado" / "mockups" / "colorado_h39.jpg",
        # Portrait flat lay
        PRINT_READY / "Georgia" / "mockups" / "georgia_flatlay.jpg",
        # Landscape above couch
        PRINT_READY / "Texas" / "mockups" / "texas_h42.jpg",
        # 6-state grid
        MOCKUPS_DIR / "atlas_6state_grid.jpg",
        # Landscape linen
        PRINT_READY / "Alaska" / "mockups" / "alaska_linen.jpg",
        # Portrait lifestyle
        PRINT_READY / "Idaho" / "mockups" / "idaho_frame15.jpg",
        # Detail crop
        MOCKUPS_DIR / "atlas_detail_crop_edge.jpg",
    ]


def build_print_images() -> list[Path]:
    """Build image list for the print listing."""
    return [
        # Hero: landscape in white frame
        PRINT_READY / "Colorado" / "mockups" / "colorado_h6.jpg",
        # Landscape brick loft
        PRINT_READY / "Tennessee" / "mockups" / "tennessee_h39.jpg",
        # Portrait in black frame
        PRINT_READY / "California" / "mockups" / "california_main.jpg",
        # Landscape above couch
        PRINT_READY / "Texas" / "mockups" / "texas_h42.jpg",
        # Portrait flat lay on linen
        PRINT_READY / "Georgia" / "mockups" / "georgia_flatlay.jpg",
        # Landscape concrete wall
        PRINT_READY / "Montana" / "mockups" / "montana_h13.jpg",
        # 6-state grid
        MOCKUPS_DIR / "atlas_6state_grid.jpg",
        # Portrait 3-frame set
        PRINT_READY / "Alabama" / "mockups" / "alabama_nov3.jpg",
        # Landscape linen
        PRINT_READY / "Alaska" / "mockups" / "alaska_linen.jpg",
        # Detail crop
        MOCKUPS_DIR / "atlas_detail_crop_edge.jpg",
    ]


# ── Draft creation ──────────────────────────────────────────────────

def create_draft(
    client: EtsyClient,
    shop_id: int,
    listing_type: str,
    *,
    live: bool,
) -> None:
    is_digital = listing_type == "digital"
    title = DIGITAL_TITLE if is_digital else PRINT_TITLE
    description = load_description(listing_type)
    price = 9.99 if is_digital else 34.83  # base price (smallest size)
    images = build_digital_images() if is_digital else build_print_images()

    print(f"\n{'=' * 60}")
    print(f"  AtlasMap {'DIGITAL' if is_digital else 'PRINT'} Draft")
    print(f"{'=' * 60}")
    print(f"  Title: {title[:80]}...")
    print(f"  Price: ${price}")
    print(f"  Tags:  {len(TAGS)}")
    print(f"  Images: {len(images)}")

    # Verify all images exist
    missing = [p for p in images if not p.exists()]
    if missing:
        print(f"\n  ERROR: {len(missing)} missing images:")
        for m in missing:
            print(f"    {m}")
        return

    for i, img in enumerate(images, 1):
        print(f"    [{i:2d}] {img.parent.parent.name}/{img.name}")

    if not live:
        print("\n  [dry-run] Would create draft + upload images")
        return

    # Create draft
    try:
        etsy_type = "download" if is_digital else "physical"
        kwargs: dict = {
            "shop_id": shop_id,
            "title": title,
            "description": description,
            "price": price,
            "quantity": 999,
            "tags": TAGS,
            "who_made": "i_did",
            "when_made": "made_to_order",
            "taxonomy_id": TAXONOMY_ID,
            "listing_type": etsy_type,
            "return_policy_id": RETURN_POLICY_ID,
            "shop_section_id": SECTION_CITY_MAPS,
            "readiness_state_id": READINESS_STATE_ID,
        }
        if not is_digital:
            kwargs["shipping_profile_id"] = SHIPPING_PROFILE_ID

        created = client.create_draft_listing(**kwargs)
        listing_id = created.get("listing_id")
        print(f"\n  Draft created: {listing_id}")
        print(f"  https://www.etsy.com/your/shops/me/tools/listings/{listing_id}")

    except EtsyApiError as e:
        print(f"\n  ERROR creating draft: {e}")
        return

    # Upload images
    print(f"\n  Uploading {len(images)} images...")
    for rank, img_path in enumerate(images, 1):
        try:
            client.upload_listing_image(shop_id, listing_id, str(img_path), rank=rank)
            print(f"    [{rank:2d}] {img_path.name} OK")
        except EtsyApiError as e:
            print(f"    [{rank:2d}] {img_path.name} FAILED: {e}")

    print(f"\n  DONE — review at https://www.etsy.com/your/shops/me/tools/listings/{listing_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish AtlasMap drafts to Etsy.")
    parser.add_argument("--live", action="store_true", help="Actually create drafts (default is dry-run).")
    parser.add_argument("--dry-run", action="store_true", help="Preview only.")
    parser.add_argument("--listing", choices=["digital", "print", "both"], default="both",
                        help="Which listing to create.")
    args = parser.parse_args()

    live = args.live and not args.dry_run

    if live:
        print("*** LIVE MODE — will create Etsy draft listings ***")
        client = EtsyClient()
        shop_id = client.get_shop_id()
        print(f"Shop ID: {shop_id}")
    else:
        print("--- dry run ---")
        client = None
        shop_id = None

    listings = ["digital", "print"] if args.listing == "both" else [args.listing]

    for lt in listings:
        if live:
            create_draft(client, shop_id, lt, live=True)
        else:
            create_draft(None, None, lt, live=False)

    return 0


if __name__ == "__main__":
    sys.exit(main())
