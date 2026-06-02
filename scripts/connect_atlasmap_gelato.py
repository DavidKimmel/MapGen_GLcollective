"""Connect AtlasMap Etsy print listings to Gelato products via API.

For each (state, size) variant on each print listing:
  1. PATCH productUid (orientation-aware: portrait -> _ver, landscape -> _hor)
  2. POST print-file with the state-and-size-specific Dropbox URL
  3. PATCH connectionStatus=connected

Reads:
  - etsy/atlasmap_publish_log.csv     (state -> listing_id, print rows only)
  - etsy/atlasmap_dropbox_links.json  (state -> {orientation, links{size:url}})

Skips:
  - Digital listings (no Gelato connection)
  - Variants already in connectionStatus=connected

Usage:
    python scripts/connect_atlasmap_gelato.py --dry-run
    python scripts/connect_atlasmap_gelato.py --state Maryland
    python scripts/connect_atlasmap_gelato.py            # all 48 synced states
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from etsy.gelato_connect import (
    _load_api_key,
    gelato_api,
    get_gelato_products,
)
from etsy.style_config import GELATO_UIDS

VALID_SIZES = {"8x10", "11x14", "16x20", "18x24", "24x36"}


def extract_size(variant_title: str) -> str | None:
    """AtlasMap prints have single-axis variants: 'Size 8x10'."""
    t = variant_title.strip()
    if t.startswith("Size "):
        size = t[5:].strip()
        if size in VALID_SIZES:
            return size
    return None

PUBLISH_LOG = PROJECT_ROOT / "etsy" / "atlasmap_publish_log.csv"
MANIFEST_PATH = PROJECT_ROOT / "etsy" / "atlasmap_dropbox_links.json"


def load_print_listings() -> dict[str, str]:
    """Return {state: listing_id} for print listings only."""
    ids: dict[str, str] = {}
    with open(PUBLISH_LOG, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (
                row.get("status") == "draft_created"
                and row.get("type") == "print"
                and row.get("listing_id")
            ):
                ids[row["state"]] = row["listing_id"]
    return ids


def load_manifest() -> dict[str, dict]:
    if not MANIFEST_PATH.exists():
        raise SystemExit(
            f"Manifest not found: {MANIFEST_PATH}\n"
            f"Run: python scripts/build_atlasmap_dropbox_manifest.py"
        )
    return json.loads(MANIFEST_PATH.read_text())


def find_gelato_product(products: list[dict], listing_id: str) -> dict | None:
    for p in products:
        if str(p.get("externalId", "")) == str(listing_id):
            return p
    return None


def uid_for(orientation: str, size: str) -> str | None:
    key = "unframed_hor" if orientation == "landscape" else "unframed"
    return GELATO_UIDS.get(key, {}).get(size)


def connect_state(
    api_key: str,
    state: str,
    listing_id: str,
    products: list[dict],
    manifest_entry: dict,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Connect every Unframed Print variant for one state. Returns (connected, skipped, errors)."""
    product = find_gelato_product(products, listing_id)
    if not product:
        print(f"  {state}: NOT IN GELATO (listing {listing_id}) — needs manual sync")
        return (0, 0, 1)

    product_id = product["id"]
    orientation = manifest_entry["orientation"]
    links: dict[str, str] = manifest_entry["links"]

    connected = 0
    skipped = 0
    errors = 0

    for v in product.get("variants", []):
        size = extract_size(v.get("title", ""))
        if not size:
            skipped += 1
            continue

        if v.get("connectionStatus") == "connected":
            skipped += 1
            continue

        uid = uid_for(orientation, size)
        if not uid:
            print(f"    {state} {size}: no UID for orientation={orientation}")
            errors += 1
            continue

        file_url = links.get(size)
        if not file_url:
            print(f"    {state} {size}: no Dropbox link in manifest")
            errors += 1
            continue

        if dry_run:
            print(f"    [dry] {state} {size} ({orientation}) -> {uid[-20:]} / {file_url[-30:]}")
            connected += 1
            continue

        # Step 1: set productUid (idempotent — Gelato accepts re-PATCH)
        if v.get("productUid") != uid:
            gelato_api(
                api_key, "PATCH",
                f"products/{product_id}/variants/{v['id']}",
                {"productUid": uid},
            )

        # Step 2: upload print file. Gelato often 504s on large files even though
        # the upload itself succeeds — we recover by checking fileUrl after.
        post_failed = False
        try:
            gelato_api(
                api_key, "POST",
                f"products/{product_id}/variants/{v['id']}/print-files",
                {"type": "default", "fileUrl": file_url},
            )
        except RuntimeError as e:
            if "504" in str(e) or "JSON" in str(e):
                post_failed = True
                time.sleep(8)  # let Gelato finish processing
            else:
                raise

        # Step 3: verify fileUrl is set, then mark connected. Re-fetch detail if
        # we hit a 504 above or if fileUrl wasn't on the cached variant.
        cached_file = v.get("fileUrl")
        if post_failed or not cached_file:
            detail = gelato_api(api_key, "GET",
                                f"products/{product_id}/variants/{v['id']}")
            cached_file = detail.get("fileUrl") if isinstance(detail, dict) else None

        if cached_file:
            gelato_api(
                api_key, "PATCH",
                f"products/{product_id}/variants/{v['id']}",
                {"connectionStatus": "connected"},
            )
            connected += 1
            print(f"    OK {state} {size} ({orientation}){' [recovered from 504]' if post_failed else ''}")
        else:
            print(f"    ERR {state} {size}: file upload did not land")
            errors += 1

        time.sleep(0.1)

    return (connected, skipped, errors)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--state", help="Single state.")
    parser.add_argument("--skip", action="append", default=[],
                        help="Skip these states (repeatable). Default skips none.")
    args = parser.parse_args()

    listings = load_print_listings()
    manifest = load_manifest()

    if args.state:
        if args.state not in listings:
            print(f"No listing ID for state '{args.state}'")
            return 1
        if args.state not in manifest:
            print(f"No manifest entry for state '{args.state}' — build the manifest first.")
            return 1
        targets = {args.state: listings[args.state]}
    else:
        targets = {s: lid for s, lid in listings.items()
                   if s in manifest and s not in args.skip}
        missing_from_manifest = sorted(set(listings) - set(manifest))
        if missing_from_manifest:
            print(f"NOTE: {len(missing_from_manifest)} states not in manifest, skipping: {missing_from_manifest}")

    api_key = _load_api_key()
    print("Fetching Gelato products...")
    products = get_gelato_products(api_key)
    print(f"Gelato store has {len(products)} products\n")

    mode = "DRY RUN" if args.dry_run else "LIVE"
    print("=" * 60)
    print(f"  AtlasMap Gelato Connect — {mode}")
    print(f"  States: {len(targets)}")
    print("=" * 60 + "\n")

    total_c = total_s = total_e = 0
    t0 = time.time()

    for i, (state, lid) in enumerate(sorted(targets.items()), 1):
        print(f"[{i}/{len(targets)}] {state} (listing {lid})")
        c, s, e = connect_state(api_key, state, lid, products, manifest[state], args.dry_run)
        print(f"  {c} connected, {s} skipped, {e} errors")
        total_c += c
        total_s += s
        total_e += e

    elapsed = time.time() - t0
    print("\n" + "=" * 60)
    print(f"  Complete in {elapsed:.0f}s")
    print(f"  Connected: {total_c}")
    print(f"  Skipped:   {total_s}")
    print(f"  Errors:    {total_e}")
    print("=" * 60)
    return 0 if total_e == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
