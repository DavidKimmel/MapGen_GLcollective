"""Batch upload AtlasMap renders to Dropbox.

Uploads all 5 poster sizes for each state to /GeoLine/ElevationMaps/{State}/

Usage:
    python scripts/batch_dropbox_upload_atlas.py
    python scripts/batch_dropbox_upload_atlas.py --state Alabama
    python scripts/batch_dropbox_upload_atlas.py --start-from Montana
    python scripts/batch_dropbox_upload_atlas.py --dry-run
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib import request, error

# Load .env
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

ATLAS_DIR = Path(r"C:\MapGen_GLcollective\etsy\renders\AtlasMap\print_ready")
DROPBOX_BASE = "/GeoLine/ElevationMaps"


def dropbox_upload(token: str, local_path: str, dropbox_path: str) -> bool:
    """Upload a file to Dropbox. Returns True on success."""
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
        resp = request.urlopen(req)
        return True
    except error.HTTPError as e:
        body = e.read().decode()
        if e.code == 401:
            print(f"\n  TOKEN EXPIRED — refresh and retry.")
            sys.exit(1)
        print(f"  FAILED ({e.code}): {body[:200]}")
        return False


def get_states() -> list[str]:
    """Return sorted list of state folder names."""
    return sorted([
        d.name for d in ATLAS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith("_") and d.name != "new_mockups"
        and d.name != "new_mockups_fill"
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload AtlasMap renders to Dropbox.")
    parser.add_argument("--state", help="Upload only this state.")
    parser.add_argument("--start-from", help="Skip states before this one alphabetically.")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without uploading.")
    args = parser.parse_args()

    token = os.getenv("DROPBOX_ACCESS_TOKEN")
    if not token and not args.dry_run:
        print("ERROR: DROPBOX_ACCESS_TOKEN not set in .env")
        return 1

    all_states = get_states()

    if args.state:
        if args.state not in all_states:
            print(f"ERROR: {args.state} not found in {ATLAS_DIR}")
            return 2
        states = [args.state]
    elif args.start_from:
        states = [s for s in all_states if s >= args.start_from]
    else:
        states = all_states

    # Count files
    total_files = 0
    for state in states:
        state_dir = ATLAS_DIR / state
        pngs = [f for f in state_dir.iterdir() if f.suffix == ".png"]
        total_files += len(pngs)

    print(f"Uploading {total_files} files for {len(states)} states")
    print(f"Destination: {DROPBOX_BASE}/{{State}}/")
    if args.dry_run:
        print("--- dry run ---")

    uploaded = 0
    failed = 0

    for i, state in enumerate(states, 1):
        state_dir = ATLAS_DIR / state
        pngs = sorted([f for f in state_dir.iterdir() if f.suffix == ".png"])

        if not pngs:
            print(f"[{i}/{len(states)}] {state}: no PNG files, skipping")
            continue

        print(f"[{i}/{len(states)}] {state} ({len(pngs)} files)")

        for png in pngs:
            remote = f"{DROPBOX_BASE}/{state}/{png.name}"
            if args.dry_run:
                print(f"    {png.name} -> {remote}")
                uploaded += 1
                continue

            ok = dropbox_upload(token, str(png), remote)
            if ok:
                uploaded += 1
                print(f"    {png.name} OK")
            else:
                failed += 1

            # Small delay to avoid rate limiting
            time.sleep(0.3)

    print(f"\nDone. uploaded={uploaded} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
