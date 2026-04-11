"""Test composer: render atlanta 24x36 into the 3 new PosterMockup PSDs.

One-off smoke test for `etsy.layer_aware_composer.compose_layer_aware`.
For the production batch over all MonoMap cities, see
`scripts/compose_monomap_new_mockups.py`.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from etsy.layer_aware_composer import compose_layer_aware


POSTER_DIR = Path(r"C:\MapGen_GLcollective\etsy\TUR2\PosterMockup")
RENDER_DIR = Path(
    r"C:\MapGen_GLcollective\etsy\renders\POSTED\MonoMap_Posted\atlanta_monomap"
)
OUT_DIR = Path(
    r"C:\MapGen_GLcollective\etsy\renders\POSTED_CLEAN\MonoMap_Posted\atlanta_monomap"
)

# (psd_file, short_name, [(color_label, render_suffix), ...])
JOBS: list[tuple[str, str, list[tuple[str, str]]]] = [
    (
        "Framemockup _2x3_65.psd",
        "frame_wall",
        [("charcoal", "charcoal"), ("navy", "")],
    ),
    (
        "PSD (1).psd",
        "flatlay",
        [("forest", "forest"), ("dusty_rose", "dusty_rose")],
    ),
    (
        "Frame_038.psd",
        "frame_boho",
        [("terracotta", "terracotta"), ("black", "black")],
    ),
]


def load_render(color_suffix: str) -> Image.Image:
    fname = (
        "atlanta_24x36.png"
        if color_suffix == ""
        else f"atlanta_{color_suffix}_24x36.png"
    )
    path = RENDER_DIR / fname
    if not path.exists():
        raise FileNotFoundError(f"Missing render: {path}")
    return Image.open(str(path)).convert("RGBA")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for psd_name, short, color_jobs in JOBS:
        psd_path = POSTER_DIR / psd_name
        for color_label, suffix in color_jobs:
            art = load_render(suffix)
            composed = compose_layer_aware(psd_path, art)
            out = OUT_DIR / f"atlanta_{color_label}_{short}.jpg"
            composed.convert("RGB").save(str(out), "JPEG", quality=95)
            print(f"  wrote {out.name}")


if __name__ == "__main__":
    main()
