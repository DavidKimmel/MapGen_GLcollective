"""Batch composer: generate the 3 new PosterMockup PSDs for every MonoMap city.

For each *_monomap folder under etsy/renders/POSTED/MonoMap_Posted/, writes 6
new JPGs into a `new_mockups/` subfolder so they stay separate from the
existing per-city files:

  {city}_monomap/new_mockups/{city}_charcoal_frame_wall.jpg   — Framemockup _2x3_65.psd
  {city}_monomap/new_mockups/{city}_navy_frame_wall.jpg       — Framemockup _2x3_65.psd
  {city}_monomap/new_mockups/{city}_forest_flatlay.jpg        — PSD (1).psd
  {city}_monomap/new_mockups/{city}_dusty_rose_flatlay.jpg    — PSD (1).psd
  {city}_monomap/new_mockups/{city}_terracotta_frame_boho.jpg — Frame_038.psd
  {city}_monomap/new_mockups/{city}_black_frame_boho.jpg      — Frame_038.psd

Uses `etsy.layer_aware_composer.compose_layer_aware` so the MULTIPLY blend
mode and any foreground layers (hands, paper tubes, frame foregrounds) render
correctly.

Usage:
    python -m scripts.compose_monomap_new_mockups                # all cities
    python -m scripts.compose_monomap_new_mockups --city atlanta # one city
    python -m scripts.compose_monomap_new_mockups --start-from boston
    python -m scripts.compose_monomap_new_mockups --force        # overwrite
    python -m scripts.compose_monomap_new_mockups --dry-run      # no writes
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from etsy.layer_aware_composer import compose_layer_aware


MONOMAP_DIR = Path(r"C:\MapGen_GLcollective\etsy\renders\POSTED\MonoMap_Posted")
POSTER_DIR = Path(r"C:\MapGen_GLcollective\etsy\TUR2\PosterMockup")
# Subfolder inside each city folder where the new layer-aware mockups live.
# Keeps them separate from the legacy per-city mockups in the city root.
NEW_SUBFOLDER = "new_mockups"


@dataclass(frozen=True)
class MockupJob:
    psd_filename: str
    short_name: str  # suffix used in output filename
    color_label: str  # used in output filename
    color_render_suffix: str  # "" for the unsuffixed navy default


# All 6 MonoMap colors distributed across the 3 new mockups
# so every color is represented in lifestyle context.
JOBS: tuple[MockupJob, ...] = (
    MockupJob("Framemockup _2x3_65.psd", "frame_wall", "charcoal", "charcoal"),
    MockupJob("Framemockup _2x3_65.psd", "frame_wall", "navy", ""),
    MockupJob("PSD (1).psd", "flatlay", "forest", "forest"),
    MockupJob("PSD (1).psd", "flatlay", "dusty_rose", "dusty_rose"),
    MockupJob("Frame_038.psd", "frame_boho", "terracotta", "terracotta"),
    MockupJob("Frame_038.psd", "frame_boho", "black", "black"),
)


def city_slugs_from_disk() -> list[str]:
    """Return sorted list of city slugs from *_monomap folders on disk."""
    if not MONOMAP_DIR.exists():
        raise FileNotFoundError(f"MonoMap dir not found: {MONOMAP_DIR}")
    slugs: list[str] = []
    for entry in sorted(MONOMAP_DIR.iterdir()):
        if entry.is_dir() and entry.name.endswith("_monomap"):
            slugs.append(entry.name.removesuffix("_monomap"))
    return slugs


def render_path(city: str, color_suffix: str) -> Path:
    """Return the 24x36 render path for a city + color (empty => navy default)."""
    folder = MONOMAP_DIR / f"{city}_monomap"
    fname = (
        f"{city}_24x36.png"
        if color_suffix == ""
        else f"{city}_{color_suffix}_24x36.png"
    )
    return folder / fname


def output_path(city: str, job: MockupJob) -> Path:
    folder = MONOMAP_DIR / f"{city}_monomap" / NEW_SUBFOLDER
    return folder / f"{city}_{job.color_label}_{job.short_name}.jpg"


def run_city(
    city: str,
    *,
    force: bool,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Compose all jobs for one city. Returns (written, skipped, missing)."""
    written = 0
    skipped = 0
    missing = 0

    # Cache PSDs across jobs so we don't reopen the same file per color.
    for job in JOBS:
        out = output_path(city, job)
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists() and not force:
            skipped += 1
            continue

        art_path = render_path(city, job.color_render_suffix)
        if not art_path.exists():
            print(f"    MISSING {art_path.name} — skipping {out.name}")
            missing += 1
            continue

        if dry_run:
            print(f"    DRY    {out.name}")
            written += 1
            continue

        psd_path = POSTER_DIR / job.psd_filename
        art = Image.open(str(art_path)).convert("RGBA")
        composed = compose_layer_aware(psd_path, art)
        composed.convert("RGB").save(str(out), "JPEG", quality=95)
        print(f"    wrote  {out.name}")
        written += 1

    return written, skipped, missing


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Batch layer-aware mockup composer for MonoMap cities."
    )
    parser.add_argument("--city", help="Only run this city slug (e.g. atlanta).")
    parser.add_argument(
        "--start-from",
        help="Skip cities before this slug alphabetically (inclusive).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be written without composing or saving.",
    )
    args = parser.parse_args()

    all_cities = city_slugs_from_disk()
    if args.city:
        if args.city not in all_cities:
            print(f"ERROR: city {args.city!r} not found under {MONOMAP_DIR}")
            return 2
        cities = [args.city]
    elif args.start_from:
        if args.start_from not in all_cities:
            print(f"ERROR: start-from {args.start_from!r} not in city list")
            return 2
        cities = all_cities[all_cities.index(args.start_from):]
    else:
        cities = all_cities

    print(
        f"Composing {len(JOBS)} mockups x {len(cities)} cities "
        f"= {len(JOBS) * len(cities)} images"
    )
    if args.force:
        print("  (force: overwriting existing files)")
    if args.dry_run:
        print("  (dry-run: nothing will be written)")

    total_written = 0
    total_skipped = 0
    total_missing = 0

    for i, city in enumerate(cities, 1):
        print(f"[{i}/{len(cities)}] {city}")
        w, s, m = run_city(city, force=args.force, dry_run=args.dry_run)
        total_written += w
        total_skipped += s
        total_missing += m

    print()
    print(f"Done. wrote={total_written} skipped={total_skipped} missing={total_missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
