"""Layer-aware PSD compositor — the reference path for every new mockup.

See `docs/STYLE_WORKFLOW.md` § 5 "Layer-Aware + Blend-Mode Compositing" and
`CLAUDE.md` → Mockup System for the rule this module enforces.

Use this for ANY PSD mockup where either of the following is true:
  1. A visible layer sits above the smart object (hand, mask, tube,
     frame front, plant, etc.) — a flat paste would cover foreground.
  2. The smart object's blend mode is not NORMAL — commonly MULTIPLY in
     lifestyle photography, where baked-in shadows should darken the art.

If neither condition applies, the existing `etsy.mockup_composer.compose_mockup`
is sufficient. This module intentionally does not touch that code path.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops
from psd_tools import PSDImage
from psd_tools.constants import BlendMode

from etsy.mockup_composer import MockupSlot, fit_to_slot


def fill_to_slot(art: Image.Image, slot: MockupSlot) -> Image.Image:
    """Scale art to FILL the slot completely, cropping excess.

    Unlike `fit_to_slot` which pads with white to avoid cropping,
    this scales to the *larger* dimension so the slot is fully covered,
    then center-crops the overflow. At typical mismatches (2-5%) this
    loses only a sliver off the top/bottom or left/right — far less
    noticeable than white padding bars.
    """
    art_ratio = art.width / art.height
    slot_ratio = slot.width / slot.height

    if abs(art_ratio - slot_ratio) < 0.01:
        return art.resize((slot.width, slot.height), Image.LANCZOS)

    # Scale to the LARGER dimension (fill, not fit)
    scale_by_width = slot.width / art.width
    scale_by_height = slot.height / art.height
    scale = max(scale_by_width, scale_by_height)

    scaled_w = round(art.width * scale)
    scaled_h = round(art.height * scale)
    scaled = art.resize((scaled_w, scaled_h), Image.LANCZOS)

    # Center-crop to slot dimensions
    left = (scaled_w - slot.width) // 2
    top = (scaled_h - slot.height) // 2
    cropped = scaled.crop((left, top, left + slot.width, top + slot.height))
    return cropped


def find_smart_object_index(psd: PSDImage) -> int:
    """Return the top-level index of the first smart object layer.

    Raises ValueError if no smart object is present at the top level.
    """
    for i, layer in enumerate(psd):
        if layer.kind == "smartobject":
            return i
    raise ValueError("No smart object found at the top level of the PSD")


def compose_layer_aware(
    psd_path: Path,
    art: Image.Image,
    *,
    fill: bool = False,
) -> Image.Image:
    """Render `psd_path` with its smart object replaced by `art`.

    Args:
        psd_path: Path to the PSD mockup template.
        art: The artwork to insert (RGBA).
        fill: If True, use `fill_to_slot` (scale-to-cover, crop excess)
              instead of `fit_to_slot` (scale-to-fit, pad with white).
              Use fill=True when the slot ratio doesn't match the art ratio
              and white padding bars are unacceptable.

    Three stages:
      1. Render layers BELOW the smart object via `psd.composite(layer_filter=...)`
         — gives the "scene with white poster + baked-in shadows".
      2. Blend the fitted/filled art into the slot using the smart object's
         real blend mode (NORMAL -> alpha composite, MULTIPLY -> pixel multiply),
         honoring opacity.
      3. Iterate layers ABOVE the smart object and alpha-composite each on top
         at its own (left, top) origin so foreground elements stay in front.

    Limitations (both raise or fall through intentionally):
      - Blend modes other than NORMAL and MULTIPLY are not wired up.
      - Perspective warp (`warpValue` != 0) is not applied. Inspect the PSD
        before use; see the CLAUDE.md inspection command.
    """
    psd = PSDImage.open(str(psd_path))
    so_idx = find_smart_object_index(psd)
    so_layer = psd[so_idx]
    slot = MockupSlot(
        left=so_layer.left,
        top=so_layer.top,
        right=so_layer.right,
        bottom=so_layer.bottom,
    )

    # Stage 1 — render everything below the smart object (by layer identity).
    below_ids = {id(psd[i]) for i in range(so_idx)}

    def below_filter(layer: object) -> bool:
        return id(layer) in below_ids and bool(getattr(layer, "visible", True))

    below = psd.composite(layer_filter=below_filter)
    if below is None:
        below = Image.new("RGB", psd.size, (255, 255, 255))
    canvas = below.convert("RGBA")

    # Stage 2 — blend the fitted/filled art at the slot bounds, honoring blend mode.
    fitted = fill_to_slot(art, slot) if fill else fit_to_slot(art, slot)
    slot_box = (slot.left, slot.top, slot.right, slot.bottom)
    below_under_slot = canvas.crop(slot_box).convert("RGB")
    fitted_rgb = fitted.convert("RGB")

    blend_mode = so_layer.blend_mode
    if blend_mode == BlendMode.NORMAL:
        # Alpha-composite keeps fit_to_slot's white padding and masks.
        canvas.alpha_composite(fitted, (slot.left, slot.top))
        blended: Image.Image | None = None
    elif blend_mode == BlendMode.MULTIPLY:
        blended = ImageChops.multiply(below_under_slot, fitted_rgb)
    else:
        raise NotImplementedError(
            f"Blend mode {blend_mode!r} not wired up in layer_aware_composer. "
            f"Add an explicit branch for it before using this template."
        )

    if blended is not None:
        opacity = int(getattr(so_layer, "opacity", 255))
        if opacity < 255:
            blended = Image.blend(below_under_slot, blended, opacity / 255.0)
        canvas.paste(blended, (slot.left, slot.top))

    # Stage 3 — overlay each layer above the smart object at its own origin.
    for i in range(so_idx + 1, len(psd)):
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
