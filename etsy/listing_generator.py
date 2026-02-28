"""GeoLine Collective — Etsy Listing Content Generator.

Generates SEO-optimized titles, descriptions, and tags for city map listings
following the formulas defined in the GeoLine business plan (Sections 7.1, 7.2).

Usage:
    from etsy.listing_generator import generate_listing
    from etsy.city_list import get_city

    city = get_city("Chicago")
    listing = generate_listing(city)
    print(listing["title"])
    print(listing["tags"])
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from etsy.city_list import CityListing


# ---------------------------------------------------------------------------
# Pricing (from business plan Section 4.2)
# ---------------------------------------------------------------------------

DIGITAL_PRICE = 10.00       # Pre-made city map digital (launch: 20% off = $8.00)
LAUNCH_SALE_PCT = 0.20      # 20% off for first 60 days

PHYSICAL_PRICES: dict[str, float] = {
    "8x10":  28.00,
    "11x14": 38.00,
    "16x20": 52.00,
    "18x24": 62.00,
    "24x36": 72.00,
}

# ---------------------------------------------------------------------------
# US state name lookup for SEO titles
# ---------------------------------------------------------------------------

_US_STATES: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DC": "DC",
    "DE": "Delaware", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

# Reverse lookup: full name -> abbreviation
_STATE_ABBREV: dict[str, str] = {v: k for k, v in _US_STATES.items()}


# ---------------------------------------------------------------------------
# Quality descriptors and gift occasions (rotated across listings for variety)
# ---------------------------------------------------------------------------

_QUALITY_DESCRIPTORS = [
    "Premium Street Map Wall Art",
    "Detailed Street Map Wall Art",
    "Minimalist Street Map Art",
    "Modern City Map Wall Art",
]

_GIFT_OCCASIONS = [
    ("Housewarming Gift", "Travel Decor"),
    ("Moving Gift", "New Home Gift"),
    ("Anniversary Gift", "City Wall Art"),
    ("Housewarming", "Birthday Gift"),
    ("Travel Gift", "Modern Wall Art"),
]


# ---------------------------------------------------------------------------
# Tag generation (Section 7.2 — 13 tags per listing)
# ---------------------------------------------------------------------------

_UNIVERSAL_TAGS = [
    "city map print",
    "street map art",
    "housewarming gift",
    "new home gift",
    "moving gift",
    "city map wall art",
    "travel wall decor",
    "custom city map",
    "map print art",
]


def _generate_tags(city: CityListing) -> list[str]:
    """Generate 13 SEO tags for a city listing."""
    city_name = city.city.lower()
    city_tags = [
        f"{city_name} map print",
        f"{city_name} wall art",
        f"{city_name} poster",
        f"{city_name} gift",
    ]
    return city_tags + _UNIVERSAL_TAGS


# ---------------------------------------------------------------------------
# Title generation (Section 7.1 — max 140 chars)
# ---------------------------------------------------------------------------

def _generate_title(city: CityListing, variant_idx: int = 0) -> str:
    """Generate an SEO-optimized title under 140 characters.

    Formula: [City] [State] Map Print - [Quality] | [Gift 1] | [Gift 2]
    """
    quality = _QUALITY_DESCRIPTORS[variant_idx % len(_QUALITY_DESCRIPTORS)]
    occasion1, occasion2 = _GIFT_OCCASIONS[variant_idx % len(_GIFT_OCCASIONS)]

    if city.country == "USA" and city.state != "DC":
        location = f"{city.city} {city.state}"
    elif city.country == "USA":
        location = city.city  # "Washington DC" already includes DC
    else:
        location = f"{city.city} {city.country}"

    title = f"{location} Map Print - {quality} | {occasion1} | {occasion2}"

    # Truncate if over 140 chars (Etsy limit)
    if len(title) > 140:
        # Drop the last occasion
        title = f"{location} Map Print - {quality} | {occasion1}"
    if len(title) > 140:
        title = f"{location} Map Print - {quality}"
    if len(title) > 140:
        title = f"{location} Map Print | {occasion1}"

    return title[:140]


# ---------------------------------------------------------------------------
# Description generation
# ---------------------------------------------------------------------------

_DESCRIPTION_TEMPLATE = """\
The perfect gift for anyone who loves {city}. Whether it's a housewarming, \
anniversary, or just because — this premium street map print captures the \
beauty of {city_full} in stunning cartographic detail.

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

DETAILS

• Designed with professional GIS cartographic data — not auto-generated
• Every street, waterway, park, and building footprint rendered at 300+ DPI
• Clean, modern aesthetic that complements any home decor
• Printed on archival-quality heavyweight matte paper (physical orders)

━━━━━━━━━━━━━━━━━━━━━━━━━━

PERSONALIZATION

Want a custom location, specific address with a pin marker, or custom text? \
Check out our Custom Map listing for fully personalized options:
→ Custom text lines (names, dates, coordinates, quotes)
→ Pin marker on any address (heart, pin, house, or graduation cap)
→ 5 font styles to choose from

━━━━━━━━━━━━━━━━━━━━━━━━━━

PROCESSING & SHIPPING

✦ Digital: Instant download after purchase
✦ Physical prints: 3-5 business days production + shipping
✦ Ships from the US via our premium print partner

━━━━━━━━━━━━━━━━━━━━━━━━━━

PERFECT FOR

♥ Housewarming gifts
♥ Anniversary & wedding gifts
♥ New home celebrations
♥ Going-away & moving gifts
♥ Birthday gifts for city lovers
♥ College graduation gifts
♥ Travel memories & wanderlust decor

━━━━━━━━━━━━━━━━━━━━━━━━━━

© GeoLine Collective — Cartography as Craft"""


def _generate_description(city: CityListing) -> str:
    """Generate the Etsy listing description for a city."""
    if city.country == "USA" and city.state != "DC":
        city_full = f"{city.city}, {city.state}"
    elif city.country == "USA":
        city_full = city.city
    else:
        city_full = f"{city.city}, {city.country}"

    return _DESCRIPTION_TEMPLATE.format(
        city=city.city,
        city_full=city_full,
    )


# ---------------------------------------------------------------------------
# Variant / inventory generation
# ---------------------------------------------------------------------------

@dataclass
class ListingVariant:
    """A single purchasable variant (size + format)."""
    size: str
    format: str         # "digital" or "physical_unframed"
    price: float
    sku: str

    def to_dict(self) -> dict:
        return {
            "size": self.size,
            "format": self.format,
            "price": self.price,
            "sku": self.sku,
        }


def _generate_variants(city: CityListing, on_sale: bool = True) -> list[ListingVariant]:
    """Generate all purchasable variants for a city listing."""
    variants: list[ListingVariant] = []
    slug = city.slug

    # Digital download (one size — buyer prints at their chosen size)
    price = DIGITAL_PRICE
    if on_sale:
        price = round(DIGITAL_PRICE * (1 - LAUNCH_SALE_PCT), 2)
    variants.append(ListingVariant(
        size="digital",
        format="digital",
        price=price,
        sku=f"GLC-{slug.upper()}-DIG",
    ))

    # Physical prints (unframed, each size)
    for size_key, base_price in PHYSICAL_PRICES.items():
        variants.append(ListingVariant(
            size=size_key,
            format="physical_unframed",
            price=base_price,
            sku=f"GLC-{slug.upper()}-{size_key.replace('x', 'X')}",
        ))

    return variants


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_listing(
    city: CityListing,
    variant_idx: int = 0,
    on_sale: bool = True,
) -> dict:
    """Generate a complete Etsy listing data structure for a city.

    Args:
        city: CityListing from city_list.py
        variant_idx: Index for rotating quality descriptors / gift occasions
        on_sale: Apply launch sale discount to digital price

    Returns:
        Dict with title, description, tags, price, variants, and metadata.
    """
    title = _generate_title(city, variant_idx)
    description = _generate_description(city)
    tags = _generate_tags(city)
    variants = _generate_variants(city, on_sale=on_sale)

    return {
        "city": city.city,
        "state": city.state,
        "country": city.country,
        "tier": city.tier,
        "title": title,
        "description": description,
        "tags": tags,
        "base_price": variants[0].price,  # Digital price (lowest)
        "variants": [v.to_dict() for v in variants],
        "lat": city.lat,
        "lon": city.lon,
        "distance": city.distance,
        "theme": "37th_parallel",
        "slug": city.slug,
    }


def generate_all_listings(
    tier: int | None = None,
    on_sale: bool = True,
) -> list[dict]:
    """Generate listings for all cities (or a specific tier).

    Args:
        tier: If set, only generate for that tier (1, 2, or 3). None = all.
        on_sale: Apply launch sale discount.

    Returns:
        List of listing dicts.
    """
    from etsy.city_list import ALL_CITIES, get_cities_by_tier

    cities = get_cities_by_tier(tier) if tier else ALL_CITIES
    return [
        generate_listing(city, variant_idx=i, on_sale=on_sale)
        for i, city in enumerate(cities)
    ]


def export_listings_json(
    output_path: str = "etsy/listings.json",
    tier: int | None = None,
    on_sale: bool = True,
) -> str:
    """Generate all listings and write to JSON file.

    Returns the output file path.
    """
    listings = generate_all_listings(tier=tier, on_sale=on_sale)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(listings, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Exported {len(listings)} listings to {path}")
    return str(path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate Etsy listing content")
    parser.add_argument("--tier", type=int, default=None, help="Tier to generate (1/2/3, default: all)")
    parser.add_argument("--city", type=str, default=None, help="Generate for a single city")
    parser.add_argument("--output", "-o", default="etsy/listings.json", help="Output JSON path")
    parser.add_argument("--no-sale", action="store_true", help="Disable launch sale pricing")
    parser.add_argument("--preview", action="store_true", help="Print one listing to stdout")
    args = parser.parse_args()

    if args.city:
        from etsy.city_list import get_city
        city = get_city(args.city)
        if not city:
            print(f"City not found: {args.city}")
            raise SystemExit(1)
        listing = generate_listing(city, on_sale=not args.no_sale)
        import sys
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(listing, indent=2, ensure_ascii=False))
    elif args.preview:
        from etsy.city_list import TIER_1
        listing = generate_listing(TIER_1[0], on_sale=not args.no_sale)
        print(f"Title ({len(listing['title'])} chars):")
        print(f"  {listing['title']}")
        print(f"\nTags ({len(listing['tags'])}):")
        for tag in listing["tags"]:
            print(f"  - {tag}")
        print(f"\nBase Price: ${listing['base_price']}")
        print(f"\nVariants ({len(listing['variants'])}):")
        for v in listing["variants"]:
            print(f"  {v['sku']}: {v['size']} ({v['format']}) — ${v['price']}")
        print(f"\nDescription preview (first 200 chars):")
        print(f"  {listing['description'][:200]}...")
    else:
        export_listings_json(args.output, tier=args.tier, on_sale=not args.no_sale)
