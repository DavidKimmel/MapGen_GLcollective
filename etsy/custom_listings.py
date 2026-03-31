"""Custom map expansion listings — text generator for 5 new Etsy listings.

Each listing targets a specific occasion/style niche with tailored SEO.
All use existing renderers (Classic, Blueprint) with existing crops/pins.

Usage:
    python -m etsy.custom_listings --all                # Generate all 5
    python -m etsy.custom_listings --listing where_we_met  # Generate one
    python -m etsy.custom_listings --preview where_we_met  # Print to stdout
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from etsy.style_config import CUSTOM_EXPANSION_VARIANTS, VariantPrice


# ---------------------------------------------------------------------------
# Listing dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CustomListing:
    """Definition for one custom map Etsy listing."""
    slug: str
    sku_prefix: str
    title: str
    tags: list[str]
    description: str
    personalization_prompt: str
    shop_section_id: int = 57768965  # Custom Maps section
    variants: list[VariantPrice] = field(default_factory=lambda: list(CUSTOM_EXPANSION_VARIANTS))


# ---------------------------------------------------------------------------
# Listing 1: Where We Met
# ---------------------------------------------------------------------------

WHERE_WE_MET = CustomListing(
    slug="where_we_met",
    sku_prefix="GLC-MEET",
    title=(
        "Where We Met Map Print | Custom Heart Map, Anniversary Gift "
        "| Personalized Couple Map | Valentine's Day"
    ),
    tags=[
        "where we met map",
        "where it all began",
        "anniversary map gift",
        "couple map print",
        "personalized map gift",
        "custom heart map",
        "romantic map art",
        "engagement gift map",
        "valentine map print",
        "wedding location map",
        "first date map",
        "custom location print",
        "love map print",
    ],
    description="""\
📍 The place where your story began — captured in a beautiful custom map.

Mark the exact spot where you first met, had your first date, or fell in \
love. This personalized heart-shaped map print makes the perfect romantic \
gift for anniversaries, Valentine's Day, engagements, or weddings.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🔸 HOW TO ORDER

1. Add this listing to your cart
2. In the "Personalization" box, tell us:
   → Location where you met (city, address, or coordinates)
   → Names to display above the map (e.g., "Sarah & James")
   → Date (e.g., "June 15, 2019")
   → Style preference (see below)
   → Shape: Heart or Circle
3. We'll design your map and send a proof within 1-2 business days
4. After your approval, we deliver the final file or ship your print

━━━━━━━━━━━━━━━━━━━━━━━━━━

🎨 CHOOSE YOUR STYLE

◈ Classic White — clean black roads on white, blue water, green parks
◈ Midnight Blue — golden roads on deep navy, luxury atlas aesthetic
◈ Clay & Sage — warm clay tones with sage green, cool slate water
◈ Warm Beige — earthy neutrals with sepia tones, vintage feel

━━━━━━━━━━━━━━━━━━━━━━━━━━

🖼️ WHAT YOU GET

◈ Digital Download — High-resolution 300 DPI PNG, ready to print anywhere
◈ Physical Print — Museum-quality poster on premium matte paper
◈ Framed Option — Black or white frame, shipped ready to hang

━━━━━━━━━━━━━━━━━━━━━━━━━━

📐 AVAILABLE SIZES

◈ 8×10 inches (20×25 cm) — desk or shelf
◈ 11×14 inches (28×36 cm) — gallery wall
◈ 16×20 inches (41×51 cm) — statement piece
◈ 18×24 inches (46×61 cm) — large format
◈ 24×36 inches (61×91 cm) — above the sofa

━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ ABOUT THIS DESIGN

Your names appear elegantly above the heart-shaped map, with a heart pin \
marking the exact location where your story began. Below the map: your \
custom tagline, city name, and date.

Every map is rendered from professional cartographic data — capturing \
every street, park, waterway, and building footprint at 300+ DPI. \
No two maps are alike because no two cities are alike.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🚚 SHIPPING & DELIVERY

◈ Digital: Proof within 1-2 business days, final file after approval
◈ Physical prints: 2-3 days design + 3-5 days production + shipping
◈ Framed prints: 5-7 business days + shipping
◈ Ships from the US via our premium print partner

━━━━━━━━━━━━━━━━━━━━━━━━━━

💛 PERFECT FOR

♥ Anniversary gifts — celebrate where it all began
♥ Valentine's Day — the most romantic map gift
♥ Engagement gifts — the spot where they said yes
♥ Wedding gifts — a keepsake of the couple's story
♥ First date memories — because you never forget that place

━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ Questions? Message us anytime — we love helping you create the perfect map.

© GeoLine Collective — Cartography as Craft""",
    personalization_prompt=(
        "Please provide:\n"
        "1. Location where you met (city, address, or coordinates)\n"
        "2. Names to display above the map (e.g., 'Sarah & James')\n"
        "3. Date (e.g., 'June 15, 2019')\n"
        "4. Style: Classic White, Midnight Blue, Clay & Sage, or Warm Beige\n"
        "5. Shape: Heart or Circle"
    ),
)


# ---------------------------------------------------------------------------
# Listing 2: Graduation Map
# ---------------------------------------------------------------------------

GRADUATION_MAP = CustomListing(
    slug="graduation_map",
    sku_prefix="GLC-GRAD",
    title=(
        "Graduation Map Print | Custom College Town Map, Class of 2026 Gift "
        "| Personalized University Map"
    ),
    tags=[
        "graduation map print",
        "college graduation gift",
        "class of 2026 gift",
        "university map art",
        "campus city map",
        "personalized grad gift",
        "custom graduation art",
        "college town map",
        "senior gift map",
        "school map print",
        "graduation wall art",
        "commencement gift",
        "alma mater map",
    ],
    description="""\
📍 Celebrate their achievement with a map of the city where they earned it.

A custom map of their college town with a graduation cap pin marking \
the campus — the perfect keepsake for any graduate. Personalized with \
the university name, graduation year, and city.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🔸 HOW TO ORDER

1. Add this listing to your cart
2. In the "Personalization" box, tell us:
   → University or school name
   → City where the school is located
   → Graduation year or "Class of" text
   → Style preference (see below)
   → Shape: Full or Circle
3. We'll design your map and send a proof within 1-2 business days
4. After your approval, we deliver the final file or ship your print

━━━━━━━━━━━━━━━━━━━━━━━━━━

🎨 CHOOSE YOUR STYLE

◈ Classic White — clean black roads on white, blue water, green parks
◈ Midnight Blue — golden roads on deep navy, premium look
◈ Clay & Sage — warm earth tones, sophisticated and timeless

━━━━━━━━━━━━━━━━━━━━━━━━━━

🖼️ WHAT YOU GET

◈ Digital Download — High-resolution 300 DPI PNG, ready to print anywhere
◈ Physical Print — Museum-quality poster on premium matte paper
◈ Framed Option — Black or white frame, shipped ready to hang

━━━━━━━━━━━━━━━━━━━━━━━━━━

📐 AVAILABLE SIZES

◈ 8×10 inches (20×25 cm) — desk or dorm room
◈ 11×14 inches (28×36 cm) — gallery wall
◈ 16×20 inches (41×51 cm) — statement piece
◈ 18×24 inches (46×61 cm) — large format
◈ 24×36 inches (61×91 cm) — living room centerpiece

━━━━━━━━━━━━━━━━━━━━━━━━━━

🎓 ABOUT THIS DESIGN

Each map features a graduation cap pin at the campus location, with the \
university name displayed prominently below the map alongside the \
graduation year and city. Every street, park, and waterway surrounding \
the campus is captured in stunning cartographic detail at 300+ DPI.

A meaningful gift that captures not just where they studied — but the \
entire city that became their home for those formative years.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🚚 SHIPPING & DELIVERY

◈ Digital: Proof within 1-2 business days, final file after approval
◈ Physical prints: 2-3 days design + 3-5 days production + shipping
◈ Framed prints: 5-7 business days + shipping
◈ Ships from the US via our premium print partner

━━━━━━━━━━━━━━━━━━━━━━━━━━

💛 PERFECT FOR

🎓 College graduation gifts
🎓 High school graduation
🎓 PhD / Master's degree celebrations
🎓 Alumni nostalgia gifts
🎓 Dorm room or first apartment decor

━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ Questions? Message us anytime — we love helping you create the perfect map.

© GeoLine Collective — Cartography as Craft""",
    personalization_prompt=(
        "Please provide:\n"
        "1. University or school name\n"
        "2. City where the school is located\n"
        "3. Graduation year or 'Class of' text\n"
        "4. Style: Classic White, Midnight Blue, or Clay & Sage\n"
        "5. Shape: Full or Circle"
    ),
)


# ---------------------------------------------------------------------------
# Listing 3: Multi-Style Custom Map
# ---------------------------------------------------------------------------

MULTI_STYLE_MAP = CustomListing(
    slug="multi_style_map",
    sku_prefix="GLC-STYLE",
    title=(
        "Custom City Map Print - Choose Your Style | 6 Color Options "
        "| Personalized Map Art | Any Location"
    ),
    tags=[
        "custom city map print",
        "personalized map art",
        "choose your style map",
        "custom color map",
        "any city map poster",
        "housewarming map gift",
        "custom-map",
        "personalized wall art",
        "custom location print",
        "city map wall art",
        "map print art",
        "modern map poster",
        "travel map gift",
    ],
    description="""\
📍 Your city, your style — choose from 6 unique color palettes.

The same stunning street map rendered in the color that matches YOUR \
decor. Pick from our 6 curated styles — from clean black and white to \
warm vintage tones to luxurious midnight blue.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🔸 HOW TO ORDER

1. Add this listing to your cart
2. In the "Personalization" box, tell us:
   → Location (city, address, or coordinates)
   → Style choice (see the 6 options below)
   → Custom text (optional — default is city name + coordinates)
   → Pin: None, Heart, Pin, House, or Grad Cap
   → Shape: Full or Circle
3. We'll design your map and send a proof within 1-2 business days
4. After your approval, we deliver the final file or ship your print

━━━━━━━━━━━━━━━━━━━━━━━━━━

🎨 6 STYLE OPTIONS

◈ Classic B&W — timeless black roads on white, blue water, green parks
◈ Midnight Blue — luxurious gold roads on deep navy background
◈ Clay & Sage — warm clay tones with sage green accents
◈ Warm Beige — earthy sepia neutrals, vintage map feel
◈ Watercolor — soft painted water and parks on clean white
◈ Vintage — terracotta roads with sage parks and deep navy water

All 6 styles are shown in our listing photos so you can see exactly \
how your map will look.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🖼️ WHAT YOU GET

◈ Digital Download — High-resolution 300 DPI PNG, ready to print anywhere
◈ Physical Print — Museum-quality poster on premium matte paper
◈ Framed Option — Black or white frame, shipped ready to hang

━━━━━━━━━━━━━━━━━━━━━━━━━━

📐 AVAILABLE SIZES

◈ 8×10 inches (20×25 cm)
◈ 11×14 inches (28×36 cm)
◈ 16×20 inches (41×51 cm)
◈ 18×24 inches (46×61 cm)
◈ 24×36 inches (61×91 cm)

━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ ABOUT THIS DESIGN

Every map is rendered from professional OpenStreetMap cartographic data \
at 300+ DPI — capturing every street from highways to residential lanes, \
every park, waterway, and building footprint. The clean typography shows \
your city name, state, and coordinates.

◈ 5 pin styles available — heart, classic pin, house, or graduation cap
◈ Full rectangle or circle crop
◈ Custom text on up to 3 lines

━━━━━━━━━━━━━━━━━━━━━━━━━━

🚚 SHIPPING & DELIVERY

◈ Digital: Proof within 1-2 business days, final file after approval
◈ Physical prints: 2-3 days design + 3-5 days production + shipping
◈ Framed prints: 5-7 business days + shipping
◈ Ships from the US via our premium print partner

━━━━━━━━━━━━━━━━━━━━━━━━━━

💛 PERFECT FOR

♥ Housewarming gifts — match any room's color scheme
♥ Travel memories — your favorite city in your favorite color
♥ Moving away gifts — a piece of home in their style
♥ Anniversary & wedding gifts — personalized and unique
♥ Office or dorm decor — choose the palette that fits

━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ Questions? Message us anytime — we love helping you create the perfect map.

© GeoLine Collective — Cartography as Craft""",
    personalization_prompt=(
        "Please provide:\n"
        "1. Location (city, address, or coordinates)\n"
        "2. Style: Classic B&W, Midnight Blue, Clay & Sage, Warm Beige, "
        "Watercolor, or Vintage\n"
        "3. Custom text (optional — default is city name + coordinates)\n"
        "4. Pin: None, Heart, Pin, House, or Grad Cap\n"
        "5. Shape: Full or Circle"
    ),
)


# ---------------------------------------------------------------------------
# Listing 4: Born In Baby Map
# ---------------------------------------------------------------------------

BORN_IN_MAP = CustomListing(
    slug="born_in_map",
    sku_prefix="GLC-BABY",
    title=(
        "Baby Birth Map Print | Born In Custom City Map, Nursery Wall Art "
        "| Personalized Newborn Gift"
    ),
    tags=[
        "baby birth map",
        "born in map print",
        "nursery wall art",
        "newborn gift map",
        "baby shower gift",
        "birth city map",
        "personalized nursery",
        "custom baby map",
        "nursery decor art",
        "baby keepsake gift",
        "birth location map",
        "baby room wall art",
        "newborn keepsake",
    ],
    description="""\
📍 A beautiful map of the city where their journey began.

Celebrate a new arrival with a custom map of their birthplace — \
personalized with baby's name, birth date, and a heart pin marking \
the city. Rendered in soft, nursery-friendly color palettes.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🔸 HOW TO ORDER

1. Add this listing to your cart
2. In the "Personalization" box, tell us:
   → Birth city or location
   → Baby's name
   → Birth date (and optional details: weight, time)
   → Style preference (see below)
   → Shape: Circle or Full
3. We'll design your map and send a proof within 1-2 business days
4. After your approval, we deliver the final file or ship your print

━━━━━━━━━━━━━━━━━━━━━━━━━━

🎨 NURSERY-FRIENDLY STYLES

◈ Warm Beige — soft earthy neutrals, gentle sepia tones
◈ Clay & Sage — warm blush with soft green accents
◈ Watercolor — painted pastels on clean white canvas

All three styles use muted, calming color palettes that complement \
any nursery decor.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🖼️ WHAT YOU GET

◈ Digital Download — High-resolution 300 DPI PNG, ready to print anywhere
◈ Physical Print — Museum-quality poster on premium matte paper
◈ Framed Option — Black or white frame, shipped ready to hang

━━━━━━━━━━━━━━━━━━━━━━━━━━

📐 AVAILABLE SIZES

◈ 8×10 inches (20×25 cm) — above the crib
◈ 11×14 inches (28×36 cm) — nursery gallery wall
◈ 16×20 inches (41×51 cm) — statement piece
◈ 18×24 inches (46×61 cm) — large nursery wall
◈ 24×36 inches (61×91 cm) — feature wall

━━━━━━━━━━━━━━━━━━━━━━━━━━

🍼 ABOUT THIS DESIGN

A heart pin marks the birth city, with baby's name displayed \
prominently below the map alongside the birth date and city name. \
The circle crop creates a clean, modern look that pairs beautifully \
with other nursery art.

Every street, park, and waterway is rendered from professional \
cartographic data at 300+ DPI — a meaningful keepsake they'll \
treasure as they grow.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🚚 SHIPPING & DELIVERY

◈ Digital: Proof within 1-2 business days, final file after approval
◈ Physical prints: 2-3 days design + 3-5 days production + shipping
◈ Framed prints: 5-7 business days + shipping
◈ Ships from the US via our premium print partner

━━━━━━━━━━━━━━━━━━━━━━━━━━

💛 PERFECT FOR

🍼 Baby shower gifts
🍼 Newborn welcome gifts
🍼 Nursery decor
🍼 First birthday keepsake
🍼 Birth announcement art

━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ Questions? Message us anytime — we love helping you create the perfect map.

© GeoLine Collective — Cartography as Craft""",
    personalization_prompt=(
        "Please provide:\n"
        "1. Birth city or location\n"
        "2. Baby's name\n"
        "3. Birth date (and optional details: weight, time)\n"
        "4. Style: Warm Beige, Clay & Sage, or Watercolor\n"
        "5. Shape: Circle or Full"
    ),
)


# ---------------------------------------------------------------------------
# Listing 5: Custom Blueprint Mosaic Map
# ---------------------------------------------------------------------------

CUSTOM_BLUEPRINT = CustomListing(
    slug="custom_blueprint",
    sku_prefix="GLC-CBLU",
    title=(
        "Custom Blueprint Mosaic Map Print | Detailed City Block Art "
        "| 4 Colors | Personalized Map Gift"
    ),
    tags=[
        "blueprint map print",
        "mosaic city map",
        "custom-map",
        "architectural map art",
        "shaded city poster",
        "modern wall art",
        "blueprint wall decor",
        "city block map",
        "detailed map print",
        "custom mosaic map",
        "choose your color map",
        "housewarming gift",
        "unique map art",
    ],
    description="""\
📍 An incredibly detailed mosaic map of ANY city — choose from 4 rich color palettes.

Every city block is individually shaded in 8 tones of a single color, \
with every street, alley, and path rendered as a crisp white overlay. \
The result is a stunning architectural-style map that reveals the \
hidden geometry of any city's street grid.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🔸 HOW TO ORDER

1. Add this listing to your cart
2. In the "Personalization" box, tell us:
   → City name or location
   → Color choice (see below)
3. We'll design your map and send a proof within 1-2 business days
4. After your approval, we deliver the final file or ship your print

━━━━━━━━━━━━━━━━━━━━━━━━━━

🎨 CHOOSE YOUR COLOR

◈ Navy — deep blues from midnight to sky blue
◈ Forest — rich greens from pine to sage
◈ Terracotta — warm earth tones from espresso to peach
◈ Charcoal — elegant greys from black to silver

Each color features 8 carefully graded shades that bring depth and \
dimension to the city's blocks.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🖼️ WHAT YOU GET

◈ Digital Download — High-resolution PNG file, ready to print anywhere
◈ Physical Print — Museum-quality poster on premium matte paper
◈ Framed Option — Black or white frame, shipped ready to hang

━━━━━━━━━━━━━━━━━━━━━━━━━━

📐 AVAILABLE SIZES

◈ 8×10 inches (20×25 cm)
◈ 11×14 inches (28×36 cm)
◈ 16×20 inches (41×51 cm)
◈ 18×24 inches (46×61 cm)
◈ 24×36 inches (61×91 cm)

━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ ABOUT THIS DESIGN

This map is created by breaking the city's entire street network into \
individual blocks using a technique called polygonization. Each block \
is assigned a shade from our 8-tone palette based on its size, creating \
a richly textured mosaic. A detailed white road overlay reveals every \
street, path, and alley — including footways and cycleways that most \
maps miss.

The layout features the city name in modern lowercase typography at \
top-right, with GPS coordinates embedded in a color swatch bar. \
A unique design you won't find anywhere else.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🚚 SHIPPING & DELIVERY

◈ Digital: Proof within 1-2 business days, final file after approval
◈ Physical prints: 2-3 days design + 3-5 days production + shipping
◈ Framed prints: 5-7 business days + shipping
◈ Ships from the US via our premium print partner

━━━━━━━━━━━━━━━━━━━━━━━━━━

💛 PERFECT FOR

♥ Architecture and design lovers
♥ Housewarming gifts — truly unique wall art
♥ Travel memories — your favorite city in a new light
♥ Office decor — sophisticated and modern
♥ Anyone who appreciates cartographic detail

━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ Questions? Message us anytime — we love helping you create the perfect map.

© GeoLine Collective — Cartography as Craft""",
    personalization_prompt=(
        "Please provide:\n"
        "1. City name or location\n"
        "2. Color: Navy, Forest, Terracotta, or Charcoal"
    ),
)


# ---------------------------------------------------------------------------
# All listings registry
# ---------------------------------------------------------------------------

ALL_CUSTOM_LISTINGS: dict[str, CustomListing] = {
    "where_we_met": WHERE_WE_MET,
    "graduation_map": GRADUATION_MAP,
    "multi_style_map": MULTI_STYLE_MAP,
    "born_in_map": BORN_IN_MAP,
    "custom_blueprint": CUSTOM_BLUEPRINT,
}


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------

def _format_variants(listing: CustomListing) -> str:
    """Format variant table for listing.txt."""
    lines: list[str] = []
    for v in listing.variants:
        sku = f"{listing.sku_prefix}-{v.sku_suffix}"
        lines.append(f"{sku:<28} | {v.size:<6} | {v.format_name:<18} | ${v.price:.2f}")
    return "\n".join(lines)


def generate_listing_text(slug: str, output_dir: str | None = None) -> str:
    """Generate a listing.txt file for the given custom listing slug.

    Returns the output file path.
    """
    listing = ALL_CUSTOM_LISTINGS[slug]

    out_dir = Path(output_dir) if output_dir else Path("etsy/renders/CustomExpansion") / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "listing.txt"

    content = "\n".join([
        "=" * 70,
        f"ETSY LISTING — {listing.title.split('|')[0].strip()}",
        "=" * 70,
        "",
        "TITLE",
        "-" * 40,
        listing.title,
        "",
        "TAGS",
        "-" * 40,
        ", ".join(listing.tags),
        "",
        "DESCRIPTION",
        "-" * 40,
        listing.description,
        "",
        "PERSONALIZATION INSTRUCTIONS",
        "-" * 40,
        listing.personalization_prompt,
        "",
        "VARIATIONS (SKU / Size / Format / Price)",
        "-" * 40,
        _format_variants(listing),
        "",
    ])

    out_path.write_text(content, encoding="utf-8")
    return str(out_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate custom expansion listing text")
    parser.add_argument("--listing", "-l", choices=list(ALL_CUSTOM_LISTINGS.keys()),
                        help="Generate one listing")
    parser.add_argument("--all", "-a", action="store_true", help="Generate all 5 listings")
    parser.add_argument("--preview", "-p", choices=list(ALL_CUSTOM_LISTINGS.keys()),
                        help="Preview listing to stdout without saving")
    args = parser.parse_args()

    if args.preview:
        sys.stdout.reconfigure(encoding="utf-8")
        listing = ALL_CUSTOM_LISTINGS[args.preview]
        print(f"Title ({len(listing.title)} chars):\n  {listing.title}")
        print(f"\nTags ({len(listing.tags)}):")
        for tag in listing.tags:
            print(f"  - {tag} ({len(tag)} chars)")
        print(f"\nSKU prefix: {listing.sku_prefix}")
        print(f"\nPersonalization:\n  {listing.personalization_prompt}")
        print(f"\nDescription (first 500 chars):\n  {listing.description[:500]}...")
        return

    if args.all:
        for slug in ALL_CUSTOM_LISTINGS:
            path = generate_listing_text(slug)
            print(f"Generated: {path}")
    elif args.listing:
        path = generate_listing_text(args.listing)
        print(f"Generated: {path}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
