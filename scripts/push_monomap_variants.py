"""Push inventory variants (20 SKUs) to all MonoMap Etsy draft listings.

Each listing gets 20 variants:
  - 5 Digital Download   (GLC-MONO-DIG-{size})
  - 5 Unframed Print     (GLC-MONO-UNF-{size})
  - 5 Framed - Black     (GLC-MONO-FBK-{size})
  - 5 Framed - White     (GLC-MONO-FWH-{size})

Matches the same structure as Blueprint listings (property IDs 513/514).

Usage:
    python scripts/push_monomap_variants.py --dry-run         # Preview
    python scripts/push_monomap_variants.py                   # Push all 64
    python scripts/push_monomap_variants.py --city austin     # Single city
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from etsy.api_client import EtsyClient, EtsyApiError
from etsy.style_config import MONOMAP, READINESS_STATE_ID

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PUBLISH_LOG = PROJECT_ROOT / "etsy" / "monomap_publish_log.csv"

# Variant definitions: (format_name, size, price, sku_suffix)
VARIANTS: list[tuple[str, str, float, str]] = [
    # Digital (5)
    ("Digital Download", "8x10",  4.20,   "DIG-8X10"),
    ("Digital Download", "11x14", 5.04,   "DIG-11X14"),
    ("Digital Download", "16x20", 5.88,   "DIG-16X20"),
    ("Digital Download", "18x24", 6.72,   "DIG-18X24"),
    ("Digital Download", "24x36", 7.80,   "DIG-24X36"),
    # Unframed (5)
    ("Unframed Print",   "8x10",  34.83,  "UNF-8X10"),
    ("Unframed Print",   "11x14", 39.85,  "UNF-11X14"),
    ("Unframed Print",   "16x20", 46.35,  "UNF-16X20"),
    ("Unframed Print",   "18x24", 51.37,  "UNF-18X24"),
    ("Unframed Print",   "24x36", 62.45,  "UNF-24X36"),
    # Framed Black (5)
    ("Framed - Black",   "8x10",  78.07,  "FBK-8X10"),
    ("Framed - Black",   "11x14", 87.50,  "FBK-11X14"),
    ("Framed - Black",   "16x20", 119.62, "FBK-16X20"),
    ("Framed - Black",   "18x24", 131.12, "FBK-18X24"),
    ("Framed - Black",   "24x36", 216.17, "FBK-24X36"),
    # Framed White (5)
    ("Framed - White",   "8x10",  78.07,  "FWH-8X10"),
    ("Framed - White",   "11x14", 87.50,  "FWH-11X14"),
    ("Framed - White",   "16x20", 119.62, "FWH-16X20"),
    ("Framed - White",   "18x24", 131.12, "FWH-18X24"),
    ("Framed - White",   "24x36", 216.17, "FWH-24X36"),
]


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


def build_products() -> list[dict]:
    """Build the products list for update_listing_inventory."""
    products: list[dict] = []
    for fmt, size, price, sku_suffix in VARIANTS:
        products.append({
            "sku": f"GLC-MONO-{sku_suffix}",
            "property_values": [
                {"property_id": 513, "property_name": "Format", "values": [fmt]},
                {"property_id": 514, "property_name": "Size", "values": [size]},
            ],
            "offerings": [{
                "price": price,
                "quantity": 999,
                "is_enabled": True,
                "readiness_state_id": READINESS_STATE_ID,
            }],
        })
    return products


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Push MonoMap variants to Etsy drafts")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--city", help="Single city slug")
    args = parser.parse_args()

    listing_ids = load_listing_ids()
    if not listing_ids:
        print("No listing IDs found in publish log. Run publish_monomap_drafts.py first.")
        sys.exit(1)

    if args.city:
        if args.city not in listing_ids:
            print(f"No listing ID for {args.city}")
            sys.exit(1)
        targets = {args.city: listing_ids[args.city]}
    else:
        targets = listing_ids

    products = build_products()

    print(f"{'=' * 60}")
    print(f"  MonoMap Variant Push: {len(targets)} listings x {len(products)} variants")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"{'=' * 60}\n")

    if args.dry_run:
        print("Variants to create per listing:")
        for fmt, size, price, sku_suffix in VARIANTS:
            print(f"  GLC-MONO-{sku_suffix:10s} | {fmt:20s} | {size:5s} | ${price:.2f}")
        print(f"\nListings: {len(targets)}")
        return

    client = EtsyClient()
    try:
        me = client.get_me()
        print(f"Authenticated as: {me.get('login_name', 'unknown')}\n")
    except EtsyApiError as e:
        print(f"AUTH ERROR: {e}")
        sys.exit(1)

    ok = 0
    errors = 0
    t0 = time.time()

    for i, (slug, lid) in enumerate(sorted(targets.items()), 1):
        print(f"[{i}/{len(targets)}] {slug} (listing: {lid})...", end=" ", flush=True)
        try:
            client.update_listing_inventory(
                listing_id=int(lid),
                products=products,
                price_on_property=[513, 514],
                quantity_on_property=[513, 514],
                sku_on_property=[513, 514],
            )
            print("OK — 20 variants")
            ok += 1
        except EtsyApiError as e:
            print(f"ERROR: {e}")
            errors += 1
        time.sleep(0.3)

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"  Complete in {elapsed:.0f}s")
    print(f"  Success: {ok}  Errors: {errors}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
