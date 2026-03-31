# etsy/style_config.py
"""Style configuration for all map products — pricing, SKUs, tags, render params."""

from __future__ import annotations
from dataclasses import dataclass, field

# Gelato product UIDs per size x format
GELATO_UIDS: dict[str, dict[str, str]] = {
    "unframed": {
        "8x10": "flat_8x10-inch-200x250-mm_170-gsm-65lb-uncoated_4-0_ver",
        "11x14": "flat_11x14-inch-270x350-mm_170-gsm-65lb-uncoated_4-0_ver",
        "16x20": "flat_16x20-inch-400x500-mm_170-gsm-65lb-uncoated_4-0_ver",
        "18x24": "flat_18x24-inch-450x600-mm_170-gsm-65lb-uncoated_4-0_ver",
        "24x36": "flat_24x36-inch-600x900-mm_170-gsm-65lb-uncoated_4-0_ver",
    },
    "framed_black": {
        "8x10": "framed-poster_8x10-inch-200x250-mm_black_170-gsm-65lb-uncoated_4-0_ver",
        "11x14": "framed-poster_11x14-inch-280x355-mm_black_170-gsm-65lb-uncoated_4-0_ver",
        "16x20": "framed-poster_16x20-inch-400x500-mm_black_170-gsm-65lb-uncoated_4-0_ver",
        "18x24": "framed-poster_18x24-inch-450x600-mm_black_170-gsm-65lb-uncoated_4-0_ver",
        "24x36": "framed-poster_24x36-inch-600x900-mm_black_170-gsm-65lb-uncoated_4-0_ver",
    },
    "framed_white": {
        "8x10": "framed-poster_8x10-inch-200x250-mm_white_170-gsm-65lb-uncoated_4-0_ver",
        "11x14": "framed-poster_11x14-inch-280x355-mm_white_170-gsm-65lb-uncoated_4-0_ver",
        "16x20": "framed-poster_16x20-inch-400x500-mm_white_170-gsm-65lb-uncoated_4-0_ver",
        "18x24": "framed-poster_18x24-inch-450x600-mm_white_170-gsm-65lb-uncoated_4-0_ver",
        "24x36": "framed-poster_24x36-inch-600x900-mm_white_170-gsm-65lb-uncoated_4-0_ver",
    },
}

# Etsy shop constants
SHOP_ID = 64614087
SHIPPING_PROFILE_ID = 299396504426  # Gelato: Free shipping
RETURN_POLICY_ID = 1470278944285
READINESS_STATE_ID = 1470278628937
TAXONOMY_ID = 1029  # Art > Prints
SECTION_CITY_MAPS = 57587152
SECTION_CUSTOM_MAPS = 57768965


@dataclass(frozen=True)
class VariantPrice:
    """Price for a single size x format combination."""
    size: str
    format_name: str  # "Unframed Print", "Framed - Black", "Framed - White"
    price: float
    sku_suffix: str   # e.g., "UNF-8x10", "FBK-16x20"


@dataclass(frozen=True)
class StyleConfig:
    """Complete configuration for one map style."""
    name: str                       # "classic", "florence", "blueprint", "monomap"
    display_name: str               # "Classic Street Map", "Florence Mosaic", etc.
    renderer: str                   # "classic", "florence", "blueprint", "monomap"
    sku_prefix: str                 # "GLC-CLASSIC", "GLC-FLOR", etc.
    shop_section_id: int            # Etsy shop section
    listing_type: str               # "physical" or "both" (digital + physical)
    dpi: int                        # Render DPI
    render_timeout: int             # Subprocess timeout in seconds
    title_templates: list[str]      # SEO title templates with {city}, {state}, {gift} placeholders
    base_tags: list[str]            # Style-specific tags (city tags added dynamically)
    description_intro: str          # Style-specific description opening
    variants: list[VariantPrice]    # All size x format x price combinations
    distance_scale: float = 1.0    # Multiplier on city_list distance
    fixed_extent: int | None = None  # Fixed map radius in meters (overrides distance_scale + detect_extent)
    color_name: str | None = None   # For styles with color variants (blueprint default color)
    extra_render_args: dict = field(default_factory=dict)


# Per-city extent overrides — for cities that need more or less than the default
# These override fixed_extent when specified
CITY_EXTENT_OVERRIDES: dict[str, int] = {
    # Mega cities — need wider view
    "london": 8000,
    "tokyo": 8000,
    "los_angeles": 8000,
    "istanbul": 8000,
    "mexico_city": 7000,
    # Large sprawling cities
    "chicago": 6000,
    "new_york": 6000,
    "houston": 6000,
    "dallas": 6000,
    "phoenix": 6000,
    "san_antonio": 6000,
    "atlanta": 6000,
    "miami": 6000,
    "tampa": 6000,
    "philadelphia": 6000,
    "san_diego": 6000,
    "toronto": 6000,
    "sydney": 6000,
    "madrid": 6000,
    "rome": 6000,
    "paris": 6000,
    "berlin": 6000,
    "barcelona": 6000,
    "vienna": 6000,
    # Compact/small cities — can stay tighter
    "florence": 4000,
    "savannah": 4000,
    "charleston": 4000,
    "asheville": 4000,
}


def get_city_extent(city_slug: str, style: "StyleConfig") -> int:
    """Get the map extent (radius in meters) for a city + style.

    Priority: per-city override > style fixed_extent > city_list distance * scale.
    """
    if city_slug in CITY_EXTENT_OVERRIDES:
        return CITY_EXTENT_OVERRIDES[city_slug]
    if style.fixed_extent is not None:
        return style.fixed_extent
    return 5000  # Fallback default


# -- Variant pricing tables ---------------------------------------------------

CITY_MAP_VARIANTS: list[VariantPrice] = [
    # Digital (5)
    VariantPrice("8x10", "Digital Download", 4.20, "DIG-8x10"),
    VariantPrice("11x14", "Digital Download", 5.04, "DIG-11x14"),
    VariantPrice("16x20", "Digital Download", 5.88, "DIG-16x20"),
    VariantPrice("18x24", "Digital Download", 6.72, "DIG-18x24"),
    VariantPrice("24x36", "Digital Download", 7.80, "DIG-24x36"),
    # Unframed (5)
    VariantPrice("8x10", "Unframed Print", 34.83, "UNF-8x10"),
    VariantPrice("11x14", "Unframed Print", 39.85, "UNF-11x14"),
    VariantPrice("16x20", "Unframed Print", 46.35, "UNF-16x20"),
    VariantPrice("18x24", "Unframed Print", 51.37, "UNF-18x24"),
    VariantPrice("24x36", "Unframed Print", 62.45, "UNF-24x36"),
    # Framed Black (5)
    VariantPrice("8x10", "Framed - Black", 78.07, "FBK-8x10"),
    VariantPrice("11x14", "Framed - Black", 87.50, "FBK-11x14"),
    VariantPrice("16x20", "Framed - Black", 119.62, "FBK-16x20"),
    VariantPrice("18x24", "Framed - Black", 131.12, "FBK-18x24"),
    VariantPrice("24x36", "Framed - Black", 216.17, "FBK-24x36"),
    # Framed White (5)
    VariantPrice("8x10", "Framed - White", 78.07, "FWH-8x10"),
    VariantPrice("11x14", "Framed - White", 87.50, "FWH-11x14"),
    VariantPrice("16x20", "Framed - White", 119.62, "FWH-16x20"),
    VariantPrice("18x24", "Framed - White", 131.12, "FWH-18x24"),
    VariantPrice("24x36", "Framed - White", 216.17, "FWH-24x36"),
]

# Custom expansion listings — "always 25% off" sale pricing
# Original prices are set so that 25% off = the sale price shown to buyers
CUSTOM_DIGITAL_PRICES: dict[str, float] = {
    "8x10": 13.32,    # sale: $9.99
    "11x14": 13.32,   # sale: $9.99
    "16x20": 15.99,   # sale: $11.99
    "18x24": 15.99,   # sale: $11.99
    "24x36": 17.32,   # sale: $12.99
}

CUSTOM_EXPANSION_VARIANTS: list[VariantPrice] = [
    # Digital (5) — original prices (Etsy sale set to 25% off)
    VariantPrice("8x10", "Digital Download", 13.32, "DIG-8X10"),
    VariantPrice("11x14", "Digital Download", 13.32, "DIG-11X14"),
    VariantPrice("16x20", "Digital Download", 15.99, "DIG-16X20"),
    VariantPrice("18x24", "Digital Download", 15.99, "DIG-18X24"),
    VariantPrice("24x36", "Digital Download", 17.32, "DIG-24X36"),
    # Unframed (5) — same as city maps (Gelato costs unchanged)
    VariantPrice("8x10", "Unframed Print", 34.83, "UNF-8X10"),
    VariantPrice("11x14", "Unframed Print", 39.85, "UNF-11X14"),
    VariantPrice("16x20", "Unframed Print", 46.35, "UNF-16X20"),
    VariantPrice("18x24", "Unframed Print", 51.37, "UNF-18X24"),
    VariantPrice("24x36", "Unframed Print", 62.45, "UNF-24X36"),
    # Framed Black (5)
    VariantPrice("8x10", "Framed - Black", 78.07, "FBK-8X10"),
    VariantPrice("11x14", "Framed - Black", 87.50, "FBK-11X14"),
    VariantPrice("16x20", "Framed - Black", 119.62, "FBK-16X20"),
    VariantPrice("18x24", "Framed - Black", 131.12, "FBK-18X24"),
    VariantPrice("24x36", "Framed - Black", 216.17, "FBK-24X36"),
    # Framed White (5)
    VariantPrice("8x10", "Framed - White", 78.07, "FWH-8X10"),
    VariantPrice("11x14", "Framed - White", 87.50, "FWH-11X14"),
    VariantPrice("16x20", "Framed - White", 119.62, "FWH-16X20"),
    VariantPrice("18x24", "Framed - White", 131.12, "FWH-18X24"),
    VariantPrice("24x36", "Framed - White", 216.17, "FWH-24X36"),
]

GIFT_KEYWORDS: list[str] = [
    "Housewarming Gift", "New Home Gift", "Anniversary Gift",
    "Travel Gift", "Birthday Gift", "Moving Away Gift", "Graduation Gift",
]


# -- Style definitions ---------------------------------------------------------

CLASSIC = StyleConfig(
    name="classic",
    display_name="Classic Street Map",
    renderer="classic",
    sku_prefix="GLC",
    shop_section_id=SECTION_CITY_MAPS,
    listing_type="physical",
    dpi=300,
    render_timeout=3600,
    distance_scale=1.0,
    title_templates=[
        "{city} Map Print, Minimalist City Poster, Black White Wall Art, {gift}",
        "{city} Street Map Wall Art, Modern Home Decor, City Poster, {gift}",
        "Minimalist {city} Map Print, {state} City Poster, Black White Art, {gift}",
        "{city} Map Poster, City Street Art, Minimalist Wall Decor, {gift}",
    ],
    base_tags=[
        "minimalist map print", "street map poster", "black white map",
        "city map wall art", "modern map print", "map wall decor",
    ],
    description_intro=(
        "A clean, elegant street map featuring detailed black roads on a crisp "
        "white background with blue waterways and green parks. The timeless design "
        "works beautifully in any room."
    ),
    variants=CITY_MAP_VARIANTS,
)

FLORENCE = StyleConfig(
    name="florence",
    display_name="Florence Mosaic Map",
    renderer="florence",
    sku_prefix="GLC-FLOR",
    shop_section_id=SECTION_CITY_MAPS,
    listing_type="physical",
    dpi=300,
    render_timeout=7200,
    distance_scale=0.65,
    title_templates=[
        "{city} Map Wall Art, Colorful Mosaic City Poster, Abstract Street Map, {gift}",
        "{city} Colorful Map Print, Mosaic City Block Art, Modern Wall Decor, {gift}",
        "Colorful {city} Map Poster, Abstract City Art, Mosaic Street Map, {gift}",
        "{city} Map Art Print, Vibrant City Mosaic Poster, Block Map Wall Art, {gift}",
    ],
    base_tags=[
        "colorful map print", "mosaic city poster", "abstract city art",
        "city block art", "modern map print", "vibrant wall art",
    ],
    description_intro=(
        "A vibrant, colorful mosaic map where each city block is individually "
        "colored from a warm palette of oranges, ambers, greens, grays, and teals, "
        "creating a stunning mosaic that reveals your city's unique street grid."
    ),
    variants=CITY_MAP_VARIANTS,
)

BLUEPRINT = StyleConfig(
    name="blueprint",
    display_name="Blueprint Mosaic Map",
    renderer="blueprint",
    sku_prefix="GLC-BLUE",
    shop_section_id=SECTION_CITY_MAPS,
    listing_type="physical",
    dpi=200,  # Blueprint renders at 200 DPI (still high quality, faster)
    render_timeout=3600,
    distance_scale=0.7,
    fixed_extent=5000,  # Standard extent — per-city overrides in CITY_EXTENT_OVERRIDES
    color_name="terracotta",  # Default color for pre-made listings
    title_templates=[
        "{city} Map Print, Blueprint Mosaic Wall Art, Detailed Street Map Poster, {gift}",
        "{city} Blueprint Map Poster, Shaded City Mosaic Art, Modern Wall Decor, {gift}",
        "Blueprint {city} Map Print, Detailed Mosaic Street Art, City Poster, {gift}",
        "{city} Map Wall Art, Blueprint Style Poster, Mosaic City Print, {gift}",
    ],
    base_tags=[
        "blueprint map art", "mosaic city print", "detailed street map",
        "shaded map poster", "modern map art", "city block art",
    ],
    description_intro=(
        "A beautifully detailed mosaic map combining shaded blocks with an "
        "incredibly detailed street overlay, revealing every road, path, and "
        "alley in the city."
    ),
    variants=CITY_MAP_VARIANTS,
)

MONOMAP = StyleConfig(
    name="monomap",
    display_name="Monochrome Map",
    renderer="monomap",
    sku_prefix="GLC-MONO",
    shop_section_id=SECTION_CITY_MAPS,
    listing_type="physical",
    dpi=300,
    render_timeout=7200,
    distance_scale=0.65,
    fixed_extent=5000,  # Standard extent — per-city overrides in CITY_EXTENT_OVERRIDES
    color_name="navy",  # Default color for pre-made listings
    title_templates=[
        "{city} Map Print, Minimalist Monochrome Wall Art, Navy City Poster, {gift}",
        "{city} Monochrome Map Poster, Bold City Art, Minimalist Wall Decor, {gift}",
        "Monochrome {city} Map Print, Navy City Poster, Modern Wall Art, {gift}",
        "{city} Map Wall Art, Monochrome City Print, Bold Street Map Poster, {gift}",
    ],
    base_tags=[
        "monochrome map print", "navy map poster", "minimalist wall art",
        "bold city art", "modern map print", "city block art",
    ],
    description_intro=(
        "A striking monochrome map that transforms the city's street grid "
        "into a bold, minimalist mosaic with crisp white streets on a rich "
        "solid color background."
    ),
    variants=CITY_MAP_VARIANTS,
)

ALL_STYLES: dict[str, StyleConfig] = {
    "classic": CLASSIC,
    "florence": FLORENCE,
    "blueprint": BLUEPRINT,
    "monomap": MONOMAP,
}


def get_style(name: str) -> StyleConfig:
    """Get a style config by name. Raises KeyError if not found."""
    return ALL_STYLES[name]
