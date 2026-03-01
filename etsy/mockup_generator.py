"""GeoLine Collective — Leonardo.ai Mockup Image Generator.

Automates lifestyle mockup generation for Etsy listings using Leonardo.ai's
API with Content Reference (ControlNet preprocessor 100).

Flow:
  1. Upload each city's hero poster to Leonardo
  2. Generate 4 scene mockups per city via Content Reference
  3. Poll for completion and download results
  4. Save to etsy/renders/{city_slug}/mockup_*.png

Usage:
    python -m etsy.mockup_generator --city Chicago          # One city
    python -m etsy.mockup_generator --tier 1                # All Tier 1
    python -m etsy.mockup_generator --tier 1 --scenes 1,2   # Specific scenes only
    python -m etsy.mockup_generator --list-scenes           # Show available scenes
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

API_BASE = "https://cloud.leonardo.ai/api/rest/v1"
API_KEY = os.environ.get("LEONARDO_API_KEY", "")

# Leonardo model — FLUX.1 Kontext [pro] (best for preserving reference images)
MODEL_ID = "28aeddf8-bd19-4803-80fc-79602d1a9989"

# Generation settings
IMAGE_WIDTH = 1248
IMAGE_HEIGHT = 832
NUM_IMAGES = 2  # Generate 2 per scene, pick the best manually

# Rate limiting
REQUEST_DELAY = 2.0   # Seconds between API calls
POLL_INTERVAL = 5.0   # Seconds between status checks
POLL_TIMEOUT = 300.0   # Max seconds to wait for generation

# ---------------------------------------------------------------------------
# Scene definitions — reused for every city
# ---------------------------------------------------------------------------

SCENES: list[dict[str, str]] = [
    {
        "id": "living_room",
        "name": "Living Room",
        "prompt": (
            "Place this exact map print image inside a thin black picture frame "
            "with white matting, hanging on a light gray textured wall above a "
            "modern gray sofa in a minimalist living room. Keep the map image "
            "completely unchanged and unmodified. Warm natural light from a window "
            "creating soft shadows. Realistic interior photography, 4k"
        ),
    },
    {
        "id": "office",
        "name": "Home Office",
        "prompt": (
            "Place this exact map print image inside a black picture frame hanging "
            "on a white wall behind a clean oak desk with a laptop and coffee cup "
            "in a modern home office. Keep the map image completely unchanged and "
            "unmodified. Green potted plant on desk, natural daylight, warm tones. "
            "Realistic interior design photography, 4k"
        ),
    },
    {
        "id": "gallery_wall",
        "name": "Gallery Wall",
        "prompt": (
            "Place this exact map print image inside a thin black frame as the "
            "centerpiece of a curated gallery wall arrangement with other small art "
            "prints and photos on a white wall. Keep the map image completely "
            "unchanged and unmodified. Modern apartment, aesthetic minimalist decor, "
            "soft warm lighting. Realistic interior photography, 4k"
        ),
    },
    {
        "id": "gift",
        "name": "Gift Presentation",
        "prompt": (
            "This exact map print image shown as a rolled art print partially "
            "unrolled on a marble surface next to kraft paper wrapping with twine "
            "bow and eucalyptus branch. Keep the map image completely unchanged "
            "and unmodified. Flat lay photography from above, soft natural light, "
            "warm aesthetic gift presentation styling, 4k"
        ),
    },
    {
        "id": "bedroom",
        "name": "Bedroom",
        "prompt": (
            "Place this exact map print image inside a large black picture frame "
            "hanging above a bed with white linen bedding in a modern bedroom with "
            "neutral tones. Keep the map image completely unchanged and unmodified. "
            "Bedside table with lamp and small plant, morning light through sheer "
            "curtains, cozy atmosphere. Realistic interior photography, 4k"
        ),
    },
]


def _scene_by_id(scene_id: str) -> dict | None:
    """Look up a scene by its ID."""
    for s in SCENES:
        if s["id"] == scene_id:
            return s
    return None


# ---------------------------------------------------------------------------
# Leonardo API helpers
# ---------------------------------------------------------------------------

def _headers() -> dict[str, str]:
    """Build auth headers."""
    if not API_KEY:
        raise ValueError(
            "Leonardo API key not set. Either:\n"
            "  export LEONARDO_API_KEY=your-key\n"
            "  or pass --api-key on the command line"
        )
    return {
        "authorization": f"Bearer {API_KEY}",
        "content-type": "application/json",
        "accept": "application/json",
    }


def _api_get(path: str) -> dict:
    """GET request to Leonardo API."""
    resp = requests.get(f"{API_BASE}{path}", headers=_headers())
    resp.raise_for_status()
    return resp.json()


def _api_post(path: str, body: dict) -> dict:
    """POST request to Leonardo API."""
    resp = requests.post(f"{API_BASE}{path}", headers=_headers(), json=body)
    resp.raise_for_status()
    return resp.json()


def upload_image(image_path: str) -> str:
    """Upload an image to Leonardo and return the init image ID.

    Uses the presigned URL flow:
    1. Request upload credentials
    2. Upload file to S3 via presigned POST
    3. Return the image ID for use in generations
    """
    ext = Path(image_path).suffix.lstrip(".").lower()
    if ext not in ("png", "jpg", "jpeg", "webp"):
        raise ValueError(f"Unsupported image format: {ext}")

    # Step 1: Get presigned upload URL
    resp = _api_post("/init-image", {"extension": ext})
    upload_data = resp.get("uploadInitImage", {})
    image_id = upload_data["id"]
    presigned_url = upload_data["url"]
    fields = json.loads(upload_data["fields"])

    # Step 2: Upload to S3
    with open(image_path, "rb") as f:
        files = {"file": (Path(image_path).name, f, f"image/{ext}")}
        s3_resp = requests.post(presigned_url, data=fields, files=files)
        s3_resp.raise_for_status()

    print(f"    Uploaded: {Path(image_path).name} -> {image_id}")
    return image_id


def generate_mockup(
    init_image_id: str,
    scene: dict,
    city_name: str,
) -> str:
    """Start a mockup generation and return the generation ID.

    Uses FLUX Kontext contextImages to preserve the poster exactly.
    """
    body = {
        "height": IMAGE_HEIGHT,
        "width": IMAGE_WIDTH,
        "modelId": MODEL_ID,
        "num_images": NUM_IMAGES,
        "prompt": scene["prompt"].replace("map print", f"{city_name} map print"),
        "contextImages": [
            {
                "id": init_image_id,
                "type": "UPLOADED",
            }
        ],
    }

    resp = _api_post("/generations", body)
    gen_id = resp.get("sdGenerationJob", {}).get("generationId")
    if not gen_id:
        raise RuntimeError(f"No generationId in response: {resp}")

    print(f"    Started generation: {scene['name']} -> {gen_id}")
    return gen_id


def poll_generation(generation_id: str) -> list[str]:
    """Poll until generation completes, return list of image URLs."""
    start = time.time()
    while time.time() - start < POLL_TIMEOUT:
        time.sleep(POLL_INTERVAL)
        resp = _api_get(f"/generations/{generation_id}")
        gen = resp.get("generations_by_pk", {})
        status = gen.get("status")

        if status == "COMPLETE":
            images = gen.get("generated_images", [])
            return [img["url"] for img in images if img.get("url")]
        elif status == "FAILED":
            raise RuntimeError(f"Generation {generation_id} failed")
        # Still PENDING, keep polling

    raise TimeoutError(f"Generation {generation_id} timed out after {POLL_TIMEOUT}s")


def download_image(url: str, output_path: str) -> None:
    """Download an image from URL to disk."""
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def generate_city_mockups(
    city: CityListing,
    scene_ids: list[str] | None = None,
    output_dir: str | None = None,
) -> dict[str, list[str]]:
    """Generate all mockup images for a city.

    Args:
        city: City to generate mockups for
        scene_ids: Specific scene IDs to generate (None = all)
        output_dir: Override output directory

    Returns:
        Dict of scene_id -> list of downloaded file paths
    """
    slug = city.slug
    city_dir = output_dir or os.path.join(RENDERS_DIR, slug)
    hero_path = os.path.join(city_dir, f"{slug}_16x20.png")

    if not os.path.exists(hero_path):
        print(f"  [!] No hero render found: {hero_path}")
        return {}

    print(f"\n{'=' * 50}")
    print(f"Generating mockups: {city.city}, {city.state}")
    print(f"{'=' * 50}")

    # Upload hero poster
    print(f"  Uploading hero poster...")
    init_image_id = upload_image(hero_path)
    time.sleep(REQUEST_DELAY)

    # Select scenes
    scenes = SCENES if scene_ids is None else [
        s for s in SCENES if s["id"] in scene_ids
    ]

    # Fire off all generations
    gen_jobs: list[tuple[dict, str]] = []
    for scene in scenes:
        gen_id = generate_mockup(init_image_id, scene, city.city)
        gen_jobs.append((scene, gen_id))
        time.sleep(REQUEST_DELAY)

    # Poll and download results
    results: dict[str, list[str]] = {}
    for scene, gen_id in gen_jobs:
        print(f"  Waiting for {scene['name']}...", end="", flush=True)
        try:
            urls = poll_generation(gen_id)
            print(f" {len(urls)} images")

            downloaded: list[str] = []
            for i, url in enumerate(urls, 1):
                out_path = os.path.join(
                    city_dir, f"mockup_{scene['id']}_{i}.png"
                )
                download_image(url, out_path)
                print(f"    Saved: {os.path.basename(out_path)}")
                downloaded.append(out_path)

            results[scene["id"]] = downloaded

        except (RuntimeError, TimeoutError) as e:
            print(f" ERROR: {e}")
            results[scene["id"]] = []

        time.sleep(REQUEST_DELAY)

    # Summary
    total = sum(len(v) for v in results.values())
    print(f"\n  Done: {total} mockup images saved for {city.city}")
    return results


def generate_batch_mockups(
    cities: list[CityListing],
    scene_ids: list[str] | None = None,
) -> dict[str, dict[str, list[str]]]:
    """Generate mockups for multiple cities.

    Returns:
        Dict of city_slug -> {scene_id -> [file_paths]}
    """
    print(f"\n{'#' * 60}")
    print(f"GeoLine Collective — Mockup Generator")
    print(f"  Cities: {len(cities)}")
    print(f"  Scenes: {len(scene_ids) if scene_ids else len(SCENES)} per city")
    print(f"  Images per scene: {NUM_IMAGES}")
    est_total = len(cities) * (len(scene_ids) if scene_ids else len(SCENES)) * NUM_IMAGES
    print(f"  Estimated total: ~{est_total} images")
    print(f"{'#' * 60}")

    all_results: dict[str, dict[str, list[str]]] = {}
    for i, city in enumerate(cities, 1):
        print(f"\n[{i}/{len(cities)}]")
        results = generate_city_mockups(city, scene_ids=scene_ids)
        all_results[city.slug] = results

    # Final summary
    total_images = sum(
        len(paths)
        for city_results in all_results.values()
        for paths in city_results.values()
    )
    print(f"\n{'#' * 60}")
    print(f"Batch complete: {total_images} mockup images generated")
    print(f"{'#' * 60}")

    return all_results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    global API_KEY

    parser = argparse.ArgumentParser(description="Generate Leonardo.ai mockup images")
    parser.add_argument("--tier", type=int, default=None, help="Tier to generate (1/2/3)")
    parser.add_argument("--city", type=str, default=None, help="Single city")
    parser.add_argument("--all", action="store_true", help="All 25 cities")
    parser.add_argument("--scenes", type=str, default=None,
                        help="Comma-separated scene IDs (e.g., living_room,office)")
    parser.add_argument("--api-key", type=str, default=None, help="Leonardo API key")
    parser.add_argument("--list-scenes", action="store_true", help="List available scenes")
    args = parser.parse_args()

    if args.list_scenes:
        print("Available mockup scenes:")
        for s in SCENES:
            print(f"  {s['id']:15s} — {s['name']}")
        return

    if args.api_key:
        API_KEY = args.api_key
    if not API_KEY:
        API_KEY = os.environ.get("LEONARDO_API_KEY", "")

    scene_ids = args.scenes.split(",") if args.scenes else None

    if args.city:
        city = get_city(args.city)
        if not city:
            print(f"City not found: {args.city}")
            sys.exit(1)
        generate_city_mockups(city, scene_ids=scene_ids)
    elif args.all:
        generate_batch_mockups(ALL_CITIES, scene_ids=scene_ids)
    elif args.tier:
        cities = get_cities_by_tier(args.tier)
        generate_batch_mockups(cities, scene_ids=scene_ids)
    else:
        print("Specify --tier, --city, or --all")
        sys.exit(1)


if __name__ == "__main__":
    main()
