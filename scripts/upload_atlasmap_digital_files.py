"""Upload delivery PDFs to AtlasMap digital draft listings on Etsy.

Reads listing IDs from atlasmap_publish_log.csv (digital only),
uploads each state's {State}_delivery.pdf as the auto-delivered file.

Usage:
    python -m scripts.upload_atlasmap_digital_files --dry-run
    python -m scripts.upload_atlasmap_digital_files --live
    python -m scripts.upload_atlasmap_digital_files --live --state Alabama
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from etsy.api_client import EtsyClient, EtsyApiError

ATLAS_DIR = Path(r"C:\MapGen_GLcollective\etsy\renders\AtlasMap\print_ready")
PUBLISH_LOG = Path(r"C:\MapGen_GLcollective\etsy\atlasmap_publish_log.csv")


def load_digital_listings() -> dict[str, int]:
    """Load {state: listing_id} for digital draft listings."""
    listings: dict[str, int] = {}
    with open(PUBLISH_LOG, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("type") == "digital" and row.get("status") == "draft_created":
                listings[row["state"]] = int(row["listing_id"])
    return listings


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload delivery PDFs to Etsy digital listings.")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--state", help="Single state.")
    args = parser.parse_args()

    live = args.live and not args.dry_run
    listings = load_digital_listings()

    if args.state:
        if args.state not in listings:
            print(f"ERROR: {args.state} not found in digital listings")
            return 2
        listings = {args.state: listings[args.state]}

    print(f"{'LIVE' if live else 'DRY RUN'} — {len(listings)} digital listings\n")

    if live:
        client = EtsyClient()
        shop_id = client.get_shop_id()
        print(f"Shop ID: {shop_id}\n")
    else:
        client = None
        shop_id = None

    ok = 0
    failed = 0

    for i, (state, listing_id) in enumerate(sorted(listings.items()), 1):
        pdf_path = ATLAS_DIR / state / f"{state}_delivery.pdf"

        if not pdf_path.exists():
            print(f"[{i}/{len(listings)}] {state} — MISSING {pdf_path.name}")
            failed += 1
            continue

        size_kb = pdf_path.stat().st_size // 1024
        print(f"[{i}/{len(listings)}] {state} (listing {listing_id}) — {pdf_path.name} ({size_kb}KB)", end="")

        if not live:
            print(" [dry-run]")
            ok += 1
            continue

        try:
            client.upload_listing_file(
                shop_id, listing_id, str(pdf_path),
                name=f"{state} Topographic Map - All Sizes",
            )
            print(" OK")
            ok += 1
        except EtsyApiError as e:
            print(f" FAILED: {e}")
            failed += 1

        time.sleep(0.5)

    print(f"\nDone. ok={ok} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
