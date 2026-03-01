"""GeoLine Collective — PSD Mockup Compositor.

Composites rendered posters into purchased PSD mockup templates
using psd-tools + Pillow. No Photoshop required.

Each PSD has 3 layers:
  - Background (room scene)
  - Layer 1 (frame overlay)
  - "your design here" (smart object — defines placement bbox)

We render Background, paste our poster into the smart object bbox,
then render Layer 1 on top.

Usage:
    python -m etsy.mockup_psd --city Chicago                    # All templates
    python -m etsy.mockup_psd --city Chicago --templates 1 5 12  # Specific ones
    python -m etsy.mockup_psd --batch --templates 1 5 12 20 45   # All cities
    python -m etsy.mockup_psd --preview                          # List templates
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from pathlib import Path

from PIL import Image
from psd_tools import PSDImage

from etsy.batch_etsy_render import RENDERS_DIR
from etsy.city_list import ALL_CITIES, get_cities_by_tier, get_city

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

MOCKUP_DIR = os.path.join(os.path.dirname(__file__), "TUR2", "PSD Mockups")


def _list_mockup_files() -> list[tuple[int, str]]:
    """Return sorted list of (number, filepath) for all mockup PSDs."""
    files = glob.glob(os.path.join(MOCKUP_DIR, "Mockup*.psd"))
    results: list[tuple[int, str]] = []
    for f in files:
        name = os.path.basename(f)
        num_str = "".join(c for c in name if c.isdigit())
        if num_str:
            results.append((int(num_str), f))
    return sorted(results, key=lambda x: x[0])


# ---------------------------------------------------------------------------
# Compositor
# ---------------------------------------------------------------------------

def composite_mockup(poster_path: str, psd_path: str, output_path: str) -> str:
    """Composite a poster into a PSD mockup template.

    Args:
        poster_path: Path to the rendered poster PNG.
        psd_path: Path to the mockup PSD file.
        output_path: Where to save the final composite.

    Returns:
        The output path.
    """
    psd = PSDImage.open(psd_path)

    # Find layers by role
    # PSD order (bottom to top): Background -> Layer 1 (scene) -> smart object
    # The smart object uses Multiply blend mode on top of the scene.
    layers = list(psd)
    smart_obj = None
    scene_layers: list = []

    for layer in layers:
        if layer.name == "your design here":
            smart_obj = layer
        else:
            scene_layers.append(layer)

    if smart_obj is None:
        raise ValueError(f"No 'your design here' layer found in {psd_path}")

    # Get smart object placement bbox and blend settings
    x1, y1, x2, y2 = smart_obj.bbox
    frame_w = x2 - x1
    frame_h = y2 - y1
    so_opacity = smart_obj.opacity  # typically 232 (91%)

    # Inset: shrink the placement area slightly so poster sits inside frame
    # edges rather than bleeding over them
    inset = int(min(frame_w, frame_h) * 0.02)  # 2% inset
    ix1 = x1 + inset
    iy1 = y1 + inset
    ix2 = x2 - inset
    iy2 = y2 - inset
    inner_w = ix2 - ix1
    inner_h = iy2 - iy1

    # Load poster and resize to CONTAIN within the inset frame area
    # (fit entirely inside, preserving aspect ratio — no cropping)
    poster = Image.open(poster_path).convert("RGBA")
    pw, ph = poster.size

    # Scale to contain: fit entirely within the frame, preserving ratio
    scale = min(inner_w / pw, inner_h / ph)
    new_w = int(pw * scale)
    new_h = int(ph * scale)
    poster_resized = poster.resize((new_w, new_h), Image.LANCZOS)

    # Center the poster within the inset area
    offset_x = ix1 + (inner_w - new_w) // 2
    offset_y = iy1 + (inner_h - new_h) // 2

    # Build composite:
    # 1. Render the full scene (Background + Layer 1) as the base
    # 2. Apply poster on top using Multiply blend at smart object opacity
    #    Multiply lets frame shadows/texture show through the poster
    import numpy as np

    canvas = Image.new("RGBA", (psd.width, psd.height), (255, 255, 255, 255))

    for layer in scene_layers:
        if layer.visible:
            layer_img = layer.composite()
            if layer_img.mode != "RGBA":
                layer_img = layer_img.convert("RGBA")
            canvas = Image.alpha_composite(canvas, layer_img)

    # Apply poster with Multiply blend mode at the centered position
    # Multiply: result = (base * overlay) / 255
    base_crop = canvas.crop((offset_x, offset_y, offset_x + new_w, offset_y + new_h)).convert("RGB")
    poster_rgb = poster_resized.convert("RGB")

    base_arr = np.array(base_crop, dtype=np.float32)
    poster_arr = np.array(poster_rgb, dtype=np.float32)

    # Multiply blend
    blended = (base_arr * poster_arr) / 255.0

    # Apply opacity: lerp between base and blended
    alpha = so_opacity / 255.0
    result = base_arr * (1 - alpha) + blended * alpha
    result = np.clip(result, 0, 255).astype(np.uint8)

    result_img = Image.fromarray(result, "RGB").convert("RGBA")
    canvas.paste(result_img, (offset_x, offset_y))

    # Save as RGB
    final = canvas.convert("RGB")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final.save(output_path, "PNG", quality=95)
    return output_path


def generate_city_mockups(
    city_slug: str,
    template_nums: list[int] | None = None,
    output_dir: str | None = None,
) -> list[str]:
    """Generate mockup images for a city using PSD templates.

    Args:
        city_slug: City directory name (e.g. "chicago").
        template_nums: Which mockup numbers to use. None = all.
        output_dir: Override output directory.

    Returns:
        List of output file paths.
    """
    poster_path = os.path.join(
        RENDERS_DIR, city_slug, f"{city_slug}_16x20.png"
    )
    if not os.path.exists(poster_path):
        print(f"  [!] No poster found: {poster_path}")
        return []

    out_dir = output_dir or os.path.join(RENDERS_DIR, city_slug)
    all_mockups = _list_mockup_files()

    if template_nums:
        mockups = [(n, p) for n, p in all_mockups if n in template_nums]
    else:
        mockups = all_mockups

    results: list[str] = []
    for i, (num, psd_path) in enumerate(mockups, 1):
        out_path = os.path.join(out_dir, f"mockup_{num:03d}.png")
        print(f"  [{i}/{len(mockups)}] Mockup {num}...", end="", flush=True)
        try:
            composite_mockup(poster_path, psd_path, out_path)
            size_kb = os.path.getsize(out_path) / 1024
            print(f" done ({size_kb:.0f} KB)")
            results.append(out_path)
        except Exception as e:
            print(f" FAILED: {e}")

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate mockups from PSD templates")
    parser.add_argument("--city", type=str, help="City name")
    parser.add_argument("--batch", action="store_true", help="All rendered cities")
    parser.add_argument("--tier", type=int, help="Process cities by tier")
    parser.add_argument("--templates", type=int, nargs="+",
                        help="Mockup numbers to use (e.g. 1 5 12)")
    parser.add_argument("--preview", action="store_true",
                        help="List available mockup templates")
    args = parser.parse_args()

    if args.preview:
        mockups = _list_mockup_files()
        print(f"\n{len(mockups)} mockup templates available:\n")
        for num, path in mockups:
            psd = PSDImage.open(path)
            for layer in psd:
                if layer.name == "your design here":
                    x1, y1, x2, y2 = layer.bbox
                    w, h = x2 - x1, y2 - y1
                    print(f"  Mockup {num:3d}  —  frame {w}x{h}  ratio {w/h:.2f}")
                    break
        return

    if args.city:
        city = get_city(args.city)
        if not city:
            print(f"City not found: {args.city}")
            sys.exit(1)
        print(f"\nGenerating mockups for {city.city}...")
        results = generate_city_mockups(city.slug, args.templates)
        print(f"\nDone: {len(results)} mockups saved")

    elif args.batch or args.tier:
        if args.tier:
            cities = get_cities_by_tier(args.tier)
        else:
            # All rendered cities
            cities = []
            for d in sorted(Path(RENDERS_DIR).iterdir()):
                if not d.is_dir():
                    continue
                poster = d / f"{d.name}_16x20.png"
                if poster.exists():
                    from etsy.city_list import CityListing
                    city = get_city(d.name.replace("_", " "))
                    if city:
                        cities.append(city)

        for i, city in enumerate(cities, 1):
            print(f"\n[{i}/{len(cities)}] {city.city}")
            generate_city_mockups(city.slug, args.templates)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
