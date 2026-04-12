"""Generate mockup images for the AtlasMap listing.

Uses the same 3 PosterMockup PSDs and layer_aware_composer as MonoMap.
Picks visually impressive vertical states for the lifestyle mockups.

Output: etsy/renders/AtlasMap/new_mockups/
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from etsy.layer_aware_composer import compose_layer_aware


ATLAS_DIR = Path(r"C:\MapGen_GLcollective\etsy\renders\AtlasMap\print_ready")
OUT_DIR = Path(r"C:\MapGen_GLcollective\etsy\renders\AtlasMap\new_mockups")
OUT_DIR_FILL = Path(r"C:\MapGen_GLcollective\etsy\renders\AtlasMap\new_mockups_fill")
POSTER_DIR = Path(r"C:\MapGen_GLcollective\etsy\TUR2\PosterMockup")

# Vertical states with the best visual impact for mockups
MOCKUP_STATES: list[tuple[str, str]] = [
    # (folder_name, size_suffix for the 24x36 render)
    ("California", "24x36"),
    ("Georgia", "24x36"),
    ("Idaho", "24x36"),
]

# PSD templates — same 3 from MonoMap
PSDS: list[tuple[str, str]] = [
    ("Framemockup _2x3_65.psd", "frame_wall"),
    ("PSD (1).psd", "flatlay"),
    ("Frame_038.psd", "frame_boho"),
]

# States for the 6-up grid showcase (mix of H and V, diverse geography)
GRID_STATES: list[tuple[str, str]] = [
    ("Colorado", "36x24"),     # H — Rocky Mountains
    ("California", "24x36"),   # V — Sierra Nevada + coast
    ("NewYork", "36x24"),      # H — Adirondacks + Hudson
    ("Georgia", "24x36"),      # V — Appalachians to coast
    ("Texas", "36x24"),        # H — plains to mountains
    ("Idaho", "24x36"),        # V — rugged Rockies
]


def find_render(state: str, size: str) -> Path:
    """Find the atlas render for a state at a given size."""
    folder = ATLAS_DIR / state
    # Pattern: {State}_atlas_atlas_classic_CormorantGaramondBold_{WxH}.png
    for f in folder.iterdir():
        if f.name.endswith(f"_{size}.png"):
            return f
    raise FileNotFoundError(f"No {size} render for {state}")


def generate_lifestyle_mockups(*, fill: bool = False) -> None:
    """Compose each mockup state into each PSD template."""
    out_dir = OUT_DIR_FILL if fill else OUT_DIR
    mode_label = "fill" if fill else "fit"
    for state, size in MOCKUP_STATES:
        render_path = find_render(state, size)
        art = Image.open(str(render_path)).convert("RGBA")
        state_lower = state.lower()

        for psd_name, short in PSDS:
            psd_path = POSTER_DIR / psd_name
            composed = compose_layer_aware(psd_path, art, fill=fill)
            out = out_dir / f"atlas_{state_lower}_{short}.jpg"
            composed.convert("RGB").save(str(out), "JPEG", quality=95)
            print(f"  [{mode_label}] wrote {out.name}")


def generate_detail_crop() -> None:
    """Create a detail crop from California showing terrain detail."""
    render_path = find_render("California", "24x36")
    img = Image.open(str(render_path)).convert("RGB")
    w, h = img.size

    # Crop center-upper area where the Sierra Nevada detail is richest
    crop_w = int(w * 0.5)
    crop_h = int(w * 0.5)  # square
    left = int(w * 0.2)
    top = int(h * 0.15)
    cropped = img.crop((left, top, left + crop_w, top + crop_h))
    cropped = cropped.resize((2000, 2000), Image.LANCZOS)

    out = OUT_DIR / "atlas_detail_crop.jpg"
    cropped.save(str(out), "JPEG", quality=92)
    print(f"  wrote {out.name}")


def generate_6up_grid() -> None:
    """Create a 3x2 grid showing 6 diverse states."""
    cell_w = 800
    cell_h = 1000  # approx 2:3 for vertical, will be letterboxed for H
    cols = 3
    rows = 2
    gap = 20
    bg_color = (240, 240, 240)

    canvas_w = cols * cell_w + (cols + 1) * gap
    canvas_h = rows * cell_h + (rows + 1) * gap
    canvas = Image.new("RGB", (canvas_w, canvas_h), bg_color)

    for idx, (state, size) in enumerate(GRID_STATES):
        col = idx % cols
        row = idx // cols
        x = gap + col * (cell_w + gap)
        y = gap + row * (cell_h + gap)

        render_path = find_render(state, size)
        img = Image.open(str(render_path)).convert("RGB")

        # Fit into cell preserving aspect ratio
        img_ratio = img.width / img.height
        cell_ratio = cell_w / cell_h

        if img_ratio > cell_ratio:
            # Wider than cell — fit by width
            new_w = cell_w
            new_h = int(cell_w / img_ratio)
        else:
            # Taller — fit by height
            new_h = cell_h
            new_w = int(cell_h * img_ratio)

        img_resized = img.resize((new_w, new_h), Image.LANCZOS)

        # Center in cell
        paste_x = x + (cell_w - new_w) // 2
        paste_y = y + (cell_h - new_h) // 2
        canvas.paste(img_resized, (paste_x, paste_y))

    out = OUT_DIR / "atlas_6state_grid.jpg"
    canvas.save(str(out), "JPEG", quality=92)
    print(f"  wrote {out.name}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR_FILL.mkdir(parents=True, exist_ok=True)

    print("Generating lifestyle mockups (fill mode — no white padding)...")
    generate_lifestyle_mockups(fill=True)

    print("\nGenerating detail crop...")
    # Detail crop goes into the fill dir (preferred version)
    generate_detail_crop()

    print("Generating 6-state showcase grid...")
    generate_6up_grid()

    print(f"\nDone. Compare:")
    print(f"  fit (original): {OUT_DIR}")
    print(f"  fill (no padding): {OUT_DIR_FILL}")


if __name__ == "__main__":
    main()
