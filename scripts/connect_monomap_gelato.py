"""Connect MonoMap Etsy listings to Gelato products via API.

Reads gelato_import.csv from each {slug}_monomap/ folder and connects
all physical variants (unframed + framed) using the placeholder image.

Usage:
    python scripts/connect_monomap_gelato.py --dry-run
    python scripts/connect_monomap_gelato.py
    python scripts/connect_monomap_gelato.py --city austin
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from etsy.gelato_connect import (
    _load_api_key, gelato_api, get_gelato_products,
    parse_variant_title,
)
from etsy.style_config import GELATO_UIDS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RENDERS_DIR = PROJECT_ROOT / "etsy" / "renders"
PUBLISH_LOG = PROJECT_ROOT / "etsy" / "monomap_publish_log.csv"

# Coastal cities to skip (deleted from Etsy)
SKIP_SLUGS = {"copenhagen", "honolulu", "lisbon", "san_francisco", "seattle"}

PLACEHOLDER_URL = "https://geoline.neodigitalventures.com/_assets/placeholder.png"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_listing_ids() -> dict[str, str]:
    """Load {slug: listing_id} from publish log, excluding coastal skips."""
    ids: dict[str, str] = {}
    if not PUBLISH_LOG.exists():
        return ids
    with open(PUBLISH_LOG, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            slug = row.get("city", "")
            if row.get("status") == "draft_created" and slug not in SKIP_SLUGS:
                ids[slug] = row["listing_id"]
    return ids


def find_gelato_product_by_external_id(products: list[dict], listing_id: str) -> dict | None:
    """Find Gelato product by Etsy listing ID (externalId)."""
    for p in products:
        if str(p.get("externalId", "")) == str(listing_id):
            return p
    return None


# ---------------------------------------------------------------------------
# Connect
# ---------------------------------------------------------------------------


def connect_city(
    api_key: str,
    slug: str,
    listing_id: str,
    products: list[dict],
    dry_run: bool = False,
) -> tuple[int, int, int]:
    """Connect all physical variants for one city. Returns (connected, skipped, errors)."""
    product = find_gelato_product_by_external_id(products, listing_id)
    if not product:
        print(f"  NOT FOUND in Gelato (listing {listing_id})")
        return (0, 0, 1)

    product_id = product["id"]
    connected = 0
    skipped = 0
    errors = 0

    for v in product.get("variants", []):
        title = v.get("title", "")
        parsed = parse_variant_title(title)
        if not parsed:
            continue

        fmt, size = parsed

        # Skip digital variants — not connected to Gelato
        if "Digital" in fmt:
            skipped += 1
            continue

        # Already connected?
        if v.get("connectionStatus") == "connected":
            skipped += 1
            continue

        # Map Etsy format names to GELATO_UIDS keys
        fmt_key = {
            "Unframed Print": "unframed",
            "Framed - Black": "framed_black",
            "Framed - White": "framed_white",
            "Framed Black": "framed_black",
            "Framed White": "framed_white",
        }.get(fmt)
        uid = GELATO_UIDS.get(fmt_key, {}).get(size) if fmt_key else None
        if not uid:
            skipped += 1
            continue

        if dry_run:
            print(f"    [DRY] {title} -> {uid[:45]}...")
            connected += 1
            continue

        # Step 1: Set product UID
        gelato_api(api_key, "PATCH",
                   f"products/{product_id}/variants/{v['id']}",
                   {"productUid": uid})

        # Step 2: Upload print file (placeholder)
        result = gelato_api(api_key, "POST",
                            f"products/{product_id}/variants/{v['id']}/print-files",
                            {"type": "default", "fileUrl": PLACEHOLDER_URL})

        if "id" in result:
            # Step 3: Mark as connected
            gelato_api(api_key, "PATCH",
                       f"products/{product_id}/variants/{v['id']}",
                       {"connectionStatus": "connected"})
            connected += 1
        else:
            msg = result.get("message", str(result))
            print(f"    ERR {title}: {msg}")
            errors += 1

        time.sleep(0.1)

    return (connected, skipped, errors)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Connect MonoMap listings to Gelato")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--city", help="Single city slug")
    args = parser.parse_args()

    listing_ids = load_listing_ids()
    if not listing_ids:
        print("No listing IDs found.")
        sys.exit(1)

    if args.city:
        if args.city not in listing_ids:
            print(f"No listing ID for {args.city}")
            sys.exit(1)
        targets = {args.city: listing_ids[args.city]}
    else:
        targets = listing_ids

    api_key = _load_api_key()
    print("Fetching Gelato products...")
    products = get_gelato_products(api_key)
    print(f"Found {len(products)} products in store\n")

    mode = "DRY RUN" if args.dry_run else "LIVE"
    print(f"{'=' * 60}")
    print(f"  MonoMap Gelato Connect — {mode}")
    print(f"  Cities: {len(targets)}")
    print(f"  Placeholder: {PLACEHOLDER_URL[:50]}...")
    print(f"{'=' * 60}\n")

    total_connected = 0
    total_skipped = 0
    total_errors = 0
    t0 = time.time()

    for i, (slug, lid) in enumerate(sorted(targets.items()), 1):
        print(f"[{i}/{len(targets)}] {slug} (listing: {lid})")
        c, s, e = connect_city(api_key, slug, lid, products, dry_run=args.dry_run)
        print(f"  {c} connected, {s} skipped, {e} errors")
        total_connected += c
        total_skipped += s
        total_errors += e

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"  Complete in {elapsed:.0f}s")
    print(f"  Connected: {total_connected}")
    print(f"  Skipped:   {total_skipped}")
    print(f"  Errors:    {total_errors}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
