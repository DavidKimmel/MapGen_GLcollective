"""GeoLine Collective — Dynamic Mockups API Integration.

Generates professional lifestyle mockup images for Etsy listings using
the Dynamic Mockups API (https://dynamicmockups.com/).

The API uses Photoshop smart objects for high-quality compositing with
proper lighting, shadows, and perspective — no stretching or distortion.

Flow:
  1. List available wall art mockup templates
  2. For each city poster, render it into selected templates via API
  3. Download rendered mockups to etsy/renders/{city_slug}/

Usage:
    python -m etsy.dynamic_mockups --list-templates          # Browse templates
    python -m etsy.dynamic_mockups --test                     # Test with Chicago
    python -m etsy.dynamic_mockups --city Chicago             # One city
    python -m etsy.dynamic_mockups --tier 1                   # All Tier 1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

from etsy.city_list import ALL_CITIES, CityListing, get_cities_by_tier, get_city
from etsy.batch_etsy_render import RENDERS_DIR

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE = "https://app.dynamicmockups.com/api/v1"

# Load from .env file
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

API_KEY = os.environ.get("DYNAMIC_MOCKUPS_API_KEY", "")

# Rate limiting
REQUEST_DELAY = 1.0  # Seconds between API calls

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _headers() -> dict[str, str]:
    """Build auth headers."""
    if not API_KEY:
        raise ValueError(
            "Dynamic Mockups API key not set. Either:\n"
            "  export DYNAMIC_MOCKUPS_API_KEY=your-key\n"
            "  or pass --api-key on the command line"
        )
    return {
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def list_mockup_templates(name_filter: str | None = None) -> list[dict]:
    """List available mockup templates from the API.

    Args:
        name_filter: Optional name filter string

    Returns:
        List of mockup template dicts with uuid, name, smart_objects, etc.
    """
    params: dict[str, str] = {"include_all_catalogs": "true"}
    if name_filter:
        params["name"] = name_filter

    resp = requests.get(
        f"{API_BASE}/mockups",
        headers=_headers(),
        params=params,
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("success"):
        print(f"  [!] API error: {data.get('message', 'Unknown')}")
        return []

    return data.get("data", [])


def render_mockup(
    mockup_uuid: str,
    smart_object_uuid: str,
    image_url: str,
    fit: str = "contain",
    export_label: str = "",
    image_format: str = "png",
    image_size: int | None = None,
) -> str | None:
    """Render a mockup via the API.

    Args:
        mockup_uuid: Template UUID
        smart_object_uuid: Smart object UUID within the template
        image_url: Public URL of the poster image to place
        fit: How to fit the image — "contain", "cover", or "stretch"
        export_label: Label for tracking the render
        image_format: Output format — "png", "jpg", or "webp"
        image_size: Output width in pixels (height auto-scales)

    Returns:
        URL of the rendered mockup image, or None on failure
    """
    body: dict = {
        "mockup_uuid": mockup_uuid,
        "smart_objects": [
            {
                "uuid": smart_object_uuid,
                "asset": {
                    "url": image_url,
                    "fit": fit,
                },
            }
        ],
    }

    if export_label:
        body["export_label"] = export_label

    export_options: dict = {"image_format": image_format}
    if image_size:
        export_options["image_size"] = image_size
    body["export_options"] = export_options

    resp = requests.post(
        f"{API_BASE}/renders",
        headers=_headers(),
        json=body,
    )

    if resp.status_code != 200:
        print(f"  [!] Render failed ({resp.status_code}): {resp.text[:200]}")
        return None

    data = resp.json()
    if not data.get("success"):
        print(f"  [!] Render error: {data.get('message', 'Unknown')}")
        return None

    export_path = data.get("data", {}).get("export_path")
    return export_path


def download_image(url: str, output_path: str) -> None:
    """Download an image from URL to disk."""
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


# ---------------------------------------------------------------------------
# Template discovery
# ---------------------------------------------------------------------------

def discover_wall_art_templates() -> list[dict]:
    """Find wall art / frame mockup templates.

    Searches for common wall art keywords and returns matches.
    """
    keywords = ["wall art", "frame", "poster"]
    seen_uuids: set[str] = set()
    results: list[dict] = []

    for kw in keywords:
        templates = list_mockup_templates(name_filter=kw)
        for t in templates:
            uuid = t.get("uuid", "")
            if uuid and uuid not in seen_uuids:
                seen_uuids.add(uuid)
                results.append(t)
        time.sleep(REQUEST_DELAY)

    return results


def print_template_info(templates: list[dict]) -> None:
    """Pretty-print template info for selection."""
    for i, t in enumerate(templates, 1):
        name = t.get("name", "Unknown")
        uuid = t.get("uuid", "")
        smart_objects = t.get("smart_objects", [])
        so_count = len(smart_objects)
        thumbnail = t.get("thumbnail", "")

        print(f"\n  [{i}] {name}")
        print(f"      UUID: {uuid}")
        print(f"      Smart Objects: {so_count}")
        if thumbnail:
            print(f"      Thumbnail: {thumbnail}")

        for so in smart_objects:
            so_uuid = so.get("uuid", "")
            so_name = so.get("name", "")
            width = so.get("width", "?")
            height = so.get("height", "?")
            print(f"        -> {so_name} ({width}x{height}) UUID: {so_uuid}")


# ---------------------------------------------------------------------------
# Saved template selections (populated after discovery)
# ---------------------------------------------------------------------------

# After browsing templates, save the ones we want to use here.
# Each entry maps a friendly ID to the mockup_uuid and smart_object_uuid.
SELECTED_TEMPLATES_FILE = os.path.join(
    os.path.dirname(__file__), "dynamic_mockup_templates.json"
)


def load_selected_templates() -> list[dict]:
    """Load saved template selections from JSON file."""
    if not os.path.exists(SELECTED_TEMPLATES_FILE):
        return []
    with open(SELECTED_TEMPLATES_FILE) as f:
        return json.load(f)


def save_selected_templates(templates: list[dict]) -> None:
    """Save template selections to JSON file."""
    with open(SELECTED_TEMPLATES_FILE, "w") as f:
        json.dump(templates, f, indent=2)
    print(f"  Saved {len(templates)} templates to {SELECTED_TEMPLATES_FILE}")


# ---------------------------------------------------------------------------
# Poster URL hosting (for API — needs public URL)
# ---------------------------------------------------------------------------

def get_poster_url(city: CityListing) -> str | None:
    """Get the public Cloudinary URL for a city's hero poster.

    Reads from the Cloudinary upload manifest.

    Returns:
        Public URL string, or None if not uploaded yet.
    """
    from etsy.cloudinary_upload import load_manifest

    manifest = load_manifest()
    url = manifest.get(city.slug)
    if url:
        return url

    print(f"  [!] No Cloudinary URL for {city.slug}. Run: python -m etsy.cloudinary_upload --city {city.city}")
    return None


def start_local_server(port: int = 8765) -> str:
    """Start a simple HTTP server to serve poster files to the API.

    Returns the base URL for accessing files.
    """
    import threading
    import http.server
    import functools

    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=RENDERS_DIR,
    )

    server = http.server.HTTPServer(("0.0.0.0", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print(f"  Local file server started on port {port}")
    print(f"  Serving: {RENDERS_DIR}")
    return f"http://localhost:{port}"


# ---------------------------------------------------------------------------
# Render orchestration
# ---------------------------------------------------------------------------

def render_city_mockups(
    city: CityListing,
    templates: list[dict] | None = None,
    image_url: str | None = None,
) -> dict[str, str | None]:
    """Render all selected mockup templates for a city.

    Args:
        city: City to render mockups for
        templates: Template list (defaults to saved selections)
        image_url: Public URL of the poster (auto-constructed if None)

    Returns:
        Dict of template_id -> output file path
    """
    if templates is None:
        templates = load_selected_templates()
    if not templates:
        print("  [!] No templates selected. Run --list-templates first.")
        return {}

    if image_url is None:
        image_url = get_poster_url(city)
        if not image_url:
            return {}

    city_dir = os.path.join(RENDERS_DIR, city.slug)
    print(f"\n  Rendering mockups: {city.city}, {city.state}")

    results: dict[str, str | None] = {}
    for tpl in templates:
        tid = tpl["id"]
        mockup_uuid = tpl["mockup_uuid"]
        so_uuid = tpl["smart_object_uuid"]
        label = f"{city.slug}_{tid}"

        print(f"    {tpl['name']}...", end="", flush=True)

        render_url = render_mockup(
            mockup_uuid=mockup_uuid,
            smart_object_uuid=so_uuid,
            image_url=image_url,
            fit="cover",
            export_label=label,
            image_format="png",
        )

        if render_url:
            out_path = os.path.join(city_dir, f"dm_{tid}.png")
            download_image(render_url, out_path)
            print(f" saved")
            results[tid] = out_path
        else:
            print(f" FAILED")
            results[tid] = None

        time.sleep(REQUEST_DELAY)

    success = sum(1 for v in results.values() if v is not None)
    print(f"  Done: {success}/{len(templates)} mockups for {city.city}")
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    global API_KEY

    parser = argparse.ArgumentParser(
        description="Generate mockups via Dynamic Mockups API"
    )
    parser.add_argument("--api-key", type=str, help="API key")
    parser.add_argument("--list-templates", action="store_true",
                        help="Browse available wall art templates")
    parser.add_argument("--search", type=str, default=None,
                        help="Search templates by name")
    parser.add_argument("--test", action="store_true",
                        help="Test render with sandbox template")
    parser.add_argument("--city", type=str, help="Single city")
    parser.add_argument("--tier", type=int, help="Tier (1/2/3)")
    parser.add_argument("--image-url", type=str, help="Public URL of poster image")
    args = parser.parse_args()

    if args.api_key:
        API_KEY = args.api_key
    if not API_KEY:
        API_KEY = os.environ.get("DYNAMIC_MOCKUPS_API_KEY", "")

    if args.list_templates or args.search:
        if args.search:
            print(f"Searching templates for: {args.search}")
            templates = list_mockup_templates(name_filter=args.search)
        else:
            print("Discovering wall art templates...")
            templates = discover_wall_art_templates()
        print(f"\nFound {len(templates)} templates:")
        print_template_info(templates)
        return

    if args.test:
        print("Running API test render...")
        # Use the sandbox template from Dynamic Mockups docs
        test_url = render_mockup(
            mockup_uuid="9ffb48c2-264f-42b9-ab86-858c410422cc",
            smart_object_uuid="cc864498-b8d1-495a-9968-45937edf42b3",
            image_url="https://app-dynamicmockups-production.s3.eu-central-1.amazonaws.com/static/api_sandbox_icon.png",
            export_label="test_render",
        )
        if test_url:
            out_path = os.path.join(RENDERS_DIR, "_test_dynamic_mockup.png")
            download_image(test_url, out_path)
            print(f"  Test render saved: {out_path}")
            print(f"  Render URL: {test_url}")
        else:
            print("  Test render failed!")
        return

    if args.city:
        city = get_city(args.city)
        if not city:
            print(f"City not found: {args.city}")
            sys.exit(1)
        render_city_mockups(city, image_url=args.image_url)
    elif args.tier:
        cities = get_cities_by_tier(args.tier)
        for i, city in enumerate(cities, 1):
            print(f"\n[{i}/{len(cities)}]")
            render_city_mockups(city, image_url=args.image_url)
    else:
        print("Specify --list-templates, --test, --city, or --tier")
        sys.exit(1)


if __name__ == "__main__":
    main()
