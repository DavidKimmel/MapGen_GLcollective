"""Compose 3 color mockups per city and upload to existing Etsy draft listings.

Mockup assignments:
  - black      -> Frame 9   (40Vintage — gold frame, concrete wall)
  - charcoal   -> Mockup79  (PSD Mockups — flat)
  - dusty_rose -> Mockup5   (PSD Mockups — flat)

Usage:
    python scripts/compose_and_upload_color_mockups.py --dry-run        # Preview
    python scripts/compose_and_upload_color_mockups.py                  # Compose + upload all
    python scripts/compose_and_upload_color_mockups.py --compose-only   # Just compose, no upload
    python scripts/compose_and_upload_color_mockups.py --upload-only    # Just upload existing mockups
    python scripts/compose_and_upload_color_mockups.py --city austin    # Single city
"""

from __future__ import annotations

import argparse
import csv
import gc
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from PIL import Image

from etsy.api_client import EtsyClient, EtsyApiError
from etsy.mockup_composer import compose_mockup, MockupDef, MockupSlot
from etsy.style_config import SHOP_ID

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

RENDERS_DIR = Path("etsy/renders")
PUBLISH_LOG = Path("etsy/monomap_publish_log.csv")

LIFESTYLE_DIR = Path(r"C:\MapGen_GLcollective\etsy\TUR2\40Vintage_Frame_Mockup_Bundle_Vertical_PSD_JPG")
PSD_DIR = Path(r"C:\MapGen_GLcollective\etsy\TUR2\PSD Mockups")

# ---------------------------------------------------------------------------
# Color -> mockup mapping
# ---------------------------------------------------------------------------

COLOR_MOCKUPS: dict[str, MockupDef] = {
    "black": MockupDef(
        filename=str(LIFESTYLE_DIR / "Frame 9.psd"),
        short_name="frame9",
        render_size="24x36",
        slots=[],
    ),
    "charcoal": MockupDef(
        filename=str(PSD_DIR / "Mockup79.psd"),
        short_name="mockup79",
        render_size="24x36",
        slots=[],
    ),
    "dusty_rose": MockupDef(
        filename=str(PSD_DIR / "Mockup5.psd"),
        short_name="mockup5",
        render_size="24x36",
        slots=[],
    ),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_listing_ids() -> dict[str, str]:
    """Load {slug: listing_id} from publish log."""
    ids: dict[str, str] = {}
    if not PUBLISH_LOG.exists():
        return ids
    with open(PUBLISH_LOG, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("listing_id") and row.get("status") == "draft_created":
                ids[row["city"]] = row["listing_id"]
    return ids


def get_monomap_slugs() -> list[str]:
    """Get sorted list of monomap city slugs."""
    slugs: list[str] = []
    for d in sorted(RENDERS_DIR.iterdir()):
        if d.is_dir() and d.name.endswith("_monomap"):
            slugs.append(d.name.replace("_monomap", ""))
    return slugs


def mockup_filename(slug: str, color: str) -> str:
    """Final mockup filename for a city + color."""
    return f"{slug}_{color}_mockup.jpg"


# ---------------------------------------------------------------------------
# Compose
# ---------------------------------------------------------------------------


def compose_city(slug: str) -> list[str]:
    """Compose 3 color mockups for a city. Returns list of output paths."""
    city_dir = RENDERS_DIR / f"{slug}_monomap"
    outputs: list[str] = []

    for color, mockup_def in COLOR_MOCKUPS.items():
        render_path = city_dir / f"{slug}_{color}_24x36.png"
        out_path = city_dir / mockup_filename(slug, color)

        if out_path.exists():
            print(f"    {color}: exists, skipping")
            outputs.append(str(out_path))
            continue

        if not render_path.exists():
            print(f"    {color}: NO RENDER, skipping")
            continue

        render_img = Image.open(str(render_path)).convert("RGBA")
        result = compose_mockup(mockup_def, f"{slug}_monomap", render_img)

        # Rename from composer default to our color-prefixed name
        expected = city_dir / f"{slug}_monomap_{mockup_def.short_name}.jpg"
        if expected.exists():
            os.rename(str(expected), str(out_path))
        elif result.exists():
            os.rename(str(result), str(out_path))

        print(f"    {color}: {out_path.name}")
        outputs.append(str(out_path))
        render_img.close()
        gc.collect()

    return outputs


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


def upload_city(client: EtsyClient, shop_id: int, slug: str,
                listing_id: str, start_rank: int = 11) -> int:
    """Upload 3 color mockups to an existing listing. Returns count uploaded."""
    city_dir = RENDERS_DIR / f"{slug}_monomap"
    uploaded = 0

    for i, color in enumerate(COLOR_MOCKUPS.keys()):
        img_path = city_dir / mockup_filename(slug, color)
        if not img_path.exists():
            print(f"    {color}: mockup missing, skipping")
            continue

        rank = start_rank + i
        try:
            client.upload_listing_image(
                shop_id, int(listing_id), str(img_path), rank=rank,
            )
            print(f"    [{rank}] {img_path.name}")
            uploaded += 1
        except EtsyApiError as e:
            print(f"    [{rank}] FAILED {img_path.name}: {e}")

    return uploaded


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Compose + upload color mockups")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--compose-only", action="store_true")
    parser.add_argument("--upload-only", action="store_true")
    parser.add_argument("--city", help="Single city slug")
    args = parser.parse_args()

    slugs = get_monomap_slugs()
    listing_ids = load_listing_ids()

    if args.city:
        if args.city not in slugs:
            print(f"City not found: {args.city}")
            sys.exit(1)
        slugs = [args.city]

    do_compose = not args.upload_only
    do_upload = not args.compose_only

    print(f"{'=' * 60}")
    print(f"  Color Mockups: {len(slugs)} cities x 3 colors")
    print(f"  Compose: {do_compose}  Upload: {do_upload}  Dry-run: {args.dry_run}")
    print(f"  Listing IDs loaded: {len(listing_ids)}")
    print(f"{'=' * 60}\n")

    compose_ok = 0
    upload_ok = 0
    t0 = time.time()

    client: EtsyClient | None = None
    if do_upload and not args.dry_run:
        client = EtsyClient()
        try:
            me = client.get_me()
            print(f"  Authenticated as: {me.get('login_name', 'unknown')}\n")
        except EtsyApiError as e:
            print(f"  AUTH ERROR: {e}")
            sys.exit(1)

    for i, slug in enumerate(slugs):
        lid = listing_ids.get(slug, "")
        print(f"[{i + 1}/{len(slugs)}] {slug} (listing: {lid or 'NONE'})")

        # Compose
        if do_compose:
            outputs = compose_city(slug)
            compose_ok += len(outputs)

        # Upload
        if do_upload and lid:
            if args.dry_run:
                for color in COLOR_MOCKUPS:
                    img = RENDERS_DIR / f"{slug}_monomap" / mockup_filename(slug, color)
                    exists = img.exists()
                    print(f"    [DRY] {color}: {'ready' if exists else 'MISSING'}")
            else:
                uploaded = upload_city(client, SHOP_ID, slug, lid)
                upload_ok += uploaded
        elif do_upload and not lid:
            print(f"    NO LISTING ID — skipping upload")

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"  Complete in {elapsed:.0f}s")
    if do_compose:
        print(f"  Mockups composed: {compose_ok}")
    if do_upload:
        print(f"  Images uploaded:  {upload_ok}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
