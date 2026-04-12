"""Generate a complete mockup set for a single AtlasMap state.

Creates a mockups/ subfolder inside the state's print_ready folder
with all upload-ready images for the listing.

Usage:
    python -m scripts.compose_atlasmap_state_mockups --state Alabama
    python -m scripts.compose_atlasmap_state_mockups --state California --force
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageChops
from psd_tools import PSDImage
from psd_tools.constants import BlendMode

from etsy.layer_aware_composer import compose_layer_aware, fill_to_slot
from etsy.mockup_composer import MockupSlot


ATLAS_DIR = Path(r"C:\MapGen_GLcollective\etsy\renders\AtlasMap\print_ready")
BEST_DIR = Path(r"C:\MapGen_GLcollective\etsy\TUR2\Best")
FLAT_DIR = BEST_DIR / "Flat"
LIFESTYLE_DIR = Path(
    r"C:\MapGen_GLcollective\etsy\TUR2\40Vintage_Frame_Mockup_Bundle_Vertical_PSD_JPG"
)
POSTER_DIR = Path(r"C:\MapGen_GLcollective\etsy\TUR2\PosterMockup")
NOV_DIR = Path(r"C:\MapGen_GLcollective\etsy\TUR2\3FrameSet\2x3 Ratio")

# Vertical filler states for multi-frame mockups (visually diverse).
# If featured state is one of these, it gets skipped and next is used.
VERTICAL_FILLERS: list[str] = [
    "California", "Idaho", "Georgia", "Utah", "Arizona", "Minnesota",
]

# ── Orientation lookup ──────────────────────────────────────────────
HORIZONTAL_STATES: set[str] = {
    "Alaska", "Arkansas", "Colorado", "Connecticut", "Florida", "Hawaii",
    "Iowa", "Kansas", "Kentucky", "Louisiana", "Maryland", "Massachusetts",
    "Missouri", "Montana", "Nebraska", "NewYork", "NorthCarolina",
    "NorthDakota", "Oklahoma", "Oregon", "Pennsylvania", "SouthCarolina",
    "SouthDakota", "Tennessee", "Texas", "Virginia", "Washington",
    "WestVirginia", "Wyoming",
}


def is_portrait(state: str) -> bool:
    return state not in HORIZONTAL_STATES


def render_size(state: str) -> str:
    return "24x36" if is_portrait(state) else "36x24"


def find_render(state: str, size: str | None = None) -> Path:
    if size is None:
        size = render_size(state)
    folder = ATLAS_DIR / state
    for f in folder.iterdir():
        if f.name.endswith(f"_{size}.png"):
            return f
    raise FileNotFoundError(f"No {size} render for {state}")


def load_art(state: str, size: str | None = None) -> Image.Image:
    return Image.open(str(find_render(state, size))).convert("RGBA")


def get_fillers(featured: str, count: int) -> list[str]:
    """Pick portrait filler states, skipping the featured state."""
    fillers: list[str] = []
    for s in VERTICAL_FILLERS:
        if s == featured:
            continue
        fillers.append(s)
        if len(fillers) == count:
            break
    return fillers


# ── Multi-slot compose (same as compose_atlasmap_old_mockups.py) ────

def get_all_smart_slots(psd: PSDImage) -> list[tuple[int, MockupSlot]]:
    slots: list[tuple[int, MockupSlot]] = []
    for i, layer in enumerate(psd):
        if layer.kind == "smartobject":
            slots.append((
                i,
                MockupSlot(
                    left=layer.left, top=layer.top,
                    right=layer.right, bottom=layer.bottom,
                ),
            ))
    slots.sort(key=lambda s: s[1].left)
    return slots


def compose_multi_fill(psd_path: Path, arts: list[Image.Image], featured_idx: int = 0) -> Image.Image:
    psd = PSDImage.open(str(psd_path))
    slots = get_all_smart_slots(psd)
    first_so_idx = min(idx for idx, _ in slots)

    below_ids = {id(psd[i]) for i in range(first_so_idx)}
    def below_filter(layer: object) -> bool:
        return id(layer) in below_ids and bool(getattr(layer, "visible", True))

    below = psd.composite(layer_filter=below_filter)
    if below is None:
        below = Image.new("RGB", psd.size, (255, 255, 255))
    canvas = below.convert("RGBA")

    filler_arts = [a for i, a in enumerate(arts) if i != featured_idx]
    filler_iter = iter(filler_arts)
    featured_art = arts[featured_idx]

    for slot_pos, (so_idx, slot) in enumerate(slots):
        art = featured_art if slot_pos == featured_idx else next(filler_iter, featured_art)
        so_layer = psd[so_idx]
        fitted = fill_to_slot(art, slot)
        below_crop = canvas.crop((slot.left, slot.top, slot.right, slot.bottom)).convert("RGB")
        fitted_rgb = fitted.convert("RGB")

        if so_layer.blend_mode == BlendMode.MULTIPLY:
            blended = ImageChops.multiply(below_crop, fitted_rgb)
        else:
            blended = fitted_rgb
        canvas.paste(blended, (slot.left, slot.top))

    last_so_idx = max(idx for idx, _ in slots)
    for i in range(last_so_idx + 1, len(psd)):
        layer = psd[i]
        if not getattr(layer, "visible", True):
            continue
        layer_img = layer.composite()
        if layer_img is None:
            continue
        if layer_img.mode != "RGBA":
            layer_img = layer_img.convert("RGBA")
        canvas.alpha_composite(layer_img, (layer.left, layer.top))

    return canvas


# ── Detail crop ─────────────────────────────────────────────────────

def generate_detail_crop(state: str, out_dir: Path) -> None:
    img = Image.open(str(find_render(state))).convert("RGB")
    w, h = img.size

    # For portrait states: crop upper area (usually most terrain detail)
    # For landscape: crop center
    if is_portrait(state):
        crop_size = int(min(w, h) * 0.55)
        left = int(w * 0.15)
        top = int(h * 0.12)
    else:
        crop_size = int(min(w, h) * 0.55)
        left = int(w * 0.25)
        top = int(h * 0.15)

    # Clamp to image bounds
    if left + crop_size > w:
        left = max(0, w - crop_size)
    if top + crop_size > h:
        top = max(0, h - crop_size)

    cropped = img.crop((left, top, left + crop_size, top + crop_size))
    cropped = cropped.resize((2000, 2000), Image.LANCZOS)

    slug = state.lower()
    out = out_dir / f"{slug}_detail_crop.jpg"
    cropped.save(str(out), "JPEG", quality=92)
    print(f"  wrote {out.name}")


# ── Main ────────────────────────────────────────────────────────────

def generate_state_mockups(state: str, *, force: bool = False) -> None:
    if not is_portrait(state):
        print(f"  NOTE: {state} is landscape — skipping portrait-only PSD templates.")
        print(f"  Horizontal mockup PSDs needed. Only generating detail crop + grid.")
        # For now, only do what we can
        out_dir = ATLAS_DIR / state / "mockups"
        out_dir.mkdir(parents=True, exist_ok=True)
        generate_detail_crop(state, out_dir)
        return

    out_dir = ATLAS_DIR / state / "mockups"
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = state.lower()
    art = load_art(state)

    fillers = get_fillers(state, 3)
    filler_arts = [load_art(f) for f in fillers]

    # ── Single-frame lifestyle (new PSDs, fill mode) ──
    new_psds: list[tuple[str, str]] = [
        ("Framemockup _2x3_65.psd", "frame_wall"),
        ("PSD (1).psd", "flatlay"),
        ("Frame_038.psd", "frame_boho"),
    ]
    print(f"  New lifestyle mockups...")
    for psd_name, short in new_psds:
        out = out_dir / f"{slug}_{short}.jpg"
        if out.exists() and not force:
            print(f"    skip {out.name} (exists)")
            continue
        composed = compose_layer_aware(POSTER_DIR / psd_name, art, fill=True)
        composed.convert("RGB").save(str(out), "JPEG", quality=95)
        print(f"    wrote {out.name}")

    # ── Single-frame old PSDs ──
    old_singles: list[tuple[str, Path]] = [
        ("main", FLAT_DIR / "Main.psd"),
        ("frame15", LIFESTYLE_DIR / "Frame 15.psd"),
        ("frame33", LIFESTYLE_DIR / "Frame 33.psd"),
    ]
    print(f"  Old-style single mockups...")
    for short, psd_path in old_singles:
        out = out_dir / f"{slug}_{short}.jpg"
        if out.exists() and not force:
            print(f"    skip {out.name} (exists)")
            continue
        composed = compose_layer_aware(psd_path, art, fill=True)
        composed.convert("RGB").save(str(out), "JPEG", quality=95)
        print(f"    wrote {out.name}")

    # ── Multi-frame mockups ──
    print(f"  Multi-frame mockups (fillers: {', '.join(fillers[:2])})...")

    # CLS-4: 3 frames, featured = middle (idx 1)
    out = out_dir / f"{slug}_cls4.jpg"
    if not out.exists() or force:
        cls4_arts = [filler_arts[0], art, filler_arts[1]]
        composed = compose_multi_fill(BEST_DIR / "CLS-4_PSD_Post.psd", cls4_arts, featured_idx=1)
        composed.convert("RGB").save(str(out), "JPEG", quality=95)
        print(f"    wrote {out.name}")

    # 3FrameSet Design 1: 3 frames, featured = center (idx 1)
    out = out_dir / f"{slug}_nov3.jpg"
    if not out.exists() or force:
        nov_arts = [filler_arts[1], art, filler_arts[2]]
        composed = compose_multi_fill(NOV_DIR / "2x3 Ratio - Desogn 1 PSD.psd", nov_arts, featured_idx=1)
        composed.convert("RGB").save(str(out), "JPEG", quality=95)
        print(f"    wrote {out.name}")

    # ── Detail crop ──
    print(f"  Detail crop...")
    out = out_dir / f"{slug}_detail_crop.jpg"
    if not out.exists() or force:
        generate_detail_crop(state, out_dir)

    print(f"\n  Done. Files in {out_dir}:")
    for f in sorted(out_dir.iterdir()):
        print(f"    {f.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AtlasMap mockups for a single state.")
    parser.add_argument("--state", required=True, help="State folder name (e.g. Alabama, NewYork)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files.")
    args = parser.parse_args()

    state_dir = ATLAS_DIR / args.state
    if not state_dir.exists():
        print(f"ERROR: {state_dir} not found")
        return 2

    print(f"Generating mockups for {args.state} ({'portrait' if is_portrait(args.state) else 'landscape'})...")
    generate_state_mockups(args.state, force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
