"""Batch upload city renders to Dropbox.

Uploads all 5 poster sizes for each city to /GeoLine/{city_slug}/

Usage:
    python batch_dropbox_upload.py
    python batch_dropbox_upload.py --start-from "Paris"
"""

import argparse
import json
import os
import sys
import time
from urllib import request, error

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Read .env manually
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

RENDERS_DIR = os.path.join("etsy", "renders")
DROPBOX_BASE = "/GeoLine"
SIZES = ["8x10", "11x14", "16x20", "18x24", "24x36"]


def dropbox_upload(token, local_path, dropbox_path):
    """Upload a file to Dropbox."""
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

    with request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_cities_to_upload():
    """Get cities that have all 5 sizes rendered."""
    cities = []
    for slug in sorted(os.listdir(RENDERS_DIR)):
        city_dir = os.path.join(RENDERS_DIR, slug)
        if not os.path.isdir(city_dir):
            continue
        # Skip non-city dirs
        if slug in ("CustomMap1", "DateMap"):
            continue
        # Check all 5 sizes exist
        all_sizes = all(
            os.path.exists(os.path.join(city_dir, f"{slug}_{size}.png"))
            for size in SIZES
        )
        if all_sizes:
            cities.append(slug)
    return cities


def main():
    parser = argparse.ArgumentParser(description="Upload city renders to Dropbox")
    parser.add_argument("--start-from", default=None, help="Resume from city slug")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    args = parser.parse_args()

    token = os.getenv("DROPBOX_ACCESS_TOKEN")
    if not token and not args.dry_run:
        print("ERROR: DROPBOX_ACCESS_TOKEN not set in .env")
        sys.exit(1)

    cities = get_cities_to_upload()

    if args.start_from:
        start = args.start_from.lower().replace(" ", "_")
        try:
            idx = cities.index(start)
            cities = cities[idx:]
        except ValueError:
            print(f"City '{args.start_from}' not found")
            sys.exit(1)

    total_files = len(cities) * len(SIZES)
    print(f"\nDropbox Upload — {len(cities)} cities x {len(SIZES)} sizes = {total_files} files")
    print(f"Destination: {DROPBOX_BASE}/{{city_slug}}/\n")

    if args.dry_run:
        for slug in cities:
            print(f"  {slug}/")
            for size in SIZES:
                print(f"    {slug}_{size}.png -> {DROPBOX_BASE}/{slug}/{slug}_{size}.png")
        print(f"\n(dry run — {total_files} files would be uploaded)")
        return

    uploaded = 0
    errors = 0
    for i, slug in enumerate(cities, 1):
        print(f"\n[{i}/{len(cities)}] {slug}")
        for size in SIZES:
            local = os.path.join(RENDERS_DIR, slug, f"{slug}_{size}.png")
            remote = f"{DROPBOX_BASE}/{slug}/{slug}_{size}.png"
            mb = os.path.getsize(local) / 1e6
            print(f"  {size} ({mb:.1f} MB)...", end=" ", flush=True)
            try:
                dropbox_upload(token, local, remote)
                print("OK")
                uploaded += 1
            except Exception as e:
                print(f"ERROR: {e}")
                errors += 1

    print(f"\n{'='*60}")
    print(f"Done! {uploaded} uploaded, {errors} errors")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
