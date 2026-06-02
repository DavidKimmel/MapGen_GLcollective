"""Build the AtlasMap Dropbox link manifest.

For each of 50 states x 5 sizes (250 files), fetch the existing shared link
from Dropbox (creating one if absent), determine orientation, and write a
JSON manifest used by connect_atlasmap_gelato.py.

Output: etsy/atlasmap_dropbox_links.json

Usage:
    python scripts/build_atlasmap_dropbox_manifest.py
    python scripts/build_atlasmap_dropbox_manifest.py --state Maryland
    python scripts/build_atlasmap_dropbox_manifest.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from etsy import r2_storage

PRINT_READY = PROJECT_ROOT / "etsy" / "renders" / "POSTED" / "AtlasMap_Posted" / "print_ready"
# Filename kept for compatibility with connect_atlasmap_gelato.py; holds R2 URLs.
MANIFEST_PATH = PROJECT_ROOT / "etsy" / "atlasmap_dropbox_links.json"

ETSY_SIZES: list[str] = ["8x10", "11x14", "16x20", "18x24", "24x36"]

# Etsy size -> (portrait_filename_suffix, landscape_filename_suffix)
SIZE_SUFFIXES: dict[str, tuple[str, str]] = {
    "8x10":  ("8x10",  "10x8"),
    "11x14": ("11x14", "14x11"),
    "16x20": ("16x20", "20x16"),
    "18x24": ("18x24", "24x18"),
    "24x36": ("24x36", "36x24"),
}


def detect_orientation(state_dir: Path) -> str:
    """Return 'portrait' or 'landscape' based on which 8x10 variant exists."""
    files = {f.name for f in state_dir.iterdir() if f.suffix == ".png"}
    has_portrait = any("_8x10." in n for n in files)
    has_landscape = any("_10x8." in n for n in files)
    if has_portrait and not has_landscape:
        return "portrait"
    if has_landscape and not has_portrait:
        return "landscape"
    raise ValueError(f"{state_dir.name}: cannot determine orientation (8x10={has_portrait} 10x8={has_landscape})")


def filename_for(state: str, etsy_size: str, orientation: str) -> str:
    portrait_sfx, landscape_sfx = SIZE_SUFFIXES[etsy_size]
    sfx = portrait_sfx if orientation == "portrait" else landscape_sfx
    return f"{state}_atlas_atlas_classic_CormorantGaramondBold_{sfx}.png"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", help="Only this state.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--merge", action="store_true",
                        help="Merge into existing manifest instead of overwriting.")
    args = parser.parse_args()

    state_dirs = sorted(d for d in PRINT_READY.iterdir() if d.is_dir())
    if args.state:
        state_dirs = [d for d in state_dirs if d.name == args.state]
        if not state_dirs:
            print(f"State '{args.state}' not found under {PRINT_READY}")
            return 1

    existing: dict[str, dict] = {}
    if args.merge and MANIFEST_PATH.exists():
        existing = json.loads(MANIFEST_PATH.read_text())

    manifest: dict[str, dict] = dict(existing)

    total_links = 0
    total_failures = 0

    for i, sd in enumerate(state_dirs, 1):
        state = sd.name
        orientation = detect_orientation(sd)
        print(f"[{i}/{len(state_dirs)}] {state} ({orientation})")

        links: dict[str, str] = {}
        for size in ETSY_SIZES:
            fname = filename_for(state, size, orientation)
            local = sd / fname
            if not local.exists():
                print(f"    MISSING local: {fname}")
                total_failures += 1
                continue
            url = r2_storage.render_url(local)
            if args.dry_run:
                print(f"    [dry] {size} -> {url}")
                continue
            links[size] = url
            total_links += 1

        if not args.dry_run:
            manifest[state] = {"orientation": orientation, "links": links}

    if not args.dry_run:
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True))
        print(f"\nWrote {MANIFEST_PATH}")
        print(f"  states:   {len(manifest)}")
        print(f"  links:    {total_links}")
        print(f"  failures: {total_failures}")
    else:
        print("\n(dry run, no manifest written)")

    return 0 if total_failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
