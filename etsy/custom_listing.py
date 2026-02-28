"""GeoLine Collective — Custom Map Anchor Listing Generator.

Generates the #1 priority "Any Location" custom map listing per
the business plan (Section 5.3). This is a single premium listing
designed to be the primary revenue driver.

Strategy:
  - Custom maps account for the majority of revenue in the map poster niche
  - This listing serves as the "anchor" that all city listings point to
  - Offers full personalization: location, text, fonts, pin styles, colors
  - Premium pricing reflects the custom/made-to-order nature

Usage:
    python -m etsy.custom_listing                    # Print to stdout
    python -m etsy.custom_listing --output custom.json  # Save to file
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Pricing (from business plan Section 5.3)
# ---------------------------------------------------------------------------

CUSTOM_DIGITAL_PRICE = 18.00       # Standard processing
CUSTOM_DIGITAL_RUSH = 28.00        # Rush (24h turnaround)

CUSTOM_PHYSICAL_PRICES: dict[str, float] = {
    "8x10":  34.00,
    "11x14": 44.00,
    "16x20": 58.00,
    "18x24": 68.00,
    "24x36": 82.00,
}


# ---------------------------------------------------------------------------
# SEO tags — 13 tags (Etsy maximum)
# ---------------------------------------------------------------------------

CUSTOM_TAGS: list[str] = [
    "custom city map",
    "personalized map print",
    "custom map gift",
    "housewarming gift",
    "new home gift",
    "anniversary gift map",
    "custom street map",
    "moving away gift",
    "city map wall art",
    "personalized wall art",
    "custom location print",
    "map print art",
    "engagement gift map",
]


# ---------------------------------------------------------------------------
# Title — max 140 chars, primary keyword first
# ---------------------------------------------------------------------------

CUSTOM_TITLE = (
    "Custom City Map Print - Any Location | Personalized Map Gift "
    "| Housewarming | Anniversary"
)


# ---------------------------------------------------------------------------
# Description — optimized for Etsy SEO + conversions
# ---------------------------------------------------------------------------

CUSTOM_DESCRIPTION = """\
The perfect personalized gift — a premium street map of ANY location in the \
world. Whether it's the home you just bought, the city where you fell in love, \
or the place you grew up — we'll create a stunning custom map print just for you.

━━━━━━━━━━━━━━━━━━━━━━━━━━

HOW IT WORKS

1. Purchase this listing and tell us your location (city, address, or coordinates)
2. Choose your style, size, and any custom text
3. We design your map using professional GIS cartographic data
4. You receive a high-resolution proof for approval
5. Final file delivered (digital) or printed and shipped (physical)

━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT YOU CAN CUSTOMIZE

✦ Location — Any city, town, neighborhood, or specific address in the world
✦ Pin Marker — Heart, pin, house, or graduation cap on any address
✦ Custom Text — Names, dates, coordinates, quotes, or any message
✦ Font Style — Choose from 5 carefully curated typography options
✦ Map Style — Classic, Midnight, Sepia, Minimal, or Terracotta
✦ Size — From 8x10" desk prints to 24x36" statement pieces

━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT YOU GET

✦ Digital Download — High-resolution 300 DPI PNG file, ready to print at \
home or at any print shop
✦ Physical Print — Museum-quality poster printed on premium matte paper, \
shipped directly to you via our print partner
✦ Framed Option — Choose black, white, or natural wood frame in any size

━━━━━━━━━━━━━━━━━━━━━━━━━━

AVAILABLE SIZES

• 8×10" — Perfect for desks, shelves, or small wall spaces
• 11×14" — Ideal for standard frames and gallery walls
• 16×20" — Our most popular size — great statement piece
• 18×24" — Large format for living rooms and offices
• 24×36" — Maximum impact — stunning above a sofa or bed

━━━━━━━━━━━━━━━━━━━━━━━━━━

HOW TO ORDER

After purchasing, please include the following in the "Personalization" box \
or send us a message:

→ Location: City name, street address, or GPS coordinates
→ Pin: Yes/No — and pin style (heart, pin, house, graduation cap)
→ Custom text: Up to 3 lines (title, subtitle, bottom text)
→ Style preference: Classic, Midnight, Sepia, Minimal, or Terracotta
→ Any other special requests

We'll send you a digital proof within 1-2 business days for your approval \
before finalizing.

━━━━━━━━━━━━━━━━━━━━━━━━━━

DETAILS

• Designed with professional GIS cartographic data — not auto-generated
• Every street, waterway, park, and building footprint rendered at 300+ DPI
• Clean, modern aesthetic that complements any home decor
• Printed on archival-quality heavyweight matte paper (physical orders)
• 5 unique map styles designed by GeoLine Collective

━━━━━━━━━━━━━━━━━━━━━━━━━━

PROCESSING & SHIPPING

✦ Digital (standard): Proof within 1-2 business days, final file after approval
✦ Digital (rush): Proof within 24 hours — select "Rush" option at checkout
✦ Physical prints: 2-3 days design + 3-5 days production + shipping
✦ Ships from the US via our premium print partner

━━━━━━━━━━━━━━━━━━━━━━━━━━

PERFECT FOR

♥ Housewarming gifts — celebrate a new home
♥ Anniversary & wedding gifts — mark where it all began
♥ Engagement gifts — the spot where they said yes
♥ Moving away gifts — a piece of home to take with you
♥ New baby gifts — birthplace keepsake
♥ College graduation — campus memories
♥ Travel memories — your favorite places on Earth

━━━━━━━━━━━━━━━━━━━━━━━━━━

© GeoLine Collective — Cartography as Craft"""


# ---------------------------------------------------------------------------
# Variant generation
# ---------------------------------------------------------------------------

def _generate_variants(on_sale: bool = False) -> list[dict]:
    """Generate all purchasable variants for the custom listing."""
    variants: list[dict] = []

    # Digital standard
    variants.append({
        "size": "digital",
        "format": "digital",
        "price": CUSTOM_DIGITAL_PRICE,
        "sku": "GLC-CUSTOM-DIG",
        "label": "Digital Download (Standard)",
    })

    # Digital rush
    variants.append({
        "size": "digital_rush",
        "format": "digital",
        "price": CUSTOM_DIGITAL_RUSH,
        "sku": "GLC-CUSTOM-DIG-RUSH",
        "label": "Digital Download (Rush — 24h)",
    })

    # Physical prints
    for size_key, price in CUSTOM_PHYSICAL_PRICES.items():
        variants.append({
            "size": size_key,
            "format": "physical_unframed",
            "price": price,
            "sku": f"GLC-CUSTOM-{size_key.replace('x', 'X')}",
            "label": f"Physical Print — {size_key}\"",
        })

    return variants


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_custom_listing(on_sale: bool = False) -> dict:
    """Generate the complete custom map anchor listing.

    Args:
        on_sale: Not typically used for custom (already premium priced).

    Returns:
        Dict with title, description, tags, price, variants, and metadata.
    """
    variants = _generate_variants(on_sale=on_sale)

    return {
        "listing_type": "custom_anchor",
        "title": CUSTOM_TITLE,
        "description": CUSTOM_DESCRIPTION,
        "tags": CUSTOM_TAGS,
        "base_price": CUSTOM_DIGITAL_PRICE,
        "variants": variants,
        "is_digital": True,
        "who_made": "i_did",
        "when_made": "made_to_order",
        "taxonomy_id": 67,  # Art & Collectibles > Prints > Digital Prints
        "personalization_required": True,
        "personalization_instructions": (
            "Please provide: (1) Location — city, address, or coordinates, "
            "(2) Pin style — heart/pin/house/grad cap or none, "
            "(3) Custom text — up to 3 lines, "
            "(4) Style — Classic/Midnight/Sepia/Minimal/Terracotta"
        ),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate custom map anchor listing")
    parser.add_argument("--output", "-o", default=None, help="Output JSON path")
    parser.add_argument("--preview", action="store_true", help="Print summary to stdout")
    args = parser.parse_args()

    listing = generate_custom_listing()

    if args.preview:
        sys.stdout.reconfigure(encoding="utf-8")
        print(f"Title ({len(listing['title'])} chars):")
        print(f"  {listing['title']}")
        print(f"\nTags ({len(listing['tags'])}):")
        for tag in listing['tags']:
            print(f"  - {tag}")
        print(f"\nBase Price: ${listing['base_price']}")
        print(f"\nVariants ({len(listing['variants'])}):")
        for v in listing['variants']:
            print(f"  {v['sku']}: {v['label']} — ${v['price']}")
        print(f"\nDescription (first 300 chars):")
        print(f"  {listing['description'][:300]}...")
        print(f"\nPersonalization:")
        print(f"  {listing['personalization_instructions']}")
    elif args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(listing, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Exported custom listing to {path}")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(listing, indent=2, ensure_ascii=False))
