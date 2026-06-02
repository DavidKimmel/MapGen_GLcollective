"""Blueprint-specific listing text generator.

Follows the same format as Florence listings (batch_florence_postprocess.py)
with Blueprint-specific titles, tags, description, and color options.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from etsy.city_list import ALL_CITIES, CityListing


_TITLE_TEMPLATES = [
    "{city} Map Print, Detailed Mosaic Wall Art, Shaded City Block Poster, {gift}",
    "{city} Map Art Print, Modern City Mosaic Poster, Choose Your Color, {gift}",
    "{city} Map Wall Art, Shaded Mosaic Street Map, Detailed City Block Print, {gift}",
    "{city} City Map Print, Mosaic Wall Art, Choose Your Color, {gift}",
    "{city} Map Poster, Detailed Mosaic City Art, Shaded Street Map Print, {gift}",
]

_GIFT_KEYWORDS = [
    "Housewarming Gift",
    "New Home Gift",
    "Anniversary Gift",
    "Travel Gift",
    "Graduation Gift",
    "Birthday Gift",
]

_TAGS = [
    "mosaic map art",
    "mosaic city print",
    "detailed street map",
    "shaded map poster",
    "custom-map",
    "modern wall art",
    "housewarming gift",
    "new home gift",
    "choose your color",
]

_VARIATIONS = """VARIATIONS (SKU / Size / Format / Price)
GLC-BLUE-DIG-8x10   | 8x10   | Digital   | $4.20
GLC-BLUE-DIG-11x14  | 11x14  | Digital   | $5.04
GLC-BLUE-DIG-16x20  | 16x20  | Digital   | $5.88
GLC-BLUE-DIG-18x24  | 18x24  | Digital   | $6.72
GLC-BLUE-DIG-24x36  | 24x36  | Digital   | $7.80
GLC-BLUE-UNF-8x10   | 8x10   | Unframed  | $34.83
GLC-BLUE-UNF-11x14  | 11x14  | Unframed  | $39.85
GLC-BLUE-UNF-16x20  | 16x20  | Unframed  | $46.35
GLC-BLUE-UNF-18x24  | 18x24  | Unframed  | $51.37
GLC-BLUE-UNF-24x36  | 24x36  | Unframed  | $62.45
GLC-BLUE-FBK-8x10   | 8x10   | Framed BK | $78.07
GLC-BLUE-FBK-11x14  | 11x14  | Framed BK | $87.50
GLC-BLUE-FBK-16x20  | 16x20  | Framed BK | $119.62
GLC-BLUE-FBK-18x24  | 18x24  | Framed BK | $131.12
GLC-BLUE-FBK-24x36  | 24x36  | Framed BK | $216.17
GLC-BLUE-FWH-8x10   | 8x10   | Framed WH | $78.07
GLC-BLUE-FWH-11x14  | 11x14  | Framed WH | $87.50
GLC-BLUE-FWH-16x20  | 16x20  | Framed WH | $119.62
GLC-BLUE-FWH-18x24  | 18x24  | Framed WH | $131.12
GLC-BLUE-FWH-24x36  | 24x36  | Framed WH | $216.17
"""


def generate_blueprint_listing_text(slug: str, output_dir: str | None = None) -> str | None:
    """Generate Blueprint-specific listing text file.

    Follows the Florence listing format with Blueprint-specific content
    including color options section.

    Returns output file path.
    """
    city: CityListing | None = None
    for c in ALL_CITIES:
        if c.slug == slug or (slug == "manhattan" and c.city == "New York"):
            city = c
            break
    if not city:
        return None

    display_city = "Manhattan" if slug == "manhattan" else city.city
    display_state = (
        "New York" if slug == "manhattan"
        else (city.state if city.country == "USA" else city.country)
    )
    location_label = f"{display_city}, {display_state}"

    # Title
    idx = int(hashlib.md5(slug.encode()).hexdigest(), 16)
    title_template = _TITLE_TEMPLATES[idx % len(_TITLE_TEMPLATES)]
    gift = _GIFT_KEYWORDS[idx % len(_GIFT_KEYWORDS)]
    title = title_template.format(city=display_city, gift=gift)
    if len(title) > 140:
        title = f"{display_city} Map Print | Detailed Mosaic City Wall Art, {gift}"
    title = title[:140]

    # Tags
    city_lower = display_city.lower()
    tags = [
        f"{city_lower} map print",
        f"{city_lower} wall art",
        f"{city_lower} poster",
        f"{city_lower} gift",
    ] + _TAGS

    # Description
    description = f"""The perfect piece for anyone who loves {display_city}. This detailed mosaic map transforms the streets of {location_label} into a beautifully shaded work of art.

Every city block is shaded in 8 tones of a single color — from deep dark to soft light — with every street, path, and alley rendered as a crisp white overlay. The result is an incredibly detailed map that reveals the city's unique street grid, parks, and waterways.

CHOOSE YOUR COLOR
✦ Navy — deep blues from midnight to sky
✦ Forest — rich greens from pine to sage
✦ Terracotta — warm earth tones from espresso to peach
✦ Charcoal — elegant greys from black to silver
Please specify your color choice in the personalization box.

WHAT YOU GET
✦ Digital Download — High-resolution 300 DPI PNG file, ready to print at home or at any print shop
✦ Physical Print — Museum-quality poster printed on premium matte paper, shipped directly to you via our print partner
✦ Framed Option — Choose black or white frame in any size

AVAILABLE SIZES
✦ 8×10 inches (20×25 cm)
✦ 11×14 inches (28×36 cm)
✦ 16×20 inches (41×51 cm)
✦ 18×24 inches (46×61 cm)
✦ 24×36 inches (61×91 cm)

ABOUT THIS DESIGN
This map is created by breaking {display_city}'s street network into individual city blocks using a technique called polygonization. Each block receives a shade from our curated 8-tone palette, creating a richly detailed mosaic that is unique to this city's geography. A detailed white road overlay reveals every street, alley, and path — including footways and cycleways that other maps miss.

Perfect as a housewarming gift, travel memento, or statement piece for any room. Each city's map is as unique as the city itself.

SHIPPING & DELIVERY
✦ Digital downloads are available instantly after purchase
✦ Physical prints ship within 2-5 business days via our print partner
✦ Framed prints ship within 5-7 business days
"""

    # Build listing file
    out_dir = Path(output_dir) if output_dir else Path("etsy/renders") / f"{slug}_blueprint"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}_listing.txt"

    lines = [
        "=" * 70,
        f"ETSY LISTING — {location_label} (Blueprint Style)",
        "=" * 70,
        "",
        "TITLE",
        "-" * 40,
        title,
        "",
        "TAGS",
        "-" * 40,
        ", ".join(tags),
        "",
        "DESCRIPTION",
        "-" * 40,
        description,
        "VARIATIONS",
        "-" * 40,
        _VARIATIONS,
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return str(out_path)
