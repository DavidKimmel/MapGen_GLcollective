"""Generate mockups for CustomMapPack — flat + lifestyle PSD templates.

Each style gets 7 flat mockups (all listings) + 3 lifestyle mockups (print only).
Multi-frame mockups use filler cities from the same style.
For styles with color variants, fillers use different colors.
"""

import os
import sys
from pathlib import Path

from PIL import Image
from psd_tools import PSDImage

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from etsy.mockup_composer import (
    ALL_MOCKUPS, PRINT_MOCKUPS, LIFESTYLE_MOCKUPS,
    MOCKUP_DIR, MockupDef, MockupSlot,
    get_smart_object_slots, fit_to_slot,
)

RENDERS_DIR = Path("etsy/renders")
OUT_BASE = Path("etsy/renders/CustomMapPack")


# ─── RENDER LOCATORS PER STYLE ───────────────────────────────────────────────

def find_classic_render(city_slug: str, size: str) -> Path | None:
    """Find a Classic (37th_parallel) render."""
    # Check DefaultMap_Posted first
    p = RENDERS_DIR / "DefaultMap_Posted" / city_slug / f"{city_slug}_{size}.png"
    if p.exists():
        return p
    # Check CustomMapPack renders
    p = OUT_BASE / "classic_digital" / f"{city_slug}_{size}.png"
    if p.exists():
        return p
    return None


def find_florence_render(city_slug: str, size: str) -> Path | None:
    """Find a Florence render."""
    p = RENDERS_DIR / "FlorenceMap_Posted" / f"{city_slug}_florence" / f"{city_slug}_{size}.png"
    if p.exists():
        return p
    p = OUT_BASE / "florence_digital" / f"{city_slug}_{size}.png"
    if p.exists():
        return p
    return None


def find_mono_render(city_slug: str, color: str, size: str) -> Path | None:
    """Find a MonoMap render."""
    p = RENDERS_DIR / "MonoMap" / color / f"{city_slug}_{size}.png"
    if p.exists():
        return p
    p = OUT_BASE / "monomap_digital" / f"{city_slug}_{color}_{size}.png"
    if p.exists():
        return p
    return None


def find_blueprint_render(city_slug: str, color: str, size: str) -> Path | None:
    """Find a Blueprint render — ONLY v3c layout (BlueprintV3/).

    Never use GradientMap/ (old fading bar) or CustomMapPack/ (old florence-style
    bottom title) as they have inconsistent layouts.
    """
    p = RENDERS_DIR / "BlueprintV3" / f"{city_slug}_{color}_{size}.png"
    if p.exists():
        return p
    return None


def load_render(path: Path) -> Image.Image:
    return Image.open(str(path)).convert("RGBA")


def best_available_render(
    finder, city_slug: str, target_size: str, *extra_args
) -> Image.Image | None:
    """Try target size first, then fall back to other sizes."""
    # Try exact size
    p = finder(city_slug, *extra_args, target_size)
    if p:
        return load_render(p)

    # Fallback sizes — prefer closest to target
    fallbacks = {
        "18x24": ["24x36", "16x20", "11x14"],
        "24x36": ["18x24", "16x20", "11x14"],
        "16x20": ["18x24", "24x36", "11x14"],
    }
    for fb_size in fallbacks.get(target_size, []):
        p = finder(city_slug, *extra_args, fb_size)
        if p:
            return load_render(p)
    return None


# ─── STYLE CONFIGURATIONS ────────────────────────────────────────────────────

STYLE_CONFIGS = {
    "classic": {
        "featured_city": "washington_dc",
        "filler_cities": ["pittsburgh", "new_orleans", "amsterdam"],
        "finder": find_classic_render,
        "extra_args": [],
    },
    "florence": {
        "featured_city": "amsterdam",
        "filler_cities": ["pittsburgh", "new_orleans", "washington_dc"],
        "finder": find_florence_render,
        "extra_args": [],
    },
    "monomap": {
        "featured_city": "nashville",
        "featured_color": "navy",
        # Each filler is (city, color) — mix colors to showcase variety
        "fillers_with_color": [
            ("berlin", "forest"),
            ("chicago", "terracotta"),
            ("paris", "dusty_rose"),
            ("rome", "charcoal"),
        ],
        "finder": find_mono_render,
    },
    "blueprint": {
        "featured_city": "amsterdam",
        "featured_color": "terracotta",
        # Each filler is (city, color) — mix colors to showcase variety
        "fillers_with_color": [
            ("berlin", "navy"),
            ("nashville", "forest"),
            ("chicago", "charcoal"),
        ],
        "finder": find_blueprint_render,
    },
}


def compose_mockup_generic(
    mockup_def: MockupDef,
    featured_render: Image.Image,
    filler_renders: list[Image.Image],
    output_path: Path,
) -> Path:
    """Compose renders into a mockup PSD template."""
    psd_path = Path(mockup_def.filename) if Path(mockup_def.filename).is_absolute() else MOCKUP_DIR / mockup_def.filename
    psd = PSDImage.open(str(psd_path))
    base = psd.composite().convert("RGBA")

    if mockup_def.use_smart_object_bounds:
        slots = get_smart_object_slots(psd)
    else:
        slots = list(mockup_def.slots)

    if not slots:
        raise ValueError(f"No artwork slots in {mockup_def.filename}")

    filler_idx = 0
    for i, slot in enumerate(slots):
        if i == mockup_def.featured_slot:
            fitted = fit_to_slot(featured_render, slot)
        else:
            if filler_idx < len(filler_renders):
                fitted = fit_to_slot(filler_renders[filler_idx], slot)
                filler_idx += 1
            else:
                fitted = fit_to_slot(featured_render, slot)
        base.paste(fitted, (slot.left, slot.top), fitted)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(str(output_path), "JPEG", quality=95)
    return output_path


def generate_mockups_for_style(
    style_name: str,
    mockup_list: list[MockupDef] | None = None,
    out_suffix: str = "digital",
) -> None:
    """Generate mockups for a style.

    For styles with color variants (monomap, blueprint), fillers use different
    colors to showcase the range in multi-frame mockups.
    """
    if mockup_list is None:
        mockup_list = ALL_MOCKUPS
    config = STYLE_CONFIGS[style_name]
    out_dir = OUT_BASE / f"{style_name}_{out_suffix}"
    out_dir.mkdir(parents=True, exist_ok=True)

    featured_city = config["featured_city"]
    finder = config["finder"]
    has_colors = "featured_color" in config
    featured_extra = [config["featured_color"]] if has_colors else []

    # Build filler list — either (city,) or (city, color) tuples
    if "fillers_with_color" in config:
        filler_specs = config["fillers_with_color"]  # list of (city, color)
    else:
        filler_specs = [(c,) for c in config.get("filler_cities", [])]

    print(f"\n=== {style_name.upper()} mockups ===")

    for mockup_def in mockup_list:
        out_path = out_dir / f"mockup_{mockup_def.short_name}.jpg"

        # Load featured render
        featured = best_available_render(
            finder, featured_city, mockup_def.render_size, *featured_extra
        )
        if featured is None:
            print(f"  SKIP {mockup_def.short_name}: no render for {featured_city}")
            continue

        # Count slots in this mockup
        psd_path = MOCKUP_DIR / mockup_def.filename
        if mockup_def.use_smart_object_bounds:
            psd = PSDImage.open(str(psd_path))
            num_slots = len(get_smart_object_slots(psd))
        else:
            num_slots = len(mockup_def.slots)

        # Load fillers — each with its own city+color combo
        fillers: list[Image.Image] = []
        if num_slots > 1:
            for spec in filler_specs:
                filler = best_available_render(
                    finder, spec[0], mockup_def.render_size, *spec[1:]
                )
                if filler:
                    fillers.append(filler)
                if len(fillers) >= num_slots - 1:
                    break

        try:
            result = compose_mockup_generic(mockup_def, featured, fillers, out_path)
            mb = os.path.getsize(str(result)) / 1e6
            print(f"  {mockup_def.short_name}: {result.name} ({mb:.1f} MB)")
        except Exception as e:
            print(f"  ERROR {mockup_def.short_name}: {e}")


def main():
    print("=== CustomMapPack Mockup Generator ===")

    for style in ["classic", "florence", "monomap", "blueprint"]:
        # Flat mockups → digital folder (shared with print)
        generate_mockups_for_style(style, ALL_MOCKUPS, "digital")
        # Lifestyle mockups → print folder only
        generate_mockups_for_style(style, LIFESTYLE_MOCKUPS, "print")

    print("\n=== Done! ===")
    for style in ["classic", "florence", "monomap", "blueprint"]:
        for suffix in ["digital", "print"]:
            d = OUT_BASE / f"{style}_{suffix}"
            mockup_files = sorted(f.name for f in d.glob("mockup_*.jpg"))
            print(f"  {style}_{suffix}: {len(mockup_files)} mockups")


if __name__ == "__main__":
    main()
