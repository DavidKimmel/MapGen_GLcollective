#!/usr/bin/env python3
"""Push County Map listings as drafts to Etsy — Digital + Print."""

import os
import sys
import time

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from etsy.api_client import EtsyClient
from etsy.style_config import (
    SHOP_ID, SHIPPING_PROFILE_ID, RETURN_POLICY_ID,
    READINESS_STATE_ID, TAXONOMY_ID, SECTION_CUSTOM_MAPS,
)

MOCKUPS_DIR = os.path.join(
    _PROJECT_DIR, "etsy", "renders", "CountyMap", "production", "mockups"
)

# Image upload order (max 10)
MOCKUP_FILES = [
    "Main.jpg",
    "choose_style_main_1.jpg",
    "choose_style_main_2.jpg",
    "Frame_038.jpg",
    "Frame_038 (1).jpg",
    "Frame_038 (2).jpg",
    "VV1_PSD_Post.jpg",
    "PSD.jpg",
    "PSD (1) (2).jpg",
    "2 Frames  - StudioBlank.jpg",
]

# --- Digital Listing ---
DIGITAL_TITLE = (
    "Custom County Map Digital Download | Personalized County Print, "
    "County Map Art, 12 Styles, Gift"
)

DIGITAL_TAGS = [
    "custom county map",
    "county map print",
    "county map digital",
    "personalized county art",
    "county wall art",
    "county map poster",
    "realtor closing gift",
    "hometown map print",
    "county map download",
    "custom-map",
    "housewarming gift",
    "county silhouette",
    "map print gift",
]

DIGITAL_PERSONALIZATION = (
    "Please provide your county and state:\n"
    'Example: "Fairfax County, Virginia" or "Cook County, IL"\n\n'
    "Optional: preferred style number (see photos for all 12 styles)"
)

# --- Print Listing ---
PRINT_TITLE = (
    "Custom County Map Print | Personalized County Wall Art, "
    "County Map Poster, 12 Styles, Housewarming Gift"
)

PRINT_TAGS = [
    "custom county map",
    "county map print",
    "personalized county art",
    "county wall art",
    "county map poster",
    "realtor closing gift",
    "hometown map print",
    "county silhouette map",
    "custom-map",
    "housewarming gift",
    "county art print",
    "first responder gift",
    "map print gift",
]

PRINT_PERSONALIZATION = DIGITAL_PERSONALIZATION


def _load_description(filename: str) -> str:
    """Load listing description from file, stopping at the TITLE section."""
    path = os.path.join(_PROJECT_DIR, "etsy", "renders", "CountyMap", filename)
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    desc_lines = []
    for line in lines:
        if line.strip() == "TITLE":
            break
        desc_lines.append(line)

    # Remove trailing separator lines
    while desc_lines and desc_lines[-1].strip().startswith("---"):
        desc_lines.pop()

    return "".join(desc_lines).strip()


def push_listing(
    client: EtsyClient,
    title: str,
    description: str,
    tags: list[str],
    price: float,
    listing_type: str,
    personalization: str,
) -> int:
    """Create a draft listing and upload mockup images."""
    clean_tags = [t[:20].replace(".", "") for t in tags[:13]]

    kwargs = dict(
        shop_id=SHOP_ID,
        title=title[:140],
        description=description,
        price=price,
        quantity=999,
        tags=clean_tags,
        who_made="i_did",
        when_made="made_to_order",
        taxonomy_id=TAXONOMY_ID,
        listing_type=listing_type,
        return_policy_id=RETURN_POLICY_ID,
        shop_section_id=SECTION_CUSTOM_MAPS,
        readiness_state_id=READINESS_STATE_ID,
    )

    if listing_type == "physical":
        kwargs["shipping_profile_id"] = SHIPPING_PROFILE_ID

    result = client.create_draft_listing(**kwargs)
    listing_id = result["listing_id"]
    print(f"  Draft created: listing_id={listing_id}")

    # Enable personalization
    client.update_listing(
        SHOP_ID, listing_id,
        is_personalizable=True,
        personalization_is_required=True,
        personalization_instructions=personalization[:256],
    )
    print(f"  Personalization enabled")

    # Upload mockup images
    for rank, fname in enumerate(MOCKUP_FILES, 1):
        img_path = os.path.join(MOCKUPS_DIR, fname)
        if os.path.exists(img_path):
            try:
                client.upload_listing_image(
                    SHOP_ID, listing_id, img_path, rank=rank,
                    alt_text=f"County map art - {fname.split('.')[0]}"[:500],
                )
                print(f"  Image {rank}: {fname}")
                time.sleep(0.5)
            except Exception as e:
                print(f"  Image {rank} FAILED: {e}")
        else:
            print(f"  Image {rank} MISSING: {fname}")

    return listing_id


def main() -> None:
    client = EtsyClient()

    # 1. Digital listing
    print("\n=== DIGITAL LISTING ===")
    digital_desc = _load_description("listing_digital.txt")
    digital_id = push_listing(
        client,
        title=DIGITAL_TITLE,
        description=digital_desc,
        tags=DIGITAL_TAGS,
        price=4.07,
        listing_type="download",
        personalization=DIGITAL_PERSONALIZATION,
    )

    # 2. Print listing
    print("\n=== PRINT LISTING ===")
    print_desc = _load_description("listing_print.txt")
    print_id = push_listing(
        client,
        title=PRINT_TITLE,
        description=print_desc,
        tags=PRINT_TAGS,
        price=27.00,
        listing_type="physical",
        personalization=PRINT_PERSONALIZATION,
    )

    print(f"\n{'='*60}")
    print(f"Digital draft: listing_id={digital_id}")
    print(f"Print draft:   listing_id={print_id}")
    print(f"{'='*60}")
    print("Both listings created as DRAFTS. Review in Etsy Listing Manager.")
    print("Next: add variants (styles × sizes) manually or via API.")


if __name__ == "__main__":
    main()
