"""GeoLine Collective — Custom Map Order Fulfillment.

End-to-end fulfillment for custom map orders:
1. Render the custom map from customer specifications
2. Upload to Dropbox
3. Get a shareable direct-download link
4. Push the print file to Gelato for the pending order

Usage:
    python -m etsy.custom_fulfill \
        --order-id ORD-12345 \
        --location "Portland, Oregon" \
        --size 16x20 \
        --theme midnight_blue \
        --font 2 \
        --crop circle \
        --pin-lat 45.5152 --pin-lon -122.6784 \
        --pin-style 4 \
        --line1 "Our First Home" \
        --line2 "Portland, Oregon" \
        --line3 "Est. 2024"

    # Dry run (preview without API calls):
    python -m etsy.custom_fulfill --order-id ORD-12345 --location "Portland" --size 16x20 --dry-run

    # Skip rendering (file already exists):
    python -m etsy.custom_fulfill --order-id ORD-12345 --size 16x20 --skip-render

    # Render only (no upload/Gelato):
    python -m etsy.custom_fulfill --order-id ORD-12345 --location "Portland" --size 16x20 --render-only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib import request, error

from engine.renderer import render_poster
from etsy.gelato_connect import (
    gelato_api,
    _load_api_key,
    get_gelato_products,
    STORE_ID,
)
from etsy.generate_gelato_csvs import (
    get_or_create_shared_link,
    product_uid_unframed,
    SIZES,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_DIR = Path(__file__).parent.parent
CUSTOM_OUTPUT_DIR = PROJECT_DIR / "posters" / "custom"
DROPBOX_CUSTOM_PATH = "/GeoLine/custom"

# The custom listing title in Etsy/Gelato (used to find the product)
CUSTOM_PRODUCT_TITLE = "Custom Map Print"


# ---------------------------------------------------------------------------
# CustomOrder dataclass
# ---------------------------------------------------------------------------

@dataclass
class CustomOrder:
    """All parameters needed to fulfill a custom map order."""
    order_id: str
    location: str = ""
    size: str = "16x20"
    theme: str = "37th_parallel"
    font_preset: int = 1
    crop: str = "full"
    pin_lat: float | None = None
    pin_lon: float | None = None
    pin_style: int = 1
    pin_color: str | None = None
    text_line_1: str | None = None
    text_line_2: str | None = None
    text_line_3: str | None = None
    border: bool = False
    map_only: bool = False
    distance: int | None = None


# ---------------------------------------------------------------------------
# Env helpers
# ---------------------------------------------------------------------------

def _load_env_var(key: str) -> str:
    """Load a variable from .env file."""
    env_path = PROJECT_DIR / ".env"
    if not env_path.exists():
        print(f"ERROR: .env file not found. Add {key} to .env")
        sys.exit(1)
    for line in env_path.read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    print(f"ERROR: {key} not found in .env")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Step 1: Render
# ---------------------------------------------------------------------------

def render_custom_map(order: CustomOrder) -> str:
    """Render the custom map and return the output file path."""
    CUSTOM_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = str(CUSTOM_OUTPUT_DIR / f"{order.order_id}_{order.size}.png")

    print(f"\n{'='*60}")
    print(f"STEP 1: Rendering custom map")
    print(f"{'='*60}")
    print(f"  Order:    {order.order_id}")
    print(f"  Location: {order.location}")
    print(f"  Size:     {order.size}")
    print(f"  Theme:    {order.theme}")
    print(f"  Font:     {order.font_preset}")
    print(f"  Crop:     {order.crop}")
    if order.text_line_1:
        print(f"  Line 1:   {order.text_line_1}")
    if order.text_line_2:
        print(f"  Line 2:   {order.text_line_2}")
    if order.text_line_3:
        print(f"  Line 3:   {order.text_line_3}")
    if order.pin_lat and order.pin_lon:
        print(f"  Pin:      style {order.pin_style} at ({order.pin_lat}, {order.pin_lon})")
    print()

    render_poster(
        location=order.location,
        theme=order.theme,
        size=order.size,
        crop=order.crop,
        detail_layers=False,
        distance=order.distance,
        pin_lat=order.pin_lat,
        pin_lon=order.pin_lon,
        pin_style=order.pin_style,
        pin_color=order.pin_color,
        font_preset=order.font_preset,
        text_line_1=order.text_line_1,
        text_line_2=order.text_line_2,
        text_line_3=order.text_line_3,
        dpi=300,
        output_path=output_path,
        border=order.border,
        map_only=order.map_only,
    )

    return output_path


# ---------------------------------------------------------------------------
# Step 2: Upload to Dropbox
# ---------------------------------------------------------------------------

def dropbox_upload_file(token: str, local_path: str, dropbox_path: str) -> dict:
    """Upload a file to Dropbox via the content API."""
    url = "https://content.dropboxapi.com/2/files/upload"
    api_arg = json.dumps({
        "path": dropbox_path,
        "mode": "overwrite",
        "autorename": False,
        "mute": True,
    })

    with open(local_path, "rb") as f:
        file_data = f.read()

    req = request.Request(url, data=file_data, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
        "Dropbox-API-Arg": api_arg,
    })

    try:
        with request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise RuntimeError(f"Dropbox upload error {e.code}: {body}") from e


def upload_to_dropbox(token: str, local_path: str, order_id: str,
                      size: str) -> str:
    """Upload rendered file to Dropbox and return direct download URL."""
    filename = f"{order_id}_{size}.png"
    dropbox_path = f"{DROPBOX_CUSTOM_PATH}/{filename}"

    print(f"\n{'='*60}")
    print(f"STEP 2: Uploading to Dropbox")
    print(f"{'='*60}")

    file_size_mb = os.path.getsize(local_path) / 1e6
    print(f"  File: {local_path} ({file_size_mb:.1f} MB)")
    print(f"  Dest: {dropbox_path}")
    print(f"  Uploading...", end=" ", flush=True)

    dropbox_upload_file(token, local_path, dropbox_path)
    print("OK")

    print(f"  Getting shared link...", end=" ", flush=True)
    dl_url = get_or_create_shared_link(token, dropbox_path)
    print("OK")
    print(f"  URL: {dl_url}")

    return dl_url


# ---------------------------------------------------------------------------
# Step 3: Push to Gelato
# ---------------------------------------------------------------------------

def find_custom_product(products: list[dict]) -> dict | None:
    """Find the custom map product in Gelato by title."""
    for p in products:
        title = p.get("title", "")
        if CUSTOM_PRODUCT_TITLE.lower() in title.lower():
            return p
    return None


def push_to_gelato(api_key: str, file_url: str, size: str,
                   dry_run: bool = False) -> bool:
    """Push the print file to the custom map product variant in Gelato.

    Uses the 3-step ecommerce API flow:
    1. PATCH variant with productUid
    2. POST print-file with fileUrl
    3. PATCH variant with connectionStatus = connected
    """
    print(f"\n{'='*60}")
    print(f"STEP 3: Pushing to Gelato")
    print(f"{'='*60}")

    print(f"  Fetching products...", end=" ", flush=True)
    products = get_gelato_products(api_key)
    print(f"found {len(products)}")

    product = find_custom_product(products)
    if not product:
        print(f"  ERROR: Custom map product not found in Gelato!")
        print(f"  Looking for title containing: '{CUSTOM_PRODUCT_TITLE}'")
        print(f"  Available products:")
        for p in products:
            print(f"    - {p.get('title', 'untitled')}")
        return False

    product_id = product["id"]
    print(f"  Product: {product['title'][:60]}...")
    print(f"  Product ID: {product_id}")

    # Find the matching variant (Unframed Print + size)
    target_title = f"Format Unframed Print, Size {size}"
    target_variant = None
    for v in product.get("variants", []):
        if v["title"] == target_title:
            target_variant = v
            break

    if not target_variant:
        print(f"  ERROR: Variant not found: '{target_title}'")
        print(f"  Available variants:")
        for v in product.get("variants", []):
            print(f"    - {v['title']} (status: {v.get('connectionStatus', '?')})")
        return False

    variant_id = target_variant["id"]
    uid = product_uid_unframed(size)
    print(f"  Variant: {target_title}")
    print(f"  Variant ID: {variant_id}")
    print(f"  Product UID: {uid}")
    print(f"  File URL: {file_url[:80]}...")

    if dry_run:
        print(f"\n  [DRY RUN] Would connect variant with:")
        print(f"    1. PATCH productUid = {uid}")
        print(f"    2. POST print-file = {file_url[:60]}...")
        print(f"    3. PATCH connectionStatus = connected")
        return True

    # Step 1: Set product UID
    print(f"  [1/3] Setting productUid...", end=" ", flush=True)
    gelato_api(api_key, "PATCH",
               f"products/{product_id}/variants/{variant_id}",
               {"productUid": uid})
    print("OK")

    # Step 2: Upload print file
    print(f"  [2/3] Uploading print file...", end=" ", flush=True)
    result = gelato_api(api_key, "POST",
                        f"products/{product_id}/variants/{variant_id}/print-files",
                        {"type": "default", "fileUrl": file_url})
    if "id" in result:
        size_mb = result.get("fileSize", 0) / 1e6
        print(f"OK ({size_mb:.1f} MB)")
    else:
        msg = result.get("message", str(result))
        print(f"ERROR: {msg}")
        return False

    # Step 3: Mark as connected
    print(f"  [3/3] Setting connectionStatus...", end=" ", flush=True)
    gelato_api(api_key, "PATCH",
               f"products/{product_id}/variants/{variant_id}",
               {"connectionStatus": "connected"})
    print("OK")

    print(f"\n  Variant connected successfully!")
    return True


# ---------------------------------------------------------------------------
# Main fulfillment flow
# ---------------------------------------------------------------------------

def fulfill_order(order: CustomOrder, dry_run: bool = False,
                  skip_render: bool = False, render_only: bool = False) -> None:
    """Run the full custom order fulfillment pipeline."""
    print(f"\n{'#'*60}")
    print(f"  CUSTOM MAP FULFILLMENT — {order.order_id}")
    print(f"{'#'*60}")

    # --- Render ---
    if skip_render:
        output_path = str(CUSTOM_OUTPUT_DIR / f"{order.order_id}_{order.size}.png")
        if not os.path.exists(output_path):
            print(f"ERROR: --skip-render but file not found: {output_path}")
            sys.exit(1)
        print(f"\nSkipping render — using existing file: {output_path}")
    else:
        if not order.location:
            print("ERROR: --location is required for rendering")
            sys.exit(1)
        if dry_run:
            output_path = str(CUSTOM_OUTPUT_DIR / f"{order.order_id}_{order.size}.png")
            print(f"\n[DRY RUN] Would render: {output_path}")
        else:
            output_path = render_custom_map(order)

    if render_only:
        print(f"\n{'='*60}")
        print(f"Render complete! File: {output_path}")
        print(f"Run without --render-only to upload and connect to Gelato.")
        return

    # --- Upload to Dropbox ---
    dropbox_token = _load_env_var("DROPBOX_ACCESS_TOKEN")

    if dry_run:
        dropbox_path = f"{DROPBOX_CUSTOM_PATH}/{order.order_id}_{order.size}.png"
        print(f"\n[DRY RUN] Would upload to Dropbox: {dropbox_path}")
        file_url = f"https://www.dropbox.com/placeholder/{order.order_id}?dl=1"
    else:
        file_url = upload_to_dropbox(
            dropbox_token, output_path, order.order_id, order.size)

    # --- Push to Gelato ---
    gelato_key = _load_api_key()
    success = push_to_gelato(gelato_key, file_url, order.size, dry_run=dry_run)

    # --- Summary ---
    print(f"\n{'#'*60}")
    if dry_run:
        print(f"  DRY RUN COMPLETE — no changes made")
    elif success:
        print(f"  FULFILLMENT COMPLETE — {order.order_id}")
        print(f"  File: {output_path}")
        print(f"  Dropbox: {file_url}")
        print(f"  Gelato: Variant connected for {order.size}")
        print(f"\n  Next: Approve the order in Gelato dashboard")
    else:
        print(f"  FULFILLMENT FAILED — check errors above")
    print(f"{'#'*60}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fulfill a custom map order: render → Dropbox → Gelato")

    # Required
    parser.add_argument("--order-id", required=True,
                        help="Order identifier (for file naming and tracking)")
    parser.add_argument("--location",
                        help="City name or lat,lon (e.g., 'Portland, Oregon' or '45.5,-122.6')")
    parser.add_argument("--size", default="16x20", choices=SIZES,
                        help="Print size (default: 16x20)")

    # Map styling
    parser.add_argument("--theme", default="37th_parallel",
                        help="Theme name (default: 37th_parallel)")
    parser.add_argument("--font", type=int, default=1, choices=[1, 2, 3, 4, 5],
                        help="Font preset 1-5 (default: 1)")
    parser.add_argument("--crop", default="full", choices=["full", "circle"],
                        help="Crop shape (default: full)")
    parser.add_argument("--distance", type=int, default=None,
                        help="Map radius in meters (auto if not set)")

    # Pin
    parser.add_argument("--pin-lat", type=float, help="Pin latitude")
    parser.add_argument("--pin-lon", type=float, help="Pin longitude")
    parser.add_argument("--pin-style", type=int, default=1, choices=[1, 2, 3, 4, 5],
                        help="Pin style: 1=heart 2=heart-pin 3=classic 4=house 5=grad-cap")
    parser.add_argument("--pin-color", help="Pin hex color (default: theme default)")

    # Text
    parser.add_argument("--line1", help="Large title text")
    parser.add_argument("--line2", help="Medium subtitle text")
    parser.add_argument("--line3", help="Small detail text")

    # Options
    parser.add_argument("--border", action="store_true", help="Add border")
    parser.add_argument("--map-only", action="store_true", help="Skip text (clean map)")

    # Workflow control
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview all steps without executing")
    parser.add_argument("--skip-render", action="store_true",
                        help="Skip rendering (use existing file)")
    parser.add_argument("--render-only", action="store_true",
                        help="Only render, don't upload or connect")

    args = parser.parse_args()

    order = CustomOrder(
        order_id=args.order_id,
        location=args.location or "",
        size=args.size,
        theme=args.theme,
        font_preset=args.font,
        crop=args.crop,
        distance=args.distance,
        pin_lat=args.pin_lat,
        pin_lon=args.pin_lon,
        pin_style=args.pin_style,
        pin_color=args.pin_color,
        text_line_1=args.line1,
        text_line_2=args.line2,
        text_line_3=args.line3,
        border=args.border,
        map_only=args.map_only,
    )

    fulfill_order(order, dry_run=args.dry_run,
                  skip_render=args.skip_render, render_only=args.render_only)


if __name__ == "__main__":
    main()
