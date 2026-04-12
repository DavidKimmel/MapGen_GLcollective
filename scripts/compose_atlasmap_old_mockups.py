"""Generate AtlasMap mockups using the older TUR2 PSD templates.

Adds single-frame and multi-frame mockups to the AtlasMap new_mockups_fill/
folder, using different states for variety across the listing.

Output: etsy/renders/AtlasMap/new_mockups_fill/
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops
from psd_tools import PSDImage
from psd_tools.constants import BlendMode

from etsy.layer_aware_composer import fill_to_slot
from etsy.mockup_composer import MockupSlot


ATLAS_DIR = Path(r"C:\MapGen_GLcollective\etsy\renders\AtlasMap\print_ready")
OUT_DIR = Path(r"C:\MapGen_GLcollective\etsy\renders\AtlasMap\new_mockups_fill")
BEST_DIR = Path(r"C:\MapGen_GLcollective\etsy\TUR2\Best")
FLAT_DIR = BEST_DIR / "Flat"
LIFESTYLE_DIR = Path(
    r"C:\MapGen_GLcollective\etsy\TUR2\40Vintage_Frame_Mockup_Bundle_Vertical_PSD_JPG"
)
NOV_DIR = Path(r"C:\MapGen_GLcollective\etsy\TUR2\20.11.2025\2x3 Ratio")


def find_render(state: str, size: str) -> Path:
    folder = ATLAS_DIR / state
    for f in folder.iterdir():
        if f.name.endswith(f"_{size}.png"):
            return f
    raise FileNotFoundError(f"No {size} render for {state}")


def load_art(state: str, size: str = "24x36") -> Image.Image:
    return Image.open(str(find_render(state, size))).convert("RGBA")


def get_all_smart_slots(psd: PSDImage) -> list[tuple[int, MockupSlot]]:
    """Return (layer_index, MockupSlot) for every smart object, sorted left-to-right."""
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


def compose_single(psd_path: Path, art: Image.Image) -> Image.Image:
    """Compose a single-slot PSD with layer-aware + fill + MULTIPLY."""
    psd = PSDImage.open(str(psd_path))
    slots = get_all_smart_slots(psd)
    if not slots:
        raise ValueError(f"No smart objects in {psd_path.name}")

    so_idx, slot = slots[0]
    so_layer = psd[so_idx]

    # Stage 1: render below
    below_ids = {id(psd[i]) for i in range(so_idx)}

    def below_filter(layer: object) -> bool:
        return id(layer) in below_ids and bool(getattr(layer, "visible", True))

    below = psd.composite(layer_filter=below_filter)
    if below is None:
        below = Image.new("RGB", psd.size, (255, 255, 255))
    canvas = below.convert("RGBA")

    # Stage 2: fill art into slot with MULTIPLY
    fitted = fill_to_slot(art, slot)
    below_crop = canvas.crop((slot.left, slot.top, slot.right, slot.bottom)).convert("RGB")
    fitted_rgb = fitted.convert("RGB")

    if so_layer.blend_mode == BlendMode.MULTIPLY:
        blended = ImageChops.multiply(below_crop, fitted_rgb)
    else:
        blended = fitted_rgb

    canvas.paste(blended, (slot.left, slot.top))

    # Stage 3: render above
    for i in range(so_idx + 1, len(psd)):
        layer = psd[i]
        if layer.kind == "smartobject":
            continue  # skip other smart objects (handled separately for multi)
        if not getattr(layer, "visible", True):
            continue
        layer_img = layer.composite()
        if layer_img is None:
            continue
        if layer_img.mode != "RGBA":
            layer_img = layer_img.convert("RGBA")
        canvas.alpha_composite(layer_img, (layer.left, layer.top))

    return canvas


def compose_multi(psd_path: Path, arts: list[Image.Image], featured_idx: int = 0) -> Image.Image:
    """Compose a multi-slot PSD. arts[featured_idx] goes in the featured slot.

    For CLS-4: featured_idx=1 (middle). For 2Frames: featured_idx=1 (right).
    Remaining arts fill other slots left-to-right.
    """
    psd = PSDImage.open(str(psd_path))
    slots = get_all_smart_slots(psd)
    if len(slots) < 2:
        raise ValueError(f"Expected multi-slot PSD, got {len(slots)} slots")

    # Find the lowest smart object index for the "below" render
    first_so_idx = min(idx for idx, _ in slots)

    # Render below all smart objects
    below_ids = {id(psd[i]) for i in range(first_so_idx)}

    def below_filter(layer: object) -> bool:
        return id(layer) in below_ids and bool(getattr(layer, "visible", True))

    below = psd.composite(layer_filter=below_filter)
    if below is None:
        below = Image.new("RGB", psd.size, (255, 255, 255))
    canvas = below.convert("RGBA")

    # Assign arts to slots: featured goes to featured_idx, others fill in order
    filler_arts = [a for i, a in enumerate(arts) if i != featured_idx]
    filler_iter = iter(filler_arts)
    featured_art = arts[featured_idx]

    for slot_pos, (so_idx, slot) in enumerate(slots):
        if slot_pos == featured_idx:
            art = featured_art
        else:
            art = next(filler_iter, featured_art)  # fallback to featured if not enough

        so_layer = psd[so_idx]
        fitted = fill_to_slot(art, slot)
        below_crop = canvas.crop((slot.left, slot.top, slot.right, slot.bottom)).convert("RGB")
        fitted_rgb = fitted.convert("RGB")

        if so_layer.blend_mode == BlendMode.MULTIPLY:
            blended = ImageChops.multiply(below_crop, fitted_rgb)
        else:
            blended = fitted_rgb

        canvas.paste(blended, (slot.left, slot.top))

    # Render any non-smart-object layers above all smart objects
    last_so_idx = max(idx for idx, _ in slots)
    so_indices = {idx for idx, _ in slots}
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


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Single-frame old mockups ────────────────────────────────
    singles: list[tuple[str, Path, str]] = [
        # (output_suffix, psd_path, state)
        ("main_georgia", FLAT_DIR / "Main.psd", "Georgia"),
        ("mockup4_utah", FLAT_DIR / "Mockup4.psd", "Utah"),
        ("frame15_arizona", LIFESTYLE_DIR / "Frame 15.psd", "Arizona"),
        ("frame33_nevada", LIFESTYLE_DIR / "Frame 33.psd", "Nevada"),
    ]

    print("Single-frame mockups...")
    for suffix, psd_path, state in singles:
        art = load_art(state)
        composed = compose_single(psd_path, art)
        out = OUT_DIR / f"atlas_{suffix}.jpg"
        composed.convert("RGB").save(str(out), "JPEG", quality=95)
        print(f"  wrote {out.name}")

    # ── Multi-frame mockups ─────────────────────────────────────
    print("\nMulti-frame mockups...")

    # CLS-4: 3 frames, featured = middle (index 1 when sorted left-to-right)
    cls4_arts = [
        load_art("Georgia"),      # left
        load_art("California"),   # middle (featured)
        load_art("Idaho"),        # right
    ]
    composed = compose_multi(BEST_DIR / "CLS-4_PSD_Post.psd", cls4_arts, featured_idx=1)
    out = OUT_DIR / "atlas_cls4_3state.jpg"
    composed.convert("RGB").save(str(out), "JPEG", quality=95)
    print(f"  wrote {out.name}")

    # 2 Frames: featured = right (index 1 when sorted left-to-right)
    frames2_arts = [
        load_art("Minnesota"),    # left
        load_art("Utah"),         # right (featured)
    ]
    composed = compose_multi(BEST_DIR / "2 Frames  - StudioBlank.psd", frames2_arts, featured_idx=1)
    out = OUT_DIR / "atlas_2frames_2state.jpg"
    composed.convert("RGB").save(str(out), "JPEG", quality=95)
    print(f"  wrote {out.name}")

    # 20.11.2025 Design 1: 3 frames (beautiful wall scene)
    nov_arts = [
        load_art("NewMexico"),    # left
        load_art("California"),   # center
        load_art("Minnesota"),    # right
    ]
    psd_path = NOV_DIR / "2x3 Ratio - Desogn 1 PSD.psd"
    composed = compose_multi(psd_path, nov_arts, featured_idx=1)
    out = OUT_DIR / "atlas_nov_3state.jpg"
    composed.convert("RGB").save(str(out), "JPEG", quality=95)
    print(f"  wrote {out.name}")

    print(f"\nDone. Total files in {OUT_DIR}:")
    for f in sorted(OUT_DIR.iterdir()):
        print(f"  {f.name}")


if __name__ == "__main__":
    main()
