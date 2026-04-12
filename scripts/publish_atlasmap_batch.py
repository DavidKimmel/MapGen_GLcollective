"""Publish individual AtlasMap listings per state — digital + print.

Creates 100 draft listings (50 digital + 50 print) with state-specific
titles, tags, descriptions, and mockup images.

Usage:
    python -m scripts.publish_atlasmap_batch --dry-run
    python -m scripts.publish_atlasmap_batch --dry-run --type digital
    python -m scripts.publish_atlasmap_batch --live --state Colorado
    python -m scripts.publish_atlasmap_batch --live --type print
    python -m scripts.publish_atlasmap_batch --live --start-from Montana
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from etsy.api_client import EtsyClient, EtsyApiError
from etsy.style_config import (
    SHIPPING_PROFILE_ID, RETURN_POLICY_ID,
    READINESS_STATE_ID, TAXONOMY_ID, SECTION_CITY_MAPS,
)

ATLAS_DIR = Path(r"C:\MapGen_GLcollective\etsy\renders\AtlasMap\print_ready")
MOCKUPS_GENERAL = Path(r"C:\MapGen_GLcollective\etsy\renders\AtlasMap\new_mockups_fill")
PUBLISH_LOG = Path(r"C:\MapGen_GLcollective\etsy\atlasmap_publish_log.csv")

HORIZONTAL_STATES: set[str] = {
    "Alaska", "Arkansas", "Colorado", "Connecticut", "Florida", "Hawaii",
    "Iowa", "Kansas", "Kentucky", "Louisiana", "Maryland", "Massachusetts",
    "Missouri", "Montana", "Nebraska", "NewYork", "NorthCarolina",
    "NorthDakota", "Oklahoma", "Oregon", "Pennsylvania", "SouthCarolina",
    "SouthDakota", "Tennessee", "Texas", "Virginia", "Washington",
    "WestVirginia", "Wyoming",
}

# ── State name formatting ───────────────────────────────────────────

def display_name(folder_name: str) -> str:
    """Convert folder name to display name: 'NewYork' → 'New York'."""
    spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', folder_name)
    return spaced


def slug(folder_name: str) -> str:
    return folder_name.lower()


def is_landscape(state: str) -> bool:
    return state in HORIZONTAL_STATES


# ── Tags ────────────────────────────────────────────────────────────

def build_tags(state: str, listing_type: str) -> list[str]:
    """Build 13 SEO tags per state, each ≤ 20 chars."""
    name = display_name(state)
    short = name if len(name) <= 10 else name.split()[0]  # First word if name is long
    tags = [
        f"{short} topo map",         # e.g. "Colorado topo map"
        f"{short} map print",
        f"{short} wall art",
        "topographic map",
        "elevation map print",
        "relief map poster",
        "state map art",
        "terrain map print",
        "geography gift",
        "topography print",
        "housewarming gift",
        "US state poster",
        "custom-map",
    ]
    # Enforce 20 char limit
    return [t[:20] for t in tags[:13]]


# ── Titles ──────────────────────────────────────────────────────────

def build_title(state: str, listing_type: str) -> str:
    name = display_name(state)
    if listing_type == "digital":
        return f"{name} Topographic Map Digital Download | Elevation Relief Art, State Map Print, Geography Gift"
    else:
        return f"{name} Topographic Map Print | Elevation Relief Wall Art, State Poster, Terrain Map Gift"


# ── Description ─────────────────────────────────────────────────────

def build_description(state: str, listing_type: str) -> str:
    name = display_name(state)
    orientation = "landscape (wider than tall)" if is_landscape(state) else "portrait (taller than wide)"

    if listing_type == "digital":
        return f"""📍 {name.upper()} TOPOGRAPHIC MAP — DIGITAL DOWNLOAD — Stunning elevation relief art showing every mountain, valley, and coastline of {name} — ready to print at home or at any print shop.

Real terrain data transformed into a vivid color-ramped relief map. High elevations glow in warm amber and snow white. Valleys and coasts cool into ocean blue. The state is clipped to its exact boundary with a subtle ghost relief showing surrounding terrain for context.
———————————————————————
📋 HOW IT WORKS
———————————————————————
1️⃣ Purchase this listing
2️⃣ Receive a branded PDF immediately after checkout
3️⃣ Open the PDF and click the download link for your preferred size
4️⃣ Print at home or at any local print shop

It's that easy — no waiting, no messaging, instant access to all sizes.
———————————————————————
📲 YOU WILL RECEIVE
———————————————————————
◈ 1 branded PDF delivered instantly after purchase
◈ Inside: download links for ALL 5 print sizes
◈ 💯 300 DPI — print-shop quality PNG files
◈ No need to choose a size upfront — you get every size included

NOTE: {name} is {orientation}. Your print files will match this orientation.
———————————————————————
📐 INCLUDED SIZES
———————————————————————
◈ 8×10 inches | 11×14 inches | 16×20 inches | 18×24 inches | 24×36 inches
◈ All 5 sizes included with your purchase
———————————————————————
✨ WHAT MAKES THIS MAP SPECIAL
———————————————————————
This isn't a flat cartoon or simple outline. This map is built from real USGS elevation data, processed through a custom color-ramped renderer that turns raw terrain into fine art.

◈ Snow-capped peaks glow in warm whites and burnt amber
◈ Foothills and plateaus transition through golden yellows
◈ River valleys and coastlines cool into soft blues
◈ Subtle hillshading reveals every ridge and drainage pattern
◈ A faint ghost relief of surrounding terrain provides geographic context

The state name is set in classic Cormorant Garamond — an elegant, editorial serif that gives the print a refined cartographic feel.
———————————————————————
⚠️ PLEASE NOTE
———————————————————————
◈ This is a DIGITAL DOWNLOAD — no physical item will be shipped
◈ Frame shown in listing photos is for display purposes only
◈ You can print the files as many times as you need
◈ Personal use only — files may not be shared, sold, or redistributed
———————————————————————
🖨️ PRINT IT YOURSELF
———————————————————————
Our digital files can be printed at:
◈ Home on your own printer
◈ Local print shops (FedEx, Staples, Office Depot)
◈ Online print services (Shutterfly, Mpix, Nations Photo Lab)
◈ Any professional printer — just send the PNG file
———————————————————————
💛 MAKES A GREAT GIFT FOR:
———————————————————————
◈ Outdoor enthusiasts — hikers, climbers, skiers who know the terrain
◈ Hometown pride — see the land that shaped your state
◈ Housewarming — a stunning conversation piece for any wall
◈ Teachers and students — geography and earth science come alive
◈ Office or study decor — elegant, distinctive, and smart
◈ Realtor closing gifts — a unique touch for a new homeowner
———————————————————————
❓ QUESTIONS?
———————————————————————
Feel free to message us — we're happy to help with questions about sizes, orientation, or anything else.
━━━━━━━━━━━━━━━━━━━━━━━━━━

© GeoLine Collective — Cartography as Craft"""

    else:  # print
        return f"""📍 {name.upper()} TOPOGRAPHIC MAP PRINT — Stunning elevation relief art showing every mountain, valley, and coastline of {name} — printed on premium matte paper and shipped right to your door.

Real terrain data transformed into a vivid color-ramped relief map. High elevations glow in warm amber and snow white. Valleys and coasts cool into ocean blue. The state is clipped to its exact boundary with a subtle ghost relief showing surrounding terrain for context.
———————————————————————
📋 HOW TO ORDER
———————————————————————
1️⃣ Select your Size from the dropdown
2️⃣ Complete your purchase

We'll print your map and ship it directly to you within 3–5 business days.

NOTE: {name} is {orientation}. Your print will match this orientation.
———————————————————————
🖨️ PRINT DETAILS
———————————————————————
◈ Paper Finishing: Matte, smooth, non-reflective surface
◈ Paper Weight: 170 gsm (65 lb), thickness: 0.19 mm (7.5 mils)
◈ Sustainable Paper: FSC-certified or equivalent
◈ Archival inks for long-lasting color
◈ Printed and shipped from the US

NOTE: Frame shown in listing photos is for display purposes only and not included.
———————————————————————
📐 AVAILABLE SIZES
———————————————————————
◈ Small (8×10) | Medium (11×14) | Large (16×20)
◈ XL (18×24) | Poster (24×36)
———————————————————————
✨ WHAT MAKES THIS MAP SPECIAL
———————————————————————
This isn't a flat cartoon or simple outline. This map is built from real USGS elevation data, processed through a custom color-ramped renderer that turns raw terrain into fine art.

◈ Snow-capped peaks glow in warm whites and burnt amber
◈ Foothills and plateaus transition through golden yellows
◈ River valleys and coastlines cool into soft blues
◈ Subtle hillshading reveals every ridge and drainage pattern
◈ A faint ghost relief of surrounding terrain provides geographic context

The state name is set in classic Cormorant Garamond — an elegant, editorial serif that gives the print a refined cartographic feel.
———————————————————————
💛 MAKES A GREAT GIFT FOR:
———————————————————————
◈ Outdoor enthusiasts — hikers, climbers, skiers who know the terrain
◈ Hometown pride — see the land that shaped your state
◈ Housewarming — a stunning conversation piece for any wall
◈ Teachers and students — geography and earth science come alive
◈ Office or study decor — elegant, distinctive, and smart
◈ Realtor closing gifts — a unique touch for a new homeowner
———————————————————————
❓ QUESTIONS?
———————————————————————
Feel free to message us — we're happy to help with questions about sizes, orientation, or anything else.
━━━━━━━━━━━━━━━━━━━━━━━━━━

© GeoLine Collective — Cartography as Craft"""


# ── Image ordering ──────────────────────────────────────────────────

def build_images_portrait(state: str) -> list[Path]:
    """9 images for portrait states: main (hero), frame_wall, cls4, ..."""
    s = slug(state)
    d = ATLAS_DIR / state / "mockups"
    return [
        d / f"{s}_main.jpg",
        d / f"{s}_frame_wall.jpg",
        d / f"{s}_cls4.jpg",
        d / f"{s}_flatlay.jpg",
        d / f"{s}_frame_boho.jpg",
        d / f"{s}_frame15.jpg",
        d / f"{s}_frame33.jpg",
        d / f"{s}_nov3.jpg",
        d / f"{s}_detail_crop.jpg",
    ]


def build_images_landscape(state: str) -> list[Path]:
    """8 images for landscape states: h6 (hero), h39, h4, h42, linen, h13, h5, crop."""
    s = slug(state)
    d = ATLAS_DIR / state / "mockups"
    return [
        d / f"{s}_h6.jpg",
        d / f"{s}_h39.jpg",
        d / f"{s}_h4.jpg",
        d / f"{s}_h42.jpg",
        d / f"{s}_linen.jpg",
        d / f"{s}_h13.jpg",
        d / f"{s}_h5.jpg",
        d / f"{s}_detail_crop.jpg",
    ]


def build_images(state: str) -> list[Path]:
    if is_landscape(state):
        return build_images_landscape(state)
    return build_images_portrait(state)


# ── Logging ─────────────────────────────────────────────────────────

def log_result(result: dict) -> None:
    file_exists = PUBLISH_LOG.exists()
    fieldnames = ["timestamp", "state", "type", "status", "listing_id", "title", "images", "error"]
    with open(PUBLISH_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            **{k: result.get(k, "") for k in fieldnames if k != "timestamp"},
        })


# ── Draft creation ──────────────────────────────────────────────────

def publish_state(
    client: EtsyClient | None,
    shop_id: int | None,
    state: str,
    listing_type: str,
    *,
    live: bool,
) -> dict:
    result = {
        "state": state,
        "type": listing_type,
        "status": "pending",
        "listing_id": "",
        "title": "",
        "images": 0,
        "error": "",
    }

    title = build_title(state, listing_type)
    result["title"] = title
    tags = build_tags(state, listing_type)
    description = build_description(state, listing_type)
    images = build_images(state)
    result["images"] = len(images)

    name = display_name(state)
    orient = "H" if is_landscape(state) else "V"
    lt = "DIG" if listing_type == "digital" else "PRT"
    print(f"  {name} [{orient}] {lt} — {len(images)} imgs")

    # Verify images
    missing = [p for p in images if not p.exists()]
    if missing:
        result["status"] = "missing_images"
        result["error"] = f"{len(missing)} missing"
        print(f"    SKIP — {len(missing)} missing images")
        for m in missing:
            print(f"      {m.name}")
        log_result(result)
        return result

    if not live:
        result["status"] = "dry_run"
        log_result(result)
        return result

    assert client is not None and shop_id is not None

    # Create draft
    price = 9.99 if listing_type == "digital" else 34.83
    etsy_type = "download" if listing_type == "digital" else "physical"

    try:
        kwargs: dict = {
            "shop_id": shop_id,
            "title": title,
            "description": description,
            "price": price,
            "quantity": 999,
            "tags": tags,
            "who_made": "i_did",
            "when_made": "made_to_order",
            "taxonomy_id": TAXONOMY_ID,
            "listing_type": etsy_type,
            "return_policy_id": RETURN_POLICY_ID,
            "shop_section_id": SECTION_CITY_MAPS,
            "readiness_state_id": READINESS_STATE_ID,
        }
        if listing_type == "print":
            kwargs["shipping_profile_id"] = SHIPPING_PROFILE_ID

        created = client.create_draft_listing(**kwargs)
        listing_id = created.get("listing_id")
        result["listing_id"] = str(listing_id)

    except EtsyApiError as e:
        result["status"] = "api_error"
        result["error"] = str(e)
        print(f"    ERROR creating draft: {e}")
        log_result(result)
        return result

    # Upload images
    for rank, img_path in enumerate(images, 1):
        try:
            client.upload_listing_image(shop_id, listing_id, str(img_path), rank=rank)
        except EtsyApiError as e:
            print(f"    img [{rank}] FAILED: {e}")

    result["status"] = "draft_created"
    print(f"    draft {listing_id}")
    log_result(result)
    return result


# ── Main ────────────────────────────────────────────────────────────

def get_all_states() -> list[str]:
    return sorted([
        d.name for d in ATLAS_DIR.iterdir()
        if d.is_dir() and (d / "mockups").is_dir()
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish AtlasMap per-state drafts.")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--state", help="Single state folder name.")
    parser.add_argument("--start-from", help="Start from this state alphabetically.")
    parser.add_argument("--type", choices=["digital", "print", "both"], default="both")
    args = parser.parse_args()

    live = args.live and not args.dry_run
    all_states = get_all_states()

    if args.state:
        states = [s for s in all_states if s == args.state]
        if not states:
            print(f"ERROR: {args.state} not found. Available: {all_states[:5]}...")
            return 2
    elif args.start_from:
        states = [s for s in all_states if s >= args.start_from]
    else:
        states = all_states

    types = ["digital", "print"] if args.type == "both" else [args.type]
    total = len(states) * len(types)

    print(f"{'LIVE' if live else 'DRY RUN'} — {len(states)} states × {len(types)} types = {total} listings\n")

    if live:
        client = EtsyClient()
        shop_id = client.get_shop_id()
        print(f"Shop ID: {shop_id}\n")
    else:
        client = None
        shop_id = None

    successes = 0
    failures = 0

    for i, state in enumerate(states, 1):
        print(f"[{i}/{len(states)}] {display_name(state)}")
        for lt in types:
            r = publish_state(client, shop_id, state, lt, live=live)
            if r["status"] in ("draft_created", "dry_run"):
                successes += 1
            else:
                failures += 1
            if live:
                time.sleep(1)  # rate limiting between API calls

    print(f"\nDone. successes={successes} failures={failures} total={total}")
    print(f"Log: {PUBLISH_LOG}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
