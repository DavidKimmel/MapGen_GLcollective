"""GeoLine Collective — Cloudinary Upload for Poster Hosting.

Uploads rendered posters to Cloudinary so they have public URLs
for the Dynamic Mockups API.

Usage:
    python -m etsy.cloudinary_upload                    # Upload all rendered cities
    python -m etsy.cloudinary_upload --city Chicago     # Upload one city
    python -m etsy.cloudinary_upload --list             # List uploaded posters
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from PIL import Image

import cloudinary
import cloudinary.uploader
import cloudinary.api

from etsy.batch_etsy_render import RENDERS_DIR
from etsy.city_list import get_city

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Load from .env file if python-dotenv available, otherwise from env vars
def _load_env() -> None:
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())

_load_env()

CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")

# File tracking uploaded URLs
UPLOAD_MANIFEST = os.path.join(os.path.dirname(__file__), "cloudinary_manifest.json")


def _configure() -> None:
    """Configure Cloudinary SDK."""
    if not all([CLOUD_NAME, API_KEY, API_SECRET]):
        print("Missing Cloudinary credentials. Set in .env:")
        print("  CLOUDINARY_CLOUD_NAME=xxx")
        print("  CLOUDINARY_API_KEY=xxx")
        print("  CLOUDINARY_API_SECRET=xxx")
        sys.exit(1)
    cloudinary.config(
        cloud_name=CLOUD_NAME,
        api_key=API_KEY,
        api_secret=API_SECRET,
        secure=True,
    )


# ---------------------------------------------------------------------------
# Manifest (tracks uploaded URLs so we don't re-upload)
# ---------------------------------------------------------------------------

def load_manifest() -> dict[str, str]:
    """Load upload manifest: {city_slug: secure_url}."""
    if os.path.exists(UPLOAD_MANIFEST):
        with open(UPLOAD_MANIFEST) as f:
            return json.load(f)
    return {}


def save_manifest(manifest: dict[str, str]) -> None:
    """Save upload manifest."""
    with open(UPLOAD_MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def upload_poster(city_slug: str, force: bool = False) -> str | None:
    """Upload a city's hero poster to Cloudinary.

    Returns the public URL, or None on failure.
    """
    manifest = load_manifest()

    # Skip if already uploaded (unless force)
    if city_slug in manifest and not force:
        url = manifest[city_slug]
        print(f"  {city_slug}: already uploaded -> {url[:80]}...")
        return url

    poster_path = os.path.join(
        RENDERS_DIR, city_slug, f"{city_slug}_16x20.png"
    )
    if not os.path.exists(poster_path):
        print(f"  {city_slug}: no poster found at {poster_path}")
        return None

    size_mb = os.path.getsize(poster_path) / 1e6

    # Cloudinary free tier limit is 10 MB — convert large PNGs to JPEG
    MAX_SIZE_BYTES = 10_000_000
    upload_path = poster_path
    tmp_jpg: str | None = None

    if os.path.getsize(poster_path) > MAX_SIZE_BYTES:
        tmp_fd, tmp_jpg = tempfile.mkstemp(suffix=".jpg")
        os.close(tmp_fd)
        img = Image.open(poster_path)
        if img.mode == "RGBA":
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        img.save(tmp_jpg, "JPEG", quality=85)
        upload_path = tmp_jpg
        jpg_mb = os.path.getsize(tmp_jpg) / 1e6
        print(f"  {city_slug}: PNG {size_mb:.1f} MB -> JPEG {jpg_mb:.1f} MB, uploading...", end="", flush=True)
    else:
        print(f"  {city_slug}: uploading ({size_mb:.1f} MB)...", end="", flush=True)

    try:
        result = cloudinary.uploader.upload(
            upload_path,
            public_id=f"geoline/{city_slug}_16x20",
            resource_type="image",
            overwrite=True,
            invalidate=True,
        )
        url = result["secure_url"]
        print(f" done")
        print(f"    URL: {url}")

        # Save to manifest
        manifest[city_slug] = url
        save_manifest(manifest)
        return url

    except Exception as e:
        print(f" FAILED: {e}")
        return None
    finally:
        if tmp_jpg and os.path.exists(tmp_jpg):
            os.unlink(tmp_jpg)


def upload_all(force: bool = False) -> dict[str, str]:
    """Upload all rendered city posters.

    Returns dict of {city_slug: url}.
    """
    _configure()
    results: dict[str, str] = {}

    render_dirs = sorted(Path(RENDERS_DIR).iterdir())
    cities = []
    for d in render_dirs:
        if not d.is_dir():
            continue
        poster = d / f"{d.name}_16x20.png"
        if poster.exists():
            cities.append(d.name)

    print(f"\nUploading {len(cities)} posters to Cloudinary...")
    print(f"  Cloud: {CLOUD_NAME}")
    print(f"  Folder: geoline/\n")

    for i, slug in enumerate(cities, 1):
        print(f"[{i}/{len(cities)}]", end=" ")
        url = upload_poster(slug, force=force)
        if url:
            results[slug] = url

    print(f"\nDone: {len(results)}/{len(cities)} uploaded")
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Upload posters to Cloudinary")
    parser.add_argument("--city", type=str, help="Upload single city")
    parser.add_argument("--force", action="store_true", help="Re-upload even if exists")
    parser.add_argument("--list", action="store_true", help="List uploaded URLs")
    args = parser.parse_args()

    if args.list:
        manifest = load_manifest()
        if not manifest:
            print("No uploads yet.")
            return
        print(f"\n{len(manifest)} uploaded posters:\n")
        for slug, url in sorted(manifest.items()):
            print(f"  {slug}: {url}")
        return

    if args.city:
        _configure()
        city = get_city(args.city)
        if not city:
            print(f"City not found: {args.city}")
            sys.exit(1)
        upload_poster(city.slug, force=args.force)
    else:
        upload_all(force=args.force)


if __name__ == "__main__":
    main()
