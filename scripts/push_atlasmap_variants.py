"""Push size variants to all AtlasMap Etsy draft listings.

Reads listing IDs from atlasmap_publish_log.csv and adds size variants
with correct pricing.

Digital: 5 sizes × $9.99 flat
Print:   5 sizes × tiered per PricingMaster.txt

Usage:
    python -m scripts.push_atlasmap_variants --dry-run
    python -m scripts.push_atlasmap_variants --live
    python -m scripts.push_atlasmap_variants --live --state Colorado
    python -m scripts.push_atlasmap_variants --live --type print
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from etsy.api_client import EtsyClient, EtsyApiError
from etsy.style_config import READINESS_STATE_ID

PUBLISH_LOG = Path(r"C:\MapGen_GLcollective\etsy\atlasmap_publish_log.csv")

# Size property_id = 514 on Etsy
SIZE_PROPERTY_ID = 514

# ── Digital variants (all $9.99) ────────────────────────────────────
DIGITAL_VARIANTS: list[tuple[str, float, str]] = [
    # (size_label, price, sku_suffix)
    ("8x10",  9.99, "DIG-SM"),
    ("11x14", 9.99, "DIG-MD"),
    ("16x20", 9.99, "DIG-LG"),
    ("18x24", 9.99, "DIG-XL"),
    ("24x36", 9.99, "DIG-PS"),
]

# ── Print variants (PricingMaster.txt prices) ───────────────────────
PRINT_VARIANTS: list[tuple[str, float, str]] = [
    ("8x10",  22.51, "PRT-SM"),
    ("11x14", 25.40, "PRT-MD"),
    ("16x20", 30.76, "PRT-LG"),
    ("18x24", 33.80, "PRT-XL"),
    ("24x36", 49.73, "PRT-PS"),
]


def build_products(listing_type: str, state_slug: str) -> list[dict]:
    """Build the Etsy inventory products list."""
    variants = DIGITAL_VARIANTS if listing_type == "digital" else PRINT_VARIANTS
    products: list[dict] = []
    for size, price, sku_suffix in variants:
        products.append({
            "sku": f"GLC-ATLAS-{state_slug.upper()}-{sku_suffix}",
            "property_values": [
                {
                    "property_id": SIZE_PROPERTY_ID,
                    "property_name": "Size",
                    "values": [size],
                },
            ],
            "offerings": [{
                "price": price,
                "quantity": 999,
                "is_enabled": True,
                "readiness_state_id": READINESS_STATE_ID,
            }],
        })
    return products


def load_listings() -> list[dict]:
    """Load draft_created entries from publish log."""
    entries: list[dict] = []
    if not PUBLISH_LOG.exists():
        return entries
    with open(PUBLISH_LOG, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("status") == "draft_created" and row.get("listing_id"):
                entries.append(row)
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Push AtlasMap size variants to Etsy drafts.")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--state", help="Single state folder name.")
    parser.add_argument("--type", choices=["digital", "print", "both"], default="both")
    args = parser.parse_args()

    live = args.live and not args.dry_run
    entries = load_listings()

    if not entries:
        print(f"No draft listings found in {PUBLISH_LOG}")
        return 1

    # Filter
    if args.state:
        entries = [e for e in entries if e["state"] == args.state]
    if args.type != "both":
        entries = [e for e in entries if e["type"] == args.type]

    print(f"{'LIVE' if live else 'DRY RUN'} — {len(entries)} listings to update\n")

    if args.dry_run or not live:
        print("Digital variants:")
        for size, price, sku in DIGITAL_VARIANTS:
            print(f"  {sku:15s} | {size:5s} | ${price:.2f}")
        print("\nPrint variants:")
        for size, price, sku in PRINT_VARIANTS:
            print(f"  {sku:15s} | {size:5s} | ${price:.2f}")
        print(f"\nWould update {len(entries)} listings.")
        return 0

    client = EtsyClient()
    print(f"Authenticated.\n")

    ok = 0
    errors = 0

    for i, entry in enumerate(sorted(entries, key=lambda e: e["state"]), 1):
        state = entry["state"]
        lt = entry["type"]
        lid = int(entry["listing_id"])
        state_slug = state.lower().replace(" ", "_")

        products = build_products(lt, state_slug)
        num_variants = len(products)

        print(f"[{i}/{len(entries)}] {state} ({lt}) listing {lid}...", end=" ", flush=True)
        try:
            client.update_listing_inventory(
                listing_id=lid,
                products=products,
                price_on_property=[SIZE_PROPERTY_ID],
                quantity_on_property=[SIZE_PROPERTY_ID],
                sku_on_property=[SIZE_PROPERTY_ID],
            )
            print(f"OK — {num_variants} variants")
            ok += 1
        except EtsyApiError as e:
            print(f"ERROR: {e}")
            errors += 1
        time.sleep(0.3)

    print(f"\nDone. ok={ok} errors={errors} total={len(entries)}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
