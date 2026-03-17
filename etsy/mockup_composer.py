"""
Automated mockup composer — places city map renders into flat mockup PSDs.

Multi-frame mockups show the featured city in the primary slot and
filler cities (Pittsburgh, New Orleans, Washington DC, Amsterdam) in
the remaining slots.

Usage:
    # All cities into all mockups
    python -m etsy.mockup_composer

    # Specific city
    python -m etsy.mockup_composer --city seattle

    # Specific mockup
    python -m etsy.mockup_composer --mockup Main

    # List available mockups
    python -m etsy.mockup_composer --list
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from PIL import Image
from psd_tools import PSDImage


# ── Paths ──────────────────────────────────────────────────────────────────────

MOCKUP_DIR = Path(r"C:\MapGen_GLcollective\etsy\TUR2\Best\Flat")
RENDER_DIR = Path(r"C:\MapGen_GLcollective\etsy\renders")

# Filler cities for multi-frame mockups (visually interesting maps).
# If the featured city is one of these, it gets skipped and the next is used.
FILLER_CITIES: list[str] = [
    "pittsburgh",
    "new_orleans",
    "washington_dc",
    "amsterdam",
]


# ── Mockup definitions ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MockupSlot:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height


@dataclass(frozen=True)
class MockupDef:
    filename: str
    short_name: str
    render_size: str
    slots: list[MockupSlot]
    featured_slot: int = 0  # index into sorted slots (left-to-right) for featured city
    use_smart_object_bounds: bool = True


# Single-frame mockups — featured_slot defaults to 0
AUTO_MOCKUPS: list[MockupDef] = [
    MockupDef(
        filename="Main.psd",
        short_name="main",
        render_size="24x36",
        slots=[],
    ),
    MockupDef(
        filename="Mockup4.psd",
        short_name="mockup4",
        render_size="24x36",
        slots=[],
    ),
    MockupDef(
        filename="ONCE 1_PSD_Post.psd",
        short_name="once",
        render_size="18x24",
        slots=[],
    ),
    MockupDef(
        filename="VV1_PSD_Post.psd",
        short_name="vv1",
        render_size="18x24",
        slots=[],
    ),
    # 2 frames: featured on RIGHT (index 1 when sorted left-to-right)
    MockupDef(
        filename="2 Frames  - StudioBlank.psd",
        short_name="2frames",
        render_size="24x36",
        slots=[],
        featured_slot=1,
    ),
    # 3 frames: featured in MIDDLE (index 1 when sorted left-to-right)
    MockupDef(
        filename="CLS-4_PSD_Post.psd",
        short_name="cls4",
        render_size="24x36",
        slots=[],
        featured_slot=1,
    ),
]

# FramePSD: 2 frames, featured on RIGHT (index 1)
MANUAL_MOCKUPS: list[MockupDef] = [
    MockupDef(
        filename="FramePSD.psd",
        short_name="framepsd",
        render_size="24x36",
        slots=[
            MockupSlot(left=539, top=539, right=2109, bottom=2760),
            MockupSlot(left=2425, top=539, right=3995, bottom=2760),
        ],
        featured_slot=1,
        use_smart_object_bounds=False,
    ),
]

ALL_MOCKUPS: list[MockupDef] = AUTO_MOCKUPS + MANUAL_MOCKUPS


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_smart_object_slots(psd: PSDImage) -> list[MockupSlot]:
    """Extract artwork slots from smart object layers, sorted left-to-right."""
    slots: list[MockupSlot] = []
    for layer in psd.descendants():
        if layer.kind == "smartobject":
            w = layer.right - layer.left
            h = layer.bottom - layer.top
            if w > 0 and h > 0:
                slots.append(MockupSlot(
                    left=layer.left,
                    top=layer.top,
                    right=layer.right,
                    bottom=layer.bottom,
                ))
    # Sort left-to-right so index 0 = leftmost, 1 = middle/right, etc.
    slots.sort(key=lambda s: s.left)
    return slots


def find_city_render(city_slug: str, render_size: str) -> Path | None:
    """Find the render PNG for a city at a specific size.

    Searches both renders/ and renders/Posted/ directories.
    """
    render_path = RENDER_DIR / city_slug / f"{city_slug}_{render_size}.png"
    if render_path.exists():
        return render_path
    posted_path = RENDER_DIR / "Posted" / city_slug / f"{city_slug}_{render_size}.png"
    if posted_path.exists():
        return posted_path
    return None


def get_all_city_slugs() -> list[str]:
    """Return sorted list of city slugs that have renders."""
    slugs: list[str] = []
    if not RENDER_DIR.exists():
        return slugs
    for d in sorted(RENDER_DIR.iterdir()):
        if d.is_dir():
            for size in ["11x14", "16x20", "18x24", "24x36"]:
                if find_city_render(d.name, size) is not None:
                    slugs.append(d.name)
                    break
    return slugs


def get_filler_cities(featured_slug: str, count: int, render_size: str) -> list[str]:
    """Pick filler cities for multi-frame mockups, excluding the featured city."""
    fillers: list[str] = []
    for slug in FILLER_CITIES:
        if slug == featured_slug:
            continue
        if find_city_render(slug, render_size) is not None:
            fillers.append(slug)
        if len(fillers) == count:
            break
    return fillers


def fit_to_slot(city_render: Image.Image, slot: MockupSlot) -> Image.Image:
    """Fit a city render into a slot, preserving aspect ratio with white fill."""
    render_ratio = city_render.width / city_render.height
    slot_ratio = slot.aspect_ratio

    if abs(render_ratio - slot_ratio) < 0.01:
        return city_render.resize((slot.width, slot.height), Image.LANCZOS)

    # Fit to width, pad height with white
    scaled_w = slot.width
    scaled_h = round(slot.width / render_ratio)

    scaled = city_render.resize((scaled_w, scaled_h), Image.LANCZOS)

    canvas = Image.new("RGBA", (slot.width, slot.height), (255, 255, 255, 255))
    y_offset = (slot.height - scaled_h) // 2
    canvas.paste(scaled, (0, y_offset), scaled)
    return canvas


def load_render(city_slug: str, render_size: str) -> Image.Image | None:
    """Load a city render as RGBA, or None if not found."""
    path = find_city_render(city_slug, render_size)
    if path is None:
        return None
    return Image.open(str(path)).convert("RGBA")


# ── Compose ────────────────────────────────────────────────────────────────────

def compose_mockup(
    mockup_def: MockupDef,
    city_slug: str,
    city_render: Image.Image,
) -> Path:
    """Compose a city render into a mockup and save the result.

    For multi-slot mockups, the featured city goes in the designated slot
    and filler cities fill the remaining slots.
    """
    psd_path = MOCKUP_DIR / mockup_def.filename
    psd = PSDImage.open(str(psd_path))
    base = psd.composite().convert("RGBA")

    # Determine slots (sorted left-to-right)
    if mockup_def.use_smart_object_bounds:
        slots = get_smart_object_slots(psd)
    else:
        slots = list(mockup_def.slots)  # already in order

    if not slots:
        raise ValueError(f"No artwork slots found in {mockup_def.filename}")

    # Build the list of renders per slot
    num_fillers_needed = len(slots) - 1
    if num_fillers_needed > 0:
        filler_slugs = get_filler_cities(
            city_slug, num_fillers_needed, mockup_def.render_size
        )
        filler_renders: list[Image.Image] = []
        for slug in filler_slugs:
            img = load_render(slug, mockup_def.render_size)
            if img is not None:
                filler_renders.append(img)

        filler_idx = 0
        for i, slot in enumerate(slots):
            if i == mockup_def.featured_slot:
                fitted = fit_to_slot(city_render, slot)
            else:
                if filler_idx < len(filler_renders):
                    fitted = fit_to_slot(filler_renders[filler_idx], slot)
                    filler_idx += 1
                else:
                    fitted = fit_to_slot(city_render, slot)
            base.paste(fitted, (slot.left, slot.top), fitted)
    else:
        # Single-slot mockup
        fitted = fit_to_slot(city_render, slots[0])
        base.paste(fitted, (slots[0].left, slots[0].top), fitted)

    # Save as JPEG into the city's render folder
    city_render_dir = RENDER_DIR / city_slug
    city_render_dir.mkdir(parents=True, exist_ok=True)
    out_path = city_render_dir / f"{city_slug}_{mockup_def.short_name}.jpg"
    base.convert("RGB").save(str(out_path), "JPEG", quality=95)
    return out_path


# ── CLI ────────────────────────────────────────────────────────────────────────

def run(
    city_filter: str | None = None,
    mockup_filter: str | None = None,
) -> None:
    """Run mockup composition for selected cities and mockups."""

    if city_filter:
        city_slugs = [city_filter]
    else:
        city_slugs = get_all_city_slugs()

    if mockup_filter:
        mockup_filter_lower = mockup_filter.lower()
        mockups = [
            m for m in ALL_MOCKUPS
            if mockup_filter_lower in m.short_name.lower()
            or mockup_filter_lower in m.filename.lower()
        ]
        if not mockups:
            print(f"No mockup matching '{mockup_filter}'. Available:")
            for m in ALL_MOCKUPS:
                print(f"  {m.short_name}: {m.filename}")
            return
    else:
        mockups = ALL_MOCKUPS

    total = len(city_slugs) * len(mockups)
    count = 0

    print(f"Composing {len(city_slugs)} cities x {len(mockups)} mockups = {total} images")
    print(f"Output: {RENDER_DIR}/{{city_slug}}/\n")

    for city_slug in city_slugs:
        render_cache: dict[str, Image.Image] = {}

        for mockup_def in mockups:
            count += 1
            size = mockup_def.render_size

            if size not in render_cache:
                render_path = find_city_render(city_slug, size)
                if render_path is None:
                    print(f"  [{count}/{total}] SKIP {city_slug}_{mockup_def.short_name}: no {size} render")
                    continue
                render_cache[size] = Image.open(str(render_path)).convert("RGBA")

            if size not in render_cache:
                continue

            try:
                out_path = compose_mockup(
                    mockup_def, city_slug, render_cache[size],
                )
                print(f"  [{count}/{total}] {out_path.name} (using {size})")
            except Exception as e:
                print(f"  [{count}/{total}] ERROR {city_slug} + {mockup_def.short_name}: {e}")

    print(f"\nDone! {count} mockups saved to city render folders")


def list_mockups() -> None:
    """Print available mockups and their slot info."""
    for m in ALL_MOCKUPS:
        psd_path = MOCKUP_DIR / m.filename
        exists = psd_path.exists()
        if exists and m.use_smart_object_bounds:
            psd = PSDImage.open(str(psd_path))
            slots = get_smart_object_slots(psd)
        else:
            slots = m.slots
        slot_count = len(slots)
        if slots:
            ratio = f"{slots[0].aspect_ratio:.4f}"
        else:
            ratio = "?"
        featured = f"slot {m.featured_slot}" if slot_count > 1 else "only"
        status = "OK" if exists else "MISSING"
        print(f"  {m.short_name:12s} [{status}] {m.filename} — {slot_count} slot(s), featured={featured}, render={m.render_size}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Automated mockup composer")
    parser.add_argument("--city", type=str, help="City slug (e.g. 'seattle')")
    parser.add_argument("--mockup", type=str, help="Mockup name filter")
    parser.add_argument("--list", action="store_true", help="List available mockups")
    args = parser.parse_args()

    if args.list:
        list_mockups()
    else:
        run(city_filter=args.city, mockup_filter=args.mockup)


if __name__ == "__main__":
    main()
