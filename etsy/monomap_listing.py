"""MonoMap-specific listing text generator.

Generates listing text matching the CustomHouse emoji format with
color options, HOW TO ORDER section, and custom-map tag for Gelato
placeholder workflow.

Usage:
    python -m etsy.monomap_listing --city chicago
    python -m etsy.monomap_listing --all
    python -m etsy.monomap_listing --preview chicago
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from etsy.city_list import ALL_CITIES, CityListing


# ---------------------------------------------------------------------------
# Coastal cities to skip (water rendering artifacts)
# ---------------------------------------------------------------------------

COASTAL_SKIP: set[str] = {
    "san_francisco", "seattle", "lisbon", "copenhagen", "honolulu",
}

# ---------------------------------------------------------------------------
# Title templates — rotated per city for variety
# ---------------------------------------------------------------------------

_TITLE_TEMPLATES: list[str] = [
    "{city} Map Print | Monochrome City Art, Choose Your Color, {gift}",
    "{city} Monochrome Map Wall Art | Bold City Poster, 6 Colors, {gift}",
    "{city} Map Poster | Minimalist Monochrome Art, Choose Your Color, {gift}",
    "Monochrome {city} Map Print | Bold City Wall Art, 6 Colors, {gift}",
    "{city} Map Art Print | Monochrome City Poster, Choose Your Color, {gift}",
    "{city} City Map Print | Bold Monochrome Wall Art, 6 Color Options, {gift}",
]

_GIFT_KEYWORDS: list[str] = [
    "Housewarming Gift",
    "New Home Gift",
    "Anniversary Gift",
    "Travel Gift",
    "Birthday Gift",
    "Moving Away Gift",
    "Graduation Gift",
]

# ---------------------------------------------------------------------------
# Tags — 13 max, must include custom-map
# ---------------------------------------------------------------------------

_BASE_TAGS: list[str] = [
    "monochrome map print",
    "bold city poster",
    "minimalist wall art",
    "choose your color",
    "custom-map",
    "modern map print",
    "city block art",
    "housewarming gift",
    "new home gift",
]

# ---------------------------------------------------------------------------
# SKU / pricing
# ---------------------------------------------------------------------------

_VARIATIONS = """\
GLC-MONO-DIG-8X10   | 8x10   | Digital   | $4.20
GLC-MONO-DIG-11X14  | 11x14  | Digital   | $5.04
GLC-MONO-DIG-16X20  | 16x20  | Digital   | $5.88
GLC-MONO-DIG-18X24  | 18x24  | Digital   | $6.72
GLC-MONO-DIG-24X36  | 24x36  | Digital   | $7.80
GLC-MONO-UNF-8X10   | 8x10   | Unframed  | $34.83
GLC-MONO-UNF-11X14  | 11x14  | Unframed  | $39.85
GLC-MONO-UNF-16X20  | 16x20  | Unframed  | $46.35
GLC-MONO-UNF-18X24  | 18x24  | Unframed  | $51.37
GLC-MONO-UNF-24X36  | 24x36  | Unframed  | $62.45
GLC-MONO-FBK-8X10   | 8x10   | Framed BK | $78.07
GLC-MONO-FBK-11X14  | 11x14  | Framed BK | $87.50
GLC-MONO-FBK-16X20  | 16x20  | Framed BK | $119.62
GLC-MONO-FBK-18X24  | 18x24  | Framed BK | $131.12
GLC-MONO-FBK-24X36  | 24x36  | Framed BK | $216.17
GLC-MONO-FWH-8X10   | 8x10   | Framed WH | $78.07
GLC-MONO-FWH-11X14  | 11x14  | Framed WH | $87.50
GLC-MONO-FWH-16X20  | 16x20  | Framed WH | $119.62
GLC-MONO-FWH-18X24  | 18x24  | Framed WH | $131.12
GLC-MONO-FWH-24X36  | 24x36  | Framed WH | $216.17"""


# ---------------------------------------------------------------------------
# City intro paragraphs (reuse from listing_generator where available)
# ---------------------------------------------------------------------------

def _get_city_intro(city: CityListing) -> str:
    """Get a city-specific intro or generate a generic one."""
    display_city = city.display_city or city.city
    display_state = city.display_subtitle or city.state
    return (
        f"A bold, minimalist map of {display_city}, {display_state} — "
        f"every city block transformed into a striking monochrome mosaic. "
        f"Choose from 6 rich color palettes to match your space."
    )


# ---------------------------------------------------------------------------
# Description builder
# ---------------------------------------------------------------------------

def _build_description(city: CityListing) -> str:
    """Build full description in CustomHouse emoji format."""
    display_city = city.display_city or city.city
    display_state = city.display_subtitle or city.state

    return f"""\
📍 {display_city.upper()} MONOCHROME MAP PRINT — {_get_city_intro(city)}

Each city block is individually colored in a single bold tone with crisp \
white streets revealing every road, path, and alley. The result is a \
stunning mosaic that's unique to {display_city}'s street grid.
———————————————————————
🔸 HOW TO ORDER 🔸
———————————————————————
In the personalization box, please include:
1. Your color choice (see options below)
2. Any special requests (custom text, etc.)
✉️ A digital preview will be sent for your approval before anything is printed or finalized.
———————————————————————
🎨 CHOOSE YOUR COLOR
———————————————————————
◈ Charcoal — classic medium grey
◈ Navy — deep sophisticated blue
◈ Forest — rich dark green
◈ Terracotta — warm burnt orange
◈ Dusty Rose — elegant mauve pink
◈ Black — bold near-black

See listing photos for color reference!
———————————————————————
🖼️ PRODUCT OPTIONS
———————————————————————
📲 DIGITAL DOWNLOAD
◈ Standard (1–2 Business Days)
◈ Print at home or at any local/online print shop

🖨️ PREMIUM UNFRAMED PRINT
◈ Printed on high-quality matte fine art paper
◈ Rich, vibrant colors with sharp detail
◈ Available in: 8x10 | 11x14 | 16x20 | 18x24 | 24x36
◈ Ships from the US via our premium print partner

🖼️ FRAMED PRINT
◈ Black or white frame, shipped ready to hang
◈ Museum-quality matte paper with archival inks
———————————————————————
📐 AVAILABLE SIZES
———————————————————————
◈ 8×10 inches (20×25 cm)
◈ 11×14 inches (28×36 cm)
◈ 16×20 inches (41×51 cm)
◈ 18×24 inches (46×61 cm)
◈ 24×36 inches (61×91 cm)
———————————————————————
✨ ABOUT THIS DESIGN
———————————————————————
This map is created by breaking {display_city}'s street network into \
individual city blocks. Each block is colored in your chosen hue with \
crisp white streets overlaid on top — revealing every road, footpath, \
and alley. The poster features the city name in modern lowercase \
typography with a color swatch bar and GPS coordinates.

Every map is rendered from professional OpenStreetMap data at 300+ DPI. \
No two cities look alike because no two street grids are alike.
———————————————————————
💛 MAKES A GREAT GIFT FOR:
———————————————————————
◈ Housewarming gifts — match any room's color scheme
◈ Travel memories — your favorite city in bold color
◈ Moving away gifts — a piece of home to take with you
◈ Anniversary & wedding gifts — personalized and unique
◈ Office or dorm decor — choose the color that fits
◈ Birthday gifts for city lovers
———————————————————————
❓ QUESTIONS?
———————————————————————
Feel free to message us — we're happy to help with custom requests, \
alternate colors, or anything else to make your print perfect.
━━━━━━━━━━━━━━━━━━━━━━━━━━

© GeoLine Collective — Cartography as Craft"""


# ---------------------------------------------------------------------------
# Title + tags
# ---------------------------------------------------------------------------

def _rotate(items: list, seed: str) -> str:
    idx = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(items)
    return items[idx]


def _build_title(city: CityListing) -> str:
    display_city = city.display_city or city.city
    template = _rotate(_TITLE_TEMPLATES, f"{city.slug}_monomap")
    gift = _rotate(_GIFT_KEYWORDS, f"{city.slug}_monomap_gift")
    title = template.format(city=display_city, gift=gift)
    return title[:140]


def _build_tags(city: CityListing) -> list[str]:
    display_city = city.display_city or city.city
    city_lower = display_city.lower()

    city_tags = [
        f"{city_lower} map print",
        f"{city_lower} wall art",
        f"{city_lower} poster",
        f"{city_lower} gift",
    ]

    all_tags = city_tags + _BASE_TAGS
    # Deduplicate, max 20 chars, max 13 tags
    seen: set[str] = set()
    result: list[str] = []
    for tag in all_tags:
        tag = tag.replace(".", "")[:20]  # Strip periods (Etsy rejects them)
        if tag not in seen:
            seen.add(tag)
            result.append(tag)
        if len(result) == 13:
            break
    return result


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_monomap_listing(slug: str, output_dir: str | None = None) -> str | None:
    """Generate MonoMap listing text file for a city.

    Returns output file path.
    """
    city: CityListing | None = None
    for c in ALL_CITIES:
        if c.slug == slug:
            city = c
            break
    if not city:
        print(f"City not found: {slug}")
        return None

    if slug in COASTAL_SKIP:
        print(f"Skipping coastal city: {slug}")
        return None

    title = _build_title(city)
    tags = _build_tags(city)
    description = _build_description(city)

    out_dir = Path(output_dir) if output_dir else Path("etsy/renders") / f"{slug}_monomap"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}_listing.txt"

    content = "\n".join([
        description,
        "",
        "———————————————————————",
        "TITLE",
        "———————————————————————",
        title,
        "",
        "———————————————————————",
        "TAGS",
        "———————————————————————",
        ", ".join(tags),
        "",
        "———————————————————————",
        "VARIATIONS (SKU / Size / Format / Price)",
        "———————————————————————",
        _VARIATIONS,
        "",
    ])

    out_path.write_text(content, encoding="utf-8")
    return str(out_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate MonoMap listing text")
    parser.add_argument("--city", "-c", help="Single city slug")
    parser.add_argument("--all", "-a", action="store_true", help="All cities")
    parser.add_argument("--preview", "-p", help="Preview one city to stdout")
    args = parser.parse_args()

    if args.preview:
        city = next((c for c in ALL_CITIES if c.slug == args.preview), None)
        if not city:
            print(f"City not found: {args.preview}")
            return
        sys.stdout.reconfigure(encoding="utf-8")
        print(f"TITLE ({len(_build_title(city))} chars):")
        print(f"  {_build_title(city)}")
        print(f"\nTAGS ({len(_build_tags(city))}):")
        for t in _build_tags(city):
            print(f"  - {t} ({len(t)} chars)")
        print(f"\nDESCRIPTION (first 500 chars):")
        print(f"  {_build_description(city)[:500]}...")
        return

    if args.all:
        generated = 0
        skipped = 0
        for city in ALL_CITIES:
            path = generate_monomap_listing(city.slug)
            if path:
                generated += 1
                print(f"  {path}")
            else:
                skipped += 1
        print(f"\nGenerated: {generated}, Skipped: {skipped}")
    elif args.city:
        path = generate_monomap_listing(args.city)
        if path:
            print(f"Generated: {path}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
