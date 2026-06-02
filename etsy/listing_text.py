# etsy/listing_text.py
"""Generate SEO-optimized listing text for any style x city combination."""

from __future__ import annotations

import hashlib

from etsy.city_list import CityListing
from etsy.style_config import StyleConfig, GIFT_KEYWORDS


def _rotate_choice(items: list, seed: str) -> str:
    """Deterministic rotation based on seed string."""
    idx = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(items)
    return items[idx]


def generate_title(city: CityListing, style: StyleConfig) -> str:
    """Generate an SEO-optimized title (max 140 chars)."""
    template = _rotate_choice(style.title_templates, f"{city.slug}_{style.name}")
    gift = _rotate_choice(GIFT_KEYWORDS, f"{city.slug}_{style.name}_gift")

    display_city = city.display_city or city.city
    title = template.format(city=display_city, state=city.state, gift=gift)
    return title[:140]


def generate_tags(city: CityListing, style: StyleConfig) -> list[str]:
    """Generate 13 SEO tags (max 20 chars each)."""
    display_city = city.display_city or city.city
    city_lower = display_city.lower()

    # City-specific tags (3-4)
    city_tags = [
        f"{city_lower} map",
        f"{city_lower} wall art",
        f"{city_lower} poster",
    ]

    # Gift occasion tags (2-3)
    gift_tags = [
        "housewarming gift",
        "new home gift",
        "anniversary gift",
    ]

    # Combine: city + style base + gift, truncate to 20 chars, max 13
    all_tags = city_tags + style.base_tags + gift_tags
    # Filter to 20 char max and deduplicate
    seen: set[str] = set()
    result: list[str] = []
    for tag in all_tags:
        tag = tag[:20]
        if tag not in seen:
            seen.add(tag)
            result.append(tag)
        if len(result) == 13:
            break
    return result


COLOR_OPTIONS: dict[str, str] = {
    "blueprint": (
        "AVAILABLE COLORS\n"
        "1. Navy — deep blues from midnight to sky\n"
        "2. Forest — rich greens from pine to sage\n"
        "3. Terracotta — warm earth tones from espresso to peach\n"
        "4. Charcoal — elegant greys from black to silver\n\n"
        "See listing image #2 for color reference. "
        "Specify your color choice in the personalization box."
    ),
    "monomap": (
        "AVAILABLE COLORS\n"
        "1. Charcoal — classic medium grey\n"
        "2. Navy — deep sophisticated blue\n"
        "3. Forest — rich dark green\n"
        "4. Terracotta — warm burnt orange\n"
        "5. Dusty Rose — elegant mauve/pink\n"
        "6. Black — bold near-black\n\n"
        "See listing image #2 for color reference. "
        "Specify your color choice in the personalization box."
    ),
}


def generate_description(city: CityListing, style: StyleConfig) -> str:
    """Generate a full listing description."""
    display_city = city.display_city or city.city
    state = city.display_subtitle or city.state

    color_section = COLOR_OPTIONS.get(style.name, "")

    sizes_section = (
        "AVAILABLE SIZES\n"
        "- 8x10 inches (20x25 cm)\n"
        "- 11x14 inches (28x36 cm)\n"
        "- 16x20 inches (40x50 cm)\n"
        "- 18x24 inches (45x60 cm)\n"
        "- 24x36 inches (60x90 cm)"
    )

    physical_section = (
        "PRINT QUALITY\n"
        "- Museum-quality 170gsm uncoated matte paper\n"
        "- Vibrant, fade-resistant inks\n"
        "- Optional black or white frame\n"
        "- Ships flat in protective packaging"
    )

    parts = [
        f"{display_city}, {state}",
        style.description_intro,
    ]
    if color_section:
        parts.append(color_section)
    parts.extend([
        sizes_section,
        physical_section,
        "All maps are rendered from OpenStreetMap data at 300 DPI — "
        "every street, park, and waterway is captured in precise detail.",
        "Makes a perfect gift for anyone who loves their city.",
    ])

    return "\n\n".join(parts)


def generate_listing_text(city: CityListing, style: StyleConfig) -> dict:
    """Generate complete listing text for a city x style combination.

    Returns dict with title, tags, description keys.
    """
    return {
        "title": generate_title(city, style),
        "tags": generate_tags(city, style),
        "description": generate_description(city, style),
    }
