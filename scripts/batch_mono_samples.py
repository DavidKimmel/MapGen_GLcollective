"""Render monochrome Florence samples — 5 cities × 6 colors × 3 sizes.

Uses master crop approach: one master at 24x36 per city/color, crop to other sizes.
Output: etsy/renders/MonoMap/{color}/{slug}_{size}.png
"""

import gc
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from PIL import Image
from engine.florence_renderer import render_florence_map
from engine.florence_text_layout import compose_florence_poster as compose

FONTS_DIR = os.path.join(PROJECT_ROOT, "fonts")
OUT_DIR = os.path.join("etsy", "renders", "MonoMap")
SIZES = ["11x14", "16x20", "24x36"]
DPI = 300

CITIES: list[dict] = [
    {"name": "Chicago", "state": "Illinois", "lat": 41.8827, "lon": -87.6353, "distance": 6000, "slug": "chicago"},
    {"name": "Paris", "state": "France", "lat": 48.8566, "lon": 2.3522, "distance": 5000, "slug": "paris"},
    {"name": "Nashville", "state": "Tennessee", "lat": 36.1627, "lon": -86.7816, "distance": 5500, "slug": "nashville"},
    {"name": "Berlin", "state": "Germany", "lat": 52.5200, "lon": 13.4050, "distance": 6000, "slug": "berlin"},
    {"name": "Rome", "state": "Italy", "lat": 41.9028, "lon": 12.4964, "distance": 5000, "slug": "rome"},
]

COLORS: dict[str, dict] = {
    "charcoal": {
        "hex": "#4A4A4A",
        "text_color": "#4A4A4A",
    },
    "navy": {
        "hex": "#1C3D6E",
        "text_color": "#1C3D6E",
    },
    "forest": {
        "hex": "#2A5A2A",
        "text_color": "#2A5A2A",
    },
    "terracotta": {
        "hex": "#B5553A",
        "text_color": "#B5553A",
    },
    "dusty_rose": {
        "hex": "#A35580",
        "text_color": "#A35580",
    },
    "black": {
        "hex": "#1A1A1A",
        "text_color": "#1A1A1A",
    },
}

# Size configs (width_in, height_in)
SIZE_DIMS: dict[str, tuple[int, int]] = {
    "8x10": (8, 10),
    "11x14": (11, 14),
    "16x20": (16, 20),
    "18x24": (18, 24),
    "24x36": (24, 36),
}


def render_city_color(city: dict, color_name: str, color_data: dict) -> None:
    """Render one city in one color at all 3 sizes via master crop."""
    slug = city["slug"]
    hex_color = color_data["hex"]
    text_color = color_data["text_color"]
    font_path = os.path.join(FONTS_DIR, "Switzer-Bold.ttf")

    color_dir = os.path.join(OUT_DIR, color_name)
    os.makedirs(color_dir, exist_ok=True)

    # Check if all 3 sizes already exist
    all_exist = all(
        os.path.exists(os.path.join(color_dir, f"{slug}_{s}.png"))
        for s in SIZES
    )
    if all_exist:
        print(f"    All sizes exist — skipping")
        return

    # Render master at 24x36 aspect
    master_w, master_h = 24, 36
    master_path = os.path.join(color_dir, f"_master_{slug}.png")

    render_florence_map(
        lat=city["lat"], lon=city["lon"], radius=city["distance"],
        palette=[hex_color],
        bg_color="#FFFFFF",
        water_color="#FFFFFF",
        street_color="#FFFFFF",
        dpi=DPI,
        fig_width=master_w, fig_height=master_h,
        output_path=master_path,
    )

    master_img = Image.open(master_path).convert("RGB")
    master_px_w, master_px_h = master_img.size
    print(f"    Master: {master_px_w}x{master_px_h} px")

    for size_name in SIZES:
        out_path = os.path.join(color_dir, f"{slug}_{size_name}.png")
        w_in, h_in = SIZE_DIMS[size_name]
        target_aspect = h_in / w_in
        master_aspect = master_h / master_w  # 1.5

        # Crop master to target aspect
        if target_aspect < master_aspect:
            crop_h = int(master_px_w * target_aspect)
            y_offset = (master_px_h - crop_h) // 2
            cropped = master_img.crop((0, y_offset, master_px_w, y_offset + crop_h))
        else:
            cropped = master_img

        # Save cropped map to temp
        tmp_crop = os.path.join(color_dir, f"_crop_{slug}_{size_name}.png")
        cropped.save(tmp_crop)

        # Compose poster with text
        compose(
            map_image_path=tmp_crop,
            city_name=city["name"],
            state_or_region=city["state"],
            lat=city["lat"], lon=city["lon"],
            palette=[hex_color],
            size_name=size_name,
            dpi=DPI,
            bg_color="#FFFFFF",
            text_color=text_color,
            font_path=font_path,
            output_path=out_path,
        )

        os.remove(tmp_crop)
        size_mb = os.path.getsize(out_path) / 1e6
        print(f"    {size_name} — OK ({size_mb:.1f} MB)")

    # Clean up master
    if os.path.exists(master_path):
        os.remove(master_path)

    import matplotlib.pyplot as plt
    plt.close("all")
    gc.collect()


def main():
    total = len(CITIES) * len(COLORS)
    print(f"\nMonochrome Samples — {len(CITIES)} cities × {len(COLORS)} colors × {len(SIZES)} sizes")
    print(f"Output: {OUT_DIR}/{{color}}/{{slug}}_{{size}}.png\n")

    count = 0
    for city in CITIES:
        for color_name, color_data in COLORS.items():
            count += 1
            print(f"[{count}/{total}] {city['name']} — {color_name}")
            render_city_color(city, color_name, color_data)

    # Count output files
    total_files = sum(
        len([f for f in os.listdir(os.path.join(OUT_DIR, d)) if f.endswith(".png") and not f.startswith("_")])
        for d in os.listdir(OUT_DIR)
        if os.path.isdir(os.path.join(OUT_DIR, d))
    )
    print(f"\nDone! {total_files} files in {OUT_DIR}/")


if __name__ == "__main__":
    main()
