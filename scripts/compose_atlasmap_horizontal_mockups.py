"""Generate mockups for all horizontal/landscape AtlasMap states.

Creates a mockups/ subfolder inside each state's print_ready folder with:
  {state}_h6.jpg    — hero (white frame, window shadows)
  {state}_linen.jpg — flat lay on linen
  {state}_h5.jpg    — dark wall, white frame
  {state}_h4.jpg    — warm wall, black frame
  {state}_h39.jpg   — brick loft lifestyle
  {state}_h42.jpg   — living room above couch
  {state}_h13.jpg   — concrete wall, floating frame
  {state}_detail_crop.jpg — 50/50 terrain + background edge crop

Usage:
    python -m scripts.compose_atlasmap_horizontal_mockups
    python -m scripts.compose_atlasmap_horizontal_mockups --state Alaska
    python -m scripts.compose_atlasmap_horizontal_mockups --start-from Montana
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from psd_tools import PSDImage
from psd_tools.constants import Tag


ATLAS_DIR = Path(r"C:\MapGen_GLcollective\etsy\renders\AtlasMap\print_ready")
HFRAMES = Path(r"C:\MapGen_GLcollective\etsy\TUR2\HorizontalFrames")
LINEN_PSD = HFRAMES / "1. PSD - Poster Mockup on Linen.psd"

HORIZONTAL_STATES: list[str] = [
    "Alaska", "Arkansas", "Colorado", "Connecticut", "Florida", "Hawaii",
    "Iowa", "Kansas", "Kentucky", "Louisiana", "Maryland", "Massachusetts",
    "Missouri", "Montana", "Nebraska", "NewYork", "NorthCarolina",
    "NorthDakota", "Oklahoma", "Oregon", "Pennsylvania", "SouthCarolina",
    "SouthDakota", "Tennessee", "Texas", "Virginia", "Washington",
    "WestVirginia", "Wyoming",
]

# Frame PSDs — (filename, short_name)
FRAME_PSDS: list[tuple[str, str]] = [
    ("6.psd", "h6"),
    ("5.psd", "h5"),
    ("4.psd", "h4"),
    ("13.psd", "h13"),
    ("39.psd", "h39"),
    ("42.psd", "h42"),
]


def get_transform_corners(psd: PSDImage, so_index: int = 2) -> np.ndarray:
    """Extract 4 corner points from PlacedLayerData transform."""
    so = psd[so_index]
    block = so.tagged_blocks.get_data(Tag.PLACED_LAYER2)
    t = block.transform
    return np.array([
        [float(t[0]), float(t[1])],
        [float(t[2]), float(t[3])],
        [float(t[4]), float(t[5])],
        [float(t[6]), float(t[7])],
    ], dtype=np.float32)


def compose_hframe(psd_path: Path, art_rgb: np.ndarray, src_corners: np.ndarray) -> Image.Image:
    """Compose art into a horizontal frame PSD with perspective warp + MULTIPLY."""
    psd = PSDImage.open(str(psd_path))
    dst = get_transform_corners(psd, so_index=2)
    canvas = np.array(psd.composite().convert("RGB"))
    ch, cw = canvas.shape[:2]

    M = cv2.getPerspectiveTransform(src_corners, dst)
    warped = cv2.warpPerspective(art_rgb, M, (cw, ch),
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    mask = cv2.warpPerspective(
        np.ones((art_rgb.shape[0], art_rgb.shape[1]), dtype=np.uint8) * 255,
        M, (cw, ch), borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    mask_3ch = np.stack([mask] * 3, axis=2) > 128

    result = canvas.copy()
    multiplied = (canvas.astype(np.float32) * warped.astype(np.float32) / 255.0).astype(np.uint8)
    result[mask_3ch] = multiplied[mask_3ch]
    return Image.fromarray(result)


def compose_linen(art_rgb: np.ndarray, src_corners: np.ndarray) -> Image.Image:
    """Compose art into the linen flat-lay PSD (NORMAL blend + shadow overlay)."""
    psd = PSDImage.open(str(LINEN_PSD))
    dst = get_transform_corners(psd, so_index=1)

    # Render base only
    below_ids = {id(psd[0])}
    below = np.array(psd.composite(
        layer_filter=lambda l: id(l) in below_ids and getattr(l, 'visible', True)
    ).convert("RGB"))
    ch, cw = below.shape[:2]

    M = cv2.getPerspectiveTransform(src_corners, dst)
    warped = cv2.warpPerspective(art_rgb, M, (cw, ch),
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    mask = cv2.warpPerspective(
        np.ones((art_rgb.shape[0], art_rgb.shape[1]), dtype=np.uint8) * 255,
        M, (cw, ch), borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    mask_3ch = np.stack([mask] * 3, axis=2) > 128

    result = below.copy()
    result[mask_3ch] = warped[mask_3ch]  # NORMAL blend

    # Shadow overlay (layer 2, MULTIPLY)
    shadows = psd[2]
    shadows_img = shadows.composite()
    if shadows_img is not None:
        sa = np.array(shadows_img.convert("RGBA"))
        sl, st, sr, sb = shadows.left, shadows.top, shadows.right, shadows.bottom
        s_rgb = sa[:, :, :3].astype(np.float32)
        s_alpha = sa[:, :, 3].astype(np.float32) / 255.0
        region = result[st:sb, sl:sr].astype(np.float32)
        mult = region * s_rgb / 255.0
        blended = region * (1.0 - s_alpha[:, :, np.newaxis]) + mult * s_alpha[:, :, np.newaxis]
        result[st:sb, sl:sr] = blended.clip(0, 255).astype(np.uint8)

    return Image.fromarray(result)


def generate_detail_crop(state: str, img: Image.Image, out_dir: Path) -> None:
    """Generate a 50/50 terrain-to-background detail crop."""
    arr = np.array(img.convert("RGB"))
    w, h = img.size

    # Find map content via color saturation (background is gray, map is colorful)
    r, g, b = arr[:, :, 0].astype(float), arr[:, :, 1].astype(float), arr[:, :, 2].astype(float)
    max_ch = np.maximum(np.maximum(r, g), b)
    min_ch = np.minimum(np.minimum(r, g), b)
    saturation = (max_ch - min_ch) / (max_ch + 1)
    gray = arr.mean(axis=2)
    content_mask = (saturation > 0.08) & (gray < 230)

    rows = np.any(content_mask, axis=1)
    cols = np.any(content_mask, axis=0)

    if not rows.any() or not cols.any():
        # Fallback: center crop
        crop_size = min(w, h) // 2
        left = (w - crop_size) // 2
        top = (h - crop_size) // 2
    else:
        c_top = int(np.argmax(rows))
        c_bottom = int(len(rows) - np.argmax(rows[::-1]))
        c_left = int(np.argmax(cols))
        c_right = int(len(cols) - np.argmax(cols[::-1]))

        # Crop size: ~45% of the shorter dimension
        crop_size = int(min(w, h) * 0.45)

        # Target the RIGHT edge of content for landscape states (map on left, bg on right)
        # This gives ~50/50 split
        left = max(0, c_right - int(crop_size * 0.6))
        top = max(0, (c_top + c_bottom) // 2 - crop_size // 2)

        # Clamp
        if left + crop_size > w:
            left = w - crop_size
        if top + crop_size > h:
            top = h - crop_size

    cropped = img.crop((left, top, left + crop_size, top + crop_size))
    cropped = cropped.resize((2000, 2000), Image.LANCZOS)

    slug = state.lower()
    out = out_dir / f"{slug}_detail_crop.jpg"
    cropped.save(str(out), "JPEG", quality=92)
    print(f"    wrote {out.name}")


def generate_state(state: str, *, force: bool = False) -> None:
    """Generate all mockups for a single horizontal state."""
    out_dir = ATLAS_DIR / state / "mockups"
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = state.lower()

    # Load art
    render_path = next((ATLAS_DIR / state).glob("*36x24.png"))
    art_pil = Image.open(str(render_path)).convert("RGBA")
    art_rgb = np.array(art_pil.convert("RGB"))
    h_art, w_art = art_rgb.shape[:2]
    src_corners = np.array([[0, 0], [w_art, 0], [w_art, h_art], [0, h_art]], dtype=np.float32)

    # Frame mockups
    for psd_name, short in FRAME_PSDS:
        out = out_dir / f"{slug}_{short}.jpg"
        if out.exists() and not force:
            print(f"    skip {out.name}")
            continue
        composed = compose_hframe(HFRAMES / psd_name, art_rgb, src_corners)
        composed.save(str(out), "JPEG", quality=95)
        print(f"    wrote {out.name}")

    # Linen mockup
    out = out_dir / f"{slug}_linen.jpg"
    if not out.exists() or force:
        composed = compose_linen(art_rgb, src_corners)
        composed.save(str(out), "JPEG", quality=95)
        print(f"    wrote {out.name}")
    else:
        print(f"    skip {out.name}")

    # Detail crop
    out = out_dir / f"{slug}_detail_crop.jpg"
    if not out.exists() or force:
        generate_detail_crop(state, art_pil.convert("RGB"), out_dir)
    else:
        print(f"    skip {out.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate horizontal AtlasMap mockups.")
    parser.add_argument("--state", help="Only run this state.")
    parser.add_argument("--start-from", help="Start from this state alphabetically.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files.")
    args = parser.parse_args()

    if args.state:
        states = [args.state]
    elif args.start_from:
        states = [s for s in HORIZONTAL_STATES if s >= args.start_from]
    else:
        states = HORIZONTAL_STATES

    print(f"Generating mockups for {len(states)} horizontal states (8 each = {len(states)*8} images)\n")

    for i, state in enumerate(states, 1):
        print(f"[{i}/{len(states)}] {state}")
        generate_state(state, force=args.force)

    print(f"\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
