"""Replace Etsy listing images for all 64 MonoMap listings.

Reads listing IDs from `etsy/monomap_publish_log.csv`, builds an 11-image
layout per city from `etsy/renders/POSTED/MonoMap_Posted/{slug}_monomap/new_mockups/`,
and replaces every existing image on the listing.

Layout rules (per the user's spec):
  - Hero (rank 1) rotates across 3 variants based on alphabetical city index:
      index % 3 == 0 -> main
      index % 3 == 1 -> terracotta_frame_boho
      index % 3 == 2 -> forest_flatlay
  - 6color_labeled is always at rank 7.
  - detail_crop is always at rank 11 (last).
  - All 11 staged files upload; the other 9 ranks fill with remaining mockups.

Safety:
  - Default is --dry-run. Pass --live to actually call the API.
  - --city <slug> runs a single city (test it first, always).
  - Etsy caps a listing at 20 total images, and requires >= 1 image at all
    times. So we: delete all-but-one old image, upload all 11 new, then
    delete the last remaining old. Max total during the operation = 12.

Usage:
    # 1. Dry run over everything (no API writes)
    python -m scripts.update_monomap_listing_images --dry-run

    # 2. Test on one city for real
    python -m scripts.update_monomap_listing_images --city asheville --live

    # 3. Batch the rest (after test passes)
    python -m scripts.update_monomap_listing_images --live

    # Resume from a city alphabetically
    python -m scripts.update_monomap_listing_images --live --start-from denver
"""
from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

from etsy.api_client import EtsyApiError, EtsyClient


MONOMAP_DIR = Path(r"C:\MapGen_GLcollective\etsy\renders\POSTED\MonoMap_Posted")
PUBLISH_LOG = Path(r"C:\MapGen_GLcollective\etsy\monomap_publish_log.csv")
NEW_MOCKUPS_SUBDIR = "new_mockups"

# Hero rotation — three options that cycle alphabetically.
HERO_OPTIONS: tuple[str, ...] = (
    "main",
    "terracotta_frame_boho",
    "forest_flatlay",
)

# Fixed rank positions (1-indexed).
RANK_6COLOR = 7
RANK_DETAIL_CROP = 11  # last


@dataclass(frozen=True)
class CityJob:
    slug: str
    listing_id: int
    city_index: int  # alphabetical index for hero rotation


def load_listings_from_log() -> list[CityJob]:
    """Return one CityJob per active city, taking the most recent row per slug.

    Cities whose most-recent status is 'removed' are dropped — they reflect
    listings that have been pulled from the shop (e.g. the coastal MonoMap
    cities excluded for ocean rendering artifacts). The alphabetical city_index
    used for hero rotation is assigned AFTER filtering so rotation stays
    contiguous across active cities only.
    """
    if not PUBLISH_LOG.exists():
        raise FileNotFoundError(f"Publish log not found: {PUBLISH_LOG}")

    # most-recent-wins (log is append-only with timestamps sorted ascending)
    latest: dict[str, tuple[int, str]] = {}
    with PUBLISH_LOG.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            slug = row.get("city", "").strip()
            listing_id_s = row.get("listing_id", "").strip()
            status = row.get("status", "").strip()
            if not slug or not listing_id_s:
                continue
            latest[slug] = (int(listing_id_s), status)

    active = {
        slug: listing_id
        for slug, (listing_id, status) in latest.items()
        if status != "removed"
    }

    sorted_slugs = sorted(active.keys())
    return [
        CityJob(slug=slug, listing_id=active[slug], city_index=i)
        for i, slug in enumerate(sorted_slugs)
    ]


def build_image_layout(slug: str, city_index: int) -> list[Path]:
    """Return 11 image paths in upload order for the city.

    Satisfies: hero rotation at rank 1, 6color at rank 7, detail_crop at rank 11.
    Raises FileNotFoundError if any expected file is missing.
    """
    subdir = MONOMAP_DIR / f"{slug}_monomap" / NEW_MOCKUPS_SUBDIR
    hero_key = HERO_OPTIONS[city_index % len(HERO_OPTIONS)]

    def p(name: str) -> Path:
        return subdir / f"{slug}_{name}.jpg"

    # All 11 files that must appear exactly once:
    #   1 x main
    #   2 x frame_wall (charcoal, navy)
    #   2 x flatlay (forest, dusty_rose)
    #   2 x frame_boho (terracotta, black)
    #   1 x 2frames, 1 x cls4
    #   1 x 6color_labeled, 1 x detail_crop
    main = p("main")
    fw_charcoal = p("charcoal_frame_wall")
    fw_navy = p("navy_frame_wall")
    fl_forest = p("forest_flatlay")
    fl_dusty = p("dusty_rose_flatlay")
    fb_terracotta = p("terracotta_frame_boho")
    fb_black = p("black_frame_boho")
    two_frames = p("2frames")
    cls4 = p("cls4")
    six_color = p("6color_labeled")
    detail_crop = p("detail_crop")

    if hero_key == "main":
        ordered = [
            main,            # 1 hero
            fw_charcoal,     # 2
            fl_forest,       # 3
            fb_terracotta,   # 4
            fw_navy,         # 5
            fl_dusty,        # 6
            six_color,       # 7 FIXED
            fb_black,        # 8
            two_frames,      # 9
            cls4,            # 10
            detail_crop,     # 11 FIXED last
        ]
    elif hero_key == "terracotta_frame_boho":
        ordered = [
            fb_terracotta,   # 1 hero
            main,            # 2
            fl_forest,       # 3
            fw_charcoal,     # 4
            fb_black,        # 5
            fl_dusty,        # 6
            six_color,       # 7 FIXED
            fw_navy,         # 8
            two_frames,      # 9
            cls4,            # 10
            detail_crop,     # 11 FIXED last
        ]
    elif hero_key == "forest_flatlay":
        ordered = [
            fl_forest,       # 1 hero
            main,            # 2
            fb_terracotta,   # 3
            fw_charcoal,     # 4
            fl_dusty,        # 5
            fw_navy,         # 6
            six_color,       # 7 FIXED
            fb_black,        # 8
            two_frames,      # 9
            cls4,            # 10
            detail_crop,     # 11 FIXED last
        ]
    else:
        raise ValueError(f"Unknown hero rotation key {hero_key!r}")

    # Sanity checks on the assembled order — catch any layout bugs early.
    assert len(ordered) == 11, f"expected 11 images, got {len(ordered)}"
    assert ordered[RANK_6COLOR - 1] == six_color, "6color must be at rank 7"
    assert ordered[RANK_DETAIL_CROP - 1] == detail_crop, "detail_crop must be last"

    missing = [p for p in ordered if not p.exists()]
    if missing:
        raise FileNotFoundError(
            f"{slug}: missing {len(missing)} images: "
            + ", ".join(m.name for m in missing)
        )
    return ordered


def update_city(
    client: EtsyClient | None,
    shop_id: int | None,
    job: CityJob,
    *,
    live: bool,
) -> bool:
    """Replace the listing's images with the new 11-image layout.

    Etsy constraints: max 20 images per listing, and active listings must
    have >= 1 image at all times. So:
      1. Fetch all current image IDs.
      2. Delete all-but-one old image (listing still has >= 1 image).
      3. Upload all 11 new images (total peaks at 12, <= 20).
      4. Delete the final old image.

    Returns True on success.
    """
    hero_key = HERO_OPTIONS[job.city_index % len(HERO_OPTIONS)]
    print(f"\n[{job.city_index + 1}] {job.slug} (listing {job.listing_id}, hero={hero_key})")

    try:
        images = build_image_layout(job.slug, job.city_index)
    except FileNotFoundError as e:
        print(f"  SKIP {e}")
        return False

    for rank, path in enumerate(images, 1):
        marker = "HERO" if rank == 1 else ("6COLOR" if rank == RANK_6COLOR else ("DETAIL" if rank == RANK_DETAIL_CROP else ""))
        print(f"    [{rank:2d}] {path.name} {marker}")

    if not live:
        return True

    assert client is not None and shop_id is not None, "live mode requires client + shop_id"

    # Step 1 — fetch all current image IDs.
    try:
        old = client.get_listing_images(shop_id, job.listing_id)
    except EtsyApiError as e:
        print(f"  FAIL get_listing_images: {e}")
        return False
    old_ids = [img["listing_image_id"] for img in old]
    print(f"  existing images on listing: {len(old_ids)}")

    # Step 2 — delete all-but-one old image (keep the listing non-empty).
    keep_last = 1 if old_ids else 0
    to_delete_first = old_ids[keep_last:]
    keep_old = old_ids[:keep_last]
    for image_id in to_delete_first:
        try:
            client.delete_listing_image(shop_id, job.listing_id, image_id)
        except EtsyApiError as e:
            print(f"    predelete {image_id} FAILED: {e}")
            return False
    if to_delete_first:
        print(f"  predeleted {len(to_delete_first)} old images ({len(keep_old)} kept as placeholder)")

    # Step 3 — upload all 11 new images. Peak total = keep_last + 11 (<= 12).
    for rank, path in enumerate(images, 1):
        try:
            client.upload_listing_image(shop_id, job.listing_id, str(path), rank=rank)
            print(f"    upload [{rank:2d}] {path.name} OK")
        except EtsyApiError as e:
            print(f"    upload [{rank:2d}] {path.name} FAILED: {e}")
            print(
                "  aborting this city; some old images were predeleted and "
                "new uploads are partial — investigate before retrying."
            )
            return False

    # Step 4 — delete the final old image(s) still kept as placeholder.
    for image_id in keep_old:
        try:
            client.delete_listing_image(shop_id, job.listing_id, image_id)
        except EtsyApiError as e:
            print(f"  WARNING could not delete old image {image_id}: {e}")

    print(f"  DONE {job.slug}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replace Etsy listing images for MonoMap cities."
    )
    parser.add_argument("--city", help="Only run this city slug (test first!).")
    parser.add_argument(
        "--start-from",
        help="Skip cities alphabetically before this slug (inclusive).",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Actually call the Etsy API. Without this flag, runs in dry-run mode.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Explicit dry-run flag (default behavior, included for clarity).",
    )
    args = parser.parse_args()

    live = args.live and not args.dry_run

    jobs = load_listings_from_log()
    print(f"Loaded {len(jobs)} cities from {PUBLISH_LOG.name}")

    if args.city:
        jobs = [j for j in jobs if j.slug == args.city]
        if not jobs:
            print(f"ERROR: city {args.city!r} not found in publish log")
            return 2
    elif args.start_from:
        filtered = [j for j in jobs if j.slug >= args.start_from]
        if not filtered:
            print(f"ERROR: start-from {args.start_from!r} not in city list")
            return 2
        jobs = filtered

    if live:
        print("*** LIVE MODE — Etsy API writes will occur ***")
    else:
        print("--- dry run — no API writes ---")

    client: EtsyClient | None = None
    shop_id: int | None = None
    if live:
        client = EtsyClient()
        shop_id = client.get_shop_id()
        print(f"Shop ID: {shop_id}")

    successes = 0
    failures = 0
    for job in jobs:
        ok = update_city(client, shop_id, job, live=live)
        if ok:
            successes += 1
        else:
            failures += 1

    print()
    print(f"Done. successes={successes} failures={failures} total={len(jobs)}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
