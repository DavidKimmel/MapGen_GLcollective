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

DIGITAL_PRICES: dict[str, float] = {
    "8x10":  4.20,
    "11x14": 5.40,
    "16x20": 6.60,
    "18x24": 7.20,
    "24x36": 7.80,
}

UNFRAMED_PRICES: dict[str, float] = {
    "8x10":  34.83,
    "11x14": 42.04,
    "16x20": 46.84,
    "18x24": 51.64,
    "24x36": 62.45,
}

FRAMED_PRICES: dict[str, float] = {
    "8x10":  78.07,
    "11x14": 92.48,
    "16x20": 121.29,
    "18x24": 133.31,
    "24x36": 216.17,
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
    "High Quality City Map Poster",
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
# SEO-optimized title formulas (varied across listings)
# {location} = "City State" or "City Country"
# {city} = city name only, {region} = state or country
# {gift} = rotated gift keyword
# ---------------------------------------------------------------------------

_TITLE_FORMULAS: list[str] = [
    # 0: Classic + Minimalist + B&W
    "{location} Map Print | Minimalist City Poster, Black and White Wall Art, {gift}",
    # 1: Street Map + Home Decor
    "{location} Street Map Wall Art - Modern Home Decor, City Map Poster | {gift}",
    # 2: Map Poster + Gallery Wall
    "{city} Map Poster | Black and White City Art Print, Gallery Wall Decor, {gift}",
    # 3: Minimalist Lead
    "Minimalist {city} Map Print - {region} City Poster | Black and White Wall Art | {gift}",
    # 4: Gift-Forward
    "{location} Map Art | {gift}, Realtor Closing Gift - City Street Map Wall Decor",
    # 5: Travel + Office
    "{city} City Map Wall Art - {region} Travel Poster Print | Office Decor, {gift}",
    # 6: B&W Lead
    "Black and White {city} Map Print | {region} City Poster, Minimalist Wall Art, {gift}",
    # 7: Living Room
    "{location} Map Poster Print | Wall Art for Living Room - Modern City Map, Home Decor",
    # 8: Modern + Clean
    "{location} Map Print - Modern City Wall Art | Minimalist Poster, {gift}",
    # 9: Scandinavian
    "{location} Map Print - Scandinavian Wall Art, Contemporary City Poster | {gift}",
]

_GIFT_KEYWORDS: list[str] = [
    "Housewarming Gift",
    "New Home Gift",
    "Anniversary Gift",
    "Moving Away Gift",
    "Graduation Gift",
    "Birthday Gift",
    "Travel Gift",
]

# ---------------------------------------------------------------------------
# City-specific intro paragraphs (unique SEO content per listing)
# ---------------------------------------------------------------------------

_CITY_INTROS: dict[str, str] = {
    "Chicago": (
        "From the sweeping curves of Lake Shore Drive to the dense grid of the Loop, "
        "Chicago's street map tells the story of a city shaped by ambition and architecture. "
        "This minimalist map print captures the Windy City's iconic lakefront, river branches, "
        "and legendary neighborhoods in stunning cartographic detail."
    ),
    "New York": (
        "Manhattan's relentless grid collides with the organic streets of Greenwich Village, "
        "Central Park carves a green void through the skyline, and the bridges reach across "
        "the East River to Brooklyn. This black and white map print captures the raw geometry "
        "of the city that never sleeps."
    ),
    "New Orleans": (
        "The Mississippi River bends around the French Quarter in its famous crescent, giving "
        "New Orleans both its shape and its soul. From the narrow streets of the Marigny to the "
        "oak-lined avenues of the Garden District, this map print captures the unique geography "
        "of the Big Easy in elegant cartographic detail."
    ),
    "Nashville": (
        "The Cumberland River winds through downtown Nashville, connecting Music Row to East "
        "Nashville and framing the city's eclectic grid. This minimalist map print captures "
        "the street-level character of Music City in clean, modern cartographic detail."
    ),
    "Austin": (
        "Lady Bird Lake splits Austin between the tech-era growth of downtown and the creative "
        "neighborhoods of South Congress. From the sprawling University of Texas campus to the "
        "winding roads of the Hill Country, this map print captures the Keep Austin Weird spirit "
        "in elegant black and white detail."
    ),
    "Portland": (
        "The Willamette River divides Portland into its distinct east and west sides, with a dozen "
        "bridges stitching them together. From the tight blocks of the Pearl District to the "
        "tree-lined streets of Hawthorne, this map print captures the Pacific Northwest's most "
        "walkable city in clean cartographic detail."
    ),
    "Denver": (
        "Denver's wide grid stretches east from the Rocky Mountain foothills, with the South "
        "Platte River and Cherry Creek cutting diagonal paths through the city. This minimalist "
        "map print captures the Mile High City's bold street geometry and natural waterways in "
        "striking black and white detail."
    ),
    "Boston": (
        "Colonial-era streets twist through Beacon Hill and the North End, then give way to the "
        "perfect grid of Back Bay — a contrast only Boston can pull off. This map print captures "
        "the Charles River, the harbor, and centuries of layered urban history in elegant "
        "cartographic detail."
    ),
    "Miami": (
        "Biscayne Bay wraps around Miami's barrier islands while the Intracoastal Waterway threads "
        "between the mainland and Miami Beach. From the Art Deco grid of South Beach to the "
        "sprawling avenues of Coral Gables, this map print captures the Magic City's tropical "
        "geography in stunning detail."
    ),
    "Atlanta": (
        "Peachtree Street cuts a winding path through Atlanta's rolling hills, anchoring a radial "
        "street system that sprawls in every direction. This minimalist map print captures the "
        "capital of the South — from Midtown's dense grid to the tree-covered neighborhoods that "
        "earned Atlanta the name 'City in a Forest.'"
    ),
    "Minneapolis": (
        "The Chain of Lakes nestles into the western neighborhoods while the Mississippi River "
        "carves through the city's eastern edge. This map print captures Minneapolis's rare blend "
        "of urban grid and natural waterways — a Midwestern gem rendered in clean, modern "
        "cartographic detail."
    ),
    "Pittsburgh": (
        "Three rivers converge at the Golden Triangle where the Allegheny and Monongahela meet to "
        "form the Ohio. Pittsburgh's streets climb steep hillsides and cross iconic bridges, "
        "creating one of America's most dramatic urban maps. This print captures the Steel City's "
        "unique river-carved geography in striking black and white."
    ),
    "Savannah": (
        "Savannah's famous grid of 22 public squares creates a rhythm unlike any other American "
        "city. This map print captures the historic district's elegant geometry, the Savannah River "
        "waterfront, and the moss-draped streets that have made this coastal Georgia city a "
        "beloved destination."
    ),
    "Charleston": (
        "The peninsula where the Ashley and Cooper rivers meet forms the historic heart of "
        "Charleston. From Rainbow Row's narrow streets to the waterfront Battery, this map print "
        "captures the Holy City's tightly woven colonial grid in beautiful cartographic detail."
    ),
    "Asheville": (
        "The French Broad River curves through Asheville's mountain valley, framing a compact "
        "downtown grid surrounded by winding mountain roads. This map print captures the creative "
        "spirit of Western North Carolina's favorite city in clean, minimalist detail."
    ),
    "Honolulu": (
        "Diamond Head anchors the eastern skyline while Waikiki's dense grid meets the Pacific "
        "shore. From the harbor to the ridgelines of the Ko'olau Range, this map print captures "
        "Honolulu's dramatic island geography — where ocean, mountains, and city converge — in "
        "stunning cartographic detail."
    ),
    "Salt Lake City": (
        "Salt Lake City's ultra-wide grid blocks — laid out by Brigham Young himself — stretch "
        "east toward the Wasatch Mountains. This minimalist map print captures the city's "
        "distinctive scale and geometry, from Temple Square to the university foothills, in "
        "clean black and white detail."
    ),
    "Richmond": (
        "The James River carves dramatic S-curves through Richmond, connecting the cobblestone "
        "streets of Shockoe Bottom to the Fan District's Victorian grid. This map print captures "
        "Virginia's capital in elegant cartographic detail."
    ),
    "Chattanooga": (
        "The Tennessee River bends through a deep gorge as it passes downtown Chattanooga, "
        "creating one of the South's most dramatic natural settings. This map print captures "
        "the Scenic City's river-carved geography and surrounding ridge lines in clean, "
        "minimalist detail."
    ),
    "Boise": (
        "The Boise River winds through the city's greenbelt while a clean grid extends toward "
        "the surrounding foothills. This map print captures Idaho's capital — a growing mountain "
        "West city with a compact downtown and expansive natural surroundings — in elegant "
        "black and white detail."
    ),
    "Raleigh": (
        "Oak-lined streets radiate from the State Capitol through Raleigh's historic core, while "
        "the growing Research Triangle sprawls outward with modern development. This map print "
        "captures North Carolina's capital — where Southern charm meets innovation — in clean "
        "cartographic detail."
    ),
    "Charlotte": (
        "Charlotte's banking district anchors a grid that radiates outward along light rail "
        "corridors and tree-lined boulevards. This map print captures the Queen City's rapid "
        "growth and Southern grid geometry in striking minimalist detail."
    ),
    "San Francisco": (
        "San Francisco's grid climbs impossibly steep hills while the bay wraps around three "
        "sides of the peninsula. From the Golden Gate to the Mission, this map print captures "
        "one of America's most iconic urban landscapes in stunning black and white detail."
    ),
    "Seattle": (
        "Puget Sound defines Seattle's western edge while Lake Washington bounds it to the east, "
        "creating a city built on a narrow isthmus of hills. This map print captures the Emerald "
        "City's irregular grid and dramatic waterfront geography in clean cartographic detail."
    ),
    "Washington DC": (
        "L'Enfant's grand radial avenues overlay a regular grid, creating the distinctive "
        "pattern of circles and diagonal streets that makes DC's map instantly recognizable. "
        "This print captures the nation's capital — from the National Mall to Georgetown — "
        "in elegant black and white detail."
    ),
    # --- Tier 4: International ---
    "London": (
        "Two thousand years of history are etched into London's street map — from the medieval "
        "lanes of the City to the Georgian crescents of Kensington. The Thames threads it all "
        "together, bending past Westminster, the Tower, and Canary Wharf. This map print captures "
        "one of the world's great cities in stunning cartographic detail."
    ),
    "Paris": (
        "Haussmann's grand boulevards radiate from the Arc de Triomphe while the Seine curves "
        "past Notre-Dame and the Eiffel Tower. This map print captures the City of Light's "
        "legendary geometry — arrondissements spiraling outward from the Île de la Cité — in "
        "elegant black and white detail."
    ),
    "Tokyo": (
        "Tokyo's dense organic street network defies Western grid logic, with narrow lanes "
        "spiraling around train stations and the Imperial Palace creating a vast void at the "
        "city's heart. This map print captures the mesmerizing complexity of the world's largest "
        "metropolis in striking minimalist detail."
    ),
    "Rome": (
        "Ancient roads built for legions still define Rome's street map, radiating from the "
        "Colosseum and the Forum while the Tiber River curves past Trastevere and Vatican City. "
        "This map print captures the Eternal City's layered history in elegant cartographic detail."
    ),
    "Barcelona": (
        "The Eixample district's perfect octagonal grid — designed by Ildefons Cerdà — meets "
        "the winding medieval streets of the Gothic Quarter, creating a contrast that defines "
        "Barcelona's map. This print captures the Mediterranean city's unique geometry from Las "
        "Ramblas to Sagrada Família in stunning black and white."
    ),
    "Amsterdam": (
        "Amsterdam's iconic concentric canal rings create one of the most recognizable city maps "
        "in the world. From the Herengracht to the Prinsengracht, this map print captures the "
        "Dutch capital's elegant water-defined geometry in clean, minimalist detail."
    ),
    "Lisbon": (
        "Lisbon's streets climb seven hills above the Tagus River, winding through the narrow "
        "alleys of Alfama and opening into the grand plazas of Baixa. This map print captures "
        "the Portuguese capital's dramatic hillside geography and old-world character in "
        "beautiful cartographic detail."
    ),
    "Philadelphia": (
        "William Penn's original grid plan — America's first — still anchors Philadelphia between "
        "the Schuylkill and Delaware rivers. This map print captures the birthplace of American "
        "democracy, from the historic core of Old City to the art-lined Benjamin Franklin Parkway, "
        "in elegant black and white detail."
    ),
    "San Diego": (
        "San Diego's harbor opens to the Pacific while the Coronado Bridge arcs across the bay "
        "to its famous island. From the Gaslamp Quarter grid to the coastal bluffs of La Jolla, "
        "this map print captures Southern California's most laid-back city in stunning "
        "cartographic detail."
    ),
    "Baltimore": (
        "The Inner Harbor anchors Baltimore's waterfront while the Patapsco River opens to the "
        "Chesapeake Bay. From the dense row house grid of Federal Hill to the cobblestone streets "
        "of Fells Point, this map print captures Charm City's gritty, beautiful geography in "
        "striking cartographic detail."
    ),
    # --- Tier 5: US Expansion ---
    "Los Angeles": (
        "LA's endless grid stretches from the Pacific Coast to the foothills of the San Gabriel "
        "Mountains, crossed by the concrete channel of the LA River. From the tight blocks of "
        "downtown to the winding canyons of Hollywood Hills, this map print captures the sheer "
        "scale of the City of Angels in stunning black and white detail."
    ),
    "Houston": (
        "Buffalo Bayou winds through downtown Houston while a network of bayous threads through "
        "the city's sprawling grid. This map print captures the energy capital of the world — "
        "from the Texas Medical Center to the Heights — in clean, modern cartographic detail."
    ),
    "San Antonio": (
        "The San Antonio River curves its famous walk through the heart of downtown, connecting "
        "the Alamo to the King William historic district. This map print captures the Alamo "
        "City's blend of Spanish colonial streets and modern Texas grid in elegant black and "
        "white detail."
    ),
    "Detroit": (
        "The Detroit River forms an international border as Woodward Avenue and other grand "
        "radial boulevards fan outward from the waterfront. This map print captures the Motor "
        "City's bold street geometry — designed by Augustus Woodward — in striking minimalist "
        "cartographic detail."
    ),
    "St. Louis": (
        "The Mississippi River defines St. Louis's eastern edge, with the Gateway Arch marking "
        "where the city's grid meets the waterfront. From the historic brick neighborhoods of "
        "Soulard to the grand avenues of the Central West End, this map print captures the "
        "Gateway to the West in elegant cartographic detail."
    ),
    "Cincinnati": (
        "The Ohio River bends in a dramatic horseshoe around downtown Cincinnati, with streets "
        "climbing steep hillsides in every direction. From Over-the-Rhine's dense urban grid to "
        "the riverfront stadiums, this map print captures the Queen City's river-carved geography "
        "in striking black and white detail."
    ),
    "Tampa": (
        "Tampa Bay wraps around the city's western shore while the Hillsborough River cuts "
        "through downtown. From the brick streets of Ybor City to the waterfront of Bayshore "
        "Boulevard, this map print captures Florida's Gulf Coast gem in clean, modern "
        "cartographic detail."
    ),
    "Milwaukee": (
        "Lake Michigan forms Milwaukee's dramatic eastern edge while the Milwaukee, Menomonee, "
        "and Kinnickinnic rivers converge downtown. This map print captures the Cream City's "
        "lakefront geography and historic Third Ward in elegant black and white detail."
    ),
    "Kansas City": (
        "The Missouri River bends along Kansas City's northern edge while the city's grid "
        "straddles the Missouri-Kansas state line. From the Country Club Plaza to the Crossroads "
        "Arts District, this map print captures the Heart of America's bold geometry in clean "
        "cartographic detail."
    ),
    "Cleveland": (
        "Lake Erie stretches north beyond the city skyline while the Cuyahoga River's famous "
        "bends wind through the Flats. This map print captures Cleveland's lakefront geography "
        "and resilient urban grid — from University Circle to Ohio City — in striking "
        "minimalist detail."
    ),
    # --- Tier 5: World Expansion ---
    "Berlin": (
        "The Spree River meanders past the Reichstag and Museum Island while the vast Tiergarten "
        "creates a green void at the city's heart. This map print captures Berlin's reunified "
        "street grid — from the Brandenburg Gate to Kreuzberg's dense blocks — in stunning "
        "cartographic detail."
    ),
    "Dublin": (
        "The River Liffey divides Dublin's northside from its Georgian southside, flowing past "
        "the Ha'penny Bridge and the Custom House to Dublin Bay. This map print captures the "
        "Irish capital's compact, walkable street grid in elegant black and white detail."
    ),
    "Edinburgh": (
        "Edinburgh's Old Town clings to a volcanic ridge while the Georgian New Town spreads in "
        "a perfect grid below — a contrast that earned this city UNESCO World Heritage status. "
        "This map print captures the Scottish capital's dramatic hilltop geography in stunning "
        "cartographic detail."
    ),
    "Prague": (
        "The Vltava River bends through Prague's heart, connecting the castle district of "
        "Hradcany to the medieval lanes of Stare Mesto. This map print captures the City of a "
        "Hundred Spires — its bridges, islands, and winding Baroque streets — in elegant "
        "black and white detail."
    ),
    "Vienna": (
        "The Ringstrasse encircles Vienna's imperial core — a grand boulevard replacing the "
        "old city walls — while the Danube Canal cuts through the eastern districts. This map "
        "print captures the City of Music's elegant radial geometry in clean, modern "
        "cartographic detail."
    ),
    "Copenhagen": (
        "Copenhagen's harbor district and canal-laced Christianshavn sit alongside the medieval "
        "streets of the old city. This map print captures the Danish capital's waterfront "
        "geography — from Nyhavn to the free town of Christiania — in striking minimalist detail."
    ),
    "Istanbul": (
        "The Bosphorus strait splits Istanbul across two continents while the Golden Horn "
        "inlet divides the European side into old and new. This map print captures the "
        "transcontinental city's extraordinary geography — connecting Asia and Europe — in "
        "stunning cartographic detail."
    ),
    "Sydney": (
        "Sydney Harbour's jagged inlets wind past the Opera House and under the Harbour Bridge "
        "while the Pacific Ocean defines the eastern beaches. This map print captures Australia's "
        "harbor city — from Circular Quay to Bondi — in elegant black and white detail."
    ),
    "Florence": (
        "The Arno River crosses Florence beneath the Ponte Vecchio, dividing the Renaissance "
        "city's tight medieval grid from the Oltrarno artisan quarter. This map print captures "
        "the cradle of the Renaissance — compact, beautiful, and timeless — in stunning "
        "cartographic detail."
    ),
    "Stockholm": (
        "Stockholm spreads across 14 islands where Lake Malaren meets the Baltic Sea, connected "
        "by 57 bridges. This map print captures the Scandinavian capital's unique archipelago "
        "geography — from Gamla Stan's medieval lanes to Sodermalm's hipster grid — in elegant "
        "black and white detail."
    ),
}


# ---------------------------------------------------------------------------
# Tag generation (Section 7.2 — 13 tags per listing)
# ---------------------------------------------------------------------------

_UNIVERSAL_TAGS = [
    "city map print",
    "street map art",
    "housewarming gift",
    "new home gift",
    "minimalist wall art",
    "black and white print",
    "city poster",
    "home decor",
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

    Uses varied formula templates to avoid cookie-cutter titles across the shop.
    """
    if city.country == "USA" and city.state != "DC":
        location = f"{city.city} {city.state}"
        region = city.state
    elif city.country == "USA":
        location = city.city
        region = "United States"
    else:
        location = f"{city.city} {city.country}"
        region = city.country

    gift = _GIFT_KEYWORDS[variant_idx % len(_GIFT_KEYWORDS)]
    formula = _TITLE_FORMULAS[variant_idx % len(_TITLE_FORMULAS)]

    title = formula.format(
        location=location,
        city=city.city,
        region=region,
        gift=gift,
    )

    # Truncate if over 140 chars — progressively simplify
    if len(title) > 140:
        title = f"{location} Map Print | Minimalist City Poster, {gift}"
    if len(title) > 140:
        title = f"{location} Map Print - Modern City Wall Art | {gift}"
    if len(title) > 140:
        title = f"{location} Map Print | {gift}"

    return title[:140]


# ---------------------------------------------------------------------------
# Description generation
# ---------------------------------------------------------------------------

_DESCRIPTION_TEMPLATE = """\
The perfect gift for anyone who loves {city}. Whether it's a housewarming, \
anniversary, or just because — this premium street map print captures the \
beauty of {city_full} in stunning cartographic detail.

WHAT YOU GET
✦ Digital Download — High-resolution 300 DPI PNG file, ready to print at home or at any print shop
✦ Physical Print — Museum-quality poster printed on premium matte paper, shipped directly to you via our print partner
✦ Framed Option — Choose black, white, or natural wood frame in any size

AVAILABLE SIZES
• 8×10" — Perfect for desks, shelves, or small wall spaces
• 11×14" — Ideal for standard frames and gallery walls
• 16×20" — Our most popular size — great statement piece
• 18×24" — Large format for living rooms and offices
• 24×36" — Maximum impact — stunning above a sofa or bed

DETAILS
• Designed with professional GIS cartographic data — not auto-generated
• Every street, waterway, park, and building footprint rendered at 300+ DPI
• Clean, modern aesthetic that complements any home decor
• Printed on archival-quality heavyweight matte paper (physical orders)

PERSONALIZATION
Want a custom location, specific address with a pin marker, or custom text? \
Check out our Custom Map listing for fully personalized options:
→ Custom text lines (names, dates, coordinates, quotes)
→ Pin marker on any address (heart, pin, house, or graduation cap)
→ 5 font styles to choose from

PROCESSING & SHIPPING
✦ Digital: Instant download after purchase
✦ Physical prints: 3-5 business days production + shipping
✦ Ships from the US via our premium print partner

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

    # Use city-specific intro if available, otherwise fall back to template
    if city.city in _CITY_INTROS:
        return _CITY_INTROS[city.city]

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


def _generate_variants(city: CityListing) -> list[ListingVariant]:
    """Generate all purchasable variants for a city listing."""
    variants: list[ListingVariant] = []
    slug = city.slug.upper()

    # Digital downloads (per size)
    for size_key, price in DIGITAL_PRICES.items():
        variants.append(ListingVariant(
            size=size_key,
            format="digital",
            price=price,
            sku=f"GLC-{slug}-DIG-{size_key.replace('x', 'X')}",
        ))

    # Physical prints (unframed, each size)
    for size_key, price in UNFRAMED_PRICES.items():
        variants.append(ListingVariant(
            size=size_key,
            format="physical_unframed",
            price=price,
            sku=f"GLC-{slug}-UNF-{size_key.replace('x', 'X')}",
        ))

    # Framed prints — all black sizes first, then all white sizes
    for frame_color in ("black", "white"):
        for size_key, price in FRAMED_PRICES.items():
            variants.append(ListingVariant(
                size=size_key,
                format=f"framed_{frame_color}",
                price=price,
                sku=f"GLC-{slug}-FR{frame_color[0].upper()}-{size_key.replace('x', 'X')}",
            ))

    return variants


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_listing(
    city: CityListing,
    variant_idx: int = 0,
) -> dict:
    """Generate a complete Etsy listing data structure for a city.

    Args:
        city: CityListing from city_list.py
        variant_idx: Index for rotating quality descriptors / gift occasions

    Returns:
        Dict with title, description, tags, price, variants, and metadata.
    """
    title = _generate_title(city, variant_idx)
    description = _generate_description(city)
    tags = _generate_tags(city)
    variants = _generate_variants(city)

    return {
        "city": city.city,
        "state": city.state,
        "country": city.country,
        "tier": city.tier,
        "title": title,
        "description": description,
        "tags": tags,
        "base_price": variants[0].price,  # Smallest digital price
        "variants": [v.to_dict() for v in variants],
        "lat": city.lat,
        "lon": city.lon,
        "distance": city.distance,
        "theme": "37th_parallel",
        "slug": city.slug,
    }


def generate_all_listings(
    tier: int | None = None,
) -> list[dict]:
    """Generate listings for all cities (or a specific tier).

    Args:
        tier: If set, only generate for that tier (1, 2, or 3). None = all.

    Returns:
        List of listing dicts.
    """
    from etsy.city_list import ALL_CITIES, get_cities_by_tier

    cities = get_cities_by_tier(tier) if tier else ALL_CITIES
    return [
        generate_listing(city, variant_idx=i)
        for i, city in enumerate(cities)
    ]


def _format_display(fmt: str) -> str:
    """Convert internal format name to display name for variations file."""
    _MAP = {
        "digital": "Digital Download",
        "physical_unframed": "Unframed Print",
        "framed_black": "Framed Black",
        "framed_white": "Framed White",
    }
    return _MAP.get(fmt, fmt)


def export_listing_text(city: CityListing, variant_idx: int = 0) -> str:
    """Generate the _listing.txt cheat sheet for a city.

    Returns the output file path.
    """
    listing = generate_listing(city, variant_idx)
    renders_dir = Path(__file__).parent / "renders" / city.slug
    renders_dir.mkdir(parents=True, exist_ok=True)
    out_path = renders_dir / f"{city.slug}_listing.txt"

    # Collect mockup and image files
    mockups = sorted(renders_dir.glob("mockup_*.jpg"))
    detail_crop = renders_dir / f"{city.slug}_detail_crop.jpg"
    size_comp = renders_dir / f"{city.slug}_size_comparison.png"

    if city.country == "USA":
        location_label = f"{city.city}, {city.state}"
    else:
        location_label = f"{city.city}, {city.country}"

    lines: list[str] = []
    lines.append("=" * 70)
    lines.append(f"ETSY LISTING — {location_label}")
    lines.append("=" * 70)
    lines.append("")

    # Title
    lines.append("TITLE")
    lines.append("-" * 40)
    lines.append(listing["title"])
    lines.append("")

    # Tags
    lines.append(f"TAGS (paste one per tag field)")
    lines.append("-" * 40)
    for i, tag in enumerate(listing["tags"], 1):
        lines.append(f"  {i:2d}. {tag}")
    lines.append("")

    # Description (city-specific intro paragraph only — copy the rest from existing listing)
    lines.append("DESCRIPTION (intro paragraph)")
    lines.append("-" * 40)
    lines.append(listing["description"])
    lines.append("")

    # Pricing table
    lines.append("PRICING & VARIANTS")
    lines.append("-" * 40)
    lines.append(f"{'Size':<9}{'Format':<24}{'Price':>7}   {'SKU'}")
    lines.append(f"{'----':<9}{'------':<24}{'-----':>7}   {'---'}")
    for v in listing["variants"]:
        lines.append(
            f"{v['size']:<9}{v['format']:<24}${v['price']:>7.2f}   {v['sku']}"
        )
    lines.append("")

    # Photos
    lines.append("PHOTOS (upload in this order)")
    lines.append("-" * 40)
    rank = 1
    for m in mockups:
        lines.append(f"  {rank}. {m.name}")
        rank += 1
    if detail_crop.exists():
        lines.append(f"  {rank}. {detail_crop.name}")
        rank += 1
    if size_comp.exists():
        lines.append(f"  {rank}. {size_comp.name}")
        rank += 1
    lines.append("")

    # Digital file
    lines.append("DIGITAL FILE")
    lines.append("-" * 40)
    lines.append(f"  {city.slug}_16x20.png")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return str(out_path)


def export_variations_text(city: CityListing, variant_idx: int = 0) -> str:
    """Generate the _variations.txt file for a city.

    Returns the output file path.
    """
    listing = generate_listing(city, variant_idx)
    renders_dir = Path(__file__).parent / "renders" / city.slug
    renders_dir.mkdir(parents=True, exist_ok=True)
    out_path = renders_dir / f"{city.slug}_variations.txt"

    if city.country == "USA":
        location_label = f"{city.city}, {city.state}"
    else:
        location_label = f"{city.city}, {city.country}"

    lines: list[str] = []
    lines.append(f"ETSY VARIATIONS — {location_label}")
    lines.append("Copy each row into the Etsy variation grid.")
    lines.append("")
    lines.append(f"{'Row':<6}{'Format':<21}{'Size':<12}{'Price':>7}   {'SKU'}")
    lines.append(f"{'---':<6}{'------':<21}{'----':<12}{'-----':>7}   {'---'}")

    for i, v in enumerate(listing["variants"], 1):
        display = _format_display(v["format"])
        lines.append(
            f"{i:<6}{display:<21}{v['size']:<12}{v['price']:>7.2f}   {v['sku']}"
        )

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return str(out_path)


def export_all_texts(tier: int | None = None) -> None:
    """Generate _listing.txt and _variations.txt for all cities."""
    from etsy.city_list import ALL_CITIES, get_cities_by_tier

    cities = get_cities_by_tier(tier) if tier else ALL_CITIES
    for i, city in enumerate(cities):
        export_listing_text(city, variant_idx=i)
        export_variations_text(city, variant_idx=i)
        print(f"  {city.city}: listing + variations")
    print(f"\nGenerated text files for {len(cities)} cities")


def export_listings_json(
    output_path: str = "etsy/listings.json",
    tier: int | None = None,
) -> str:
    """Generate all listings and write to JSON file.

    Returns the output file path.
    """
    listings = generate_all_listings(tier=tier)
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
    parser.add_argument("--preview", action="store_true", help="Print one listing to stdout")
    parser.add_argument("--generate-texts", action="store_true", help="Generate _listing.txt and _variations.txt for all cities")
    args = parser.parse_args()

    if args.generate_texts:
        import sys
        sys.stdout.reconfigure(encoding="utf-8")
        export_all_texts(tier=args.tier)
    elif args.city:
        from etsy.city_list import get_city
        city = get_city(args.city)
        if not city:
            print(f"City not found: {args.city}")
            raise SystemExit(1)
        listing = generate_listing(city)
        import sys
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(listing, indent=2, ensure_ascii=False))
    elif args.preview:
        from etsy.city_list import TIER_1
        listing = generate_listing(TIER_1[0])
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
        export_listings_json(args.output, tier=args.tier)
