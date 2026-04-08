#!/usr/bin/env python3
"""Add style × size variants to CountyMap Etsy draft listings."""

import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from etsy.api_client import EtsyClient
from etsy.style_config import READINESS_STATE_ID

DIGITAL_LISTING_ID = 4484494627
PRINT_LISTING_ID = 4484494881

STYLES = [
    "Classic",
    "Dark Teal",
    "Midnight Blue",
    "Noir",
    "Vintage",
    "Sage Atlas",
    "Sunset",
    "Sky Blue",
    "Rose Blush",
    "Teal Coral",
    "Minimalist",
    "Nordic",
]

# Digital: 18 sizes, flat price
DIGITAL_SIZES = [
    "5x7", "8x10", "11x14", "12x16", "12x18",
    "16x20", "18x24", "20x28", "20x30", "24x36",
    "A5 (14.8x21cm)", "A4 (21x29.7cm)", "A3 (29.7x42cm)",
    "A2 (42x59.4cm)", "A1 (59.4x84.1cm)",
    "50x70cm", "60x90cm", "70x100cm",
]
DIGITAL_PRICE = 4.07

# Print: 5 sizes with tiered pricing
PRINT_VARIANTS = [
    ("8x10",  27.00),
    ("11x14", 32.00),
    ("16x20", 44.00),
    ("18x24", 58.00),
    ("24x36", 87.00),
]


def build_digital_products() -> list[dict]:
    """Build product variants for digital listing: 12 styles × 18 sizes."""
    products = []
    for si, style in enumerate(STYLES, 1):
        for size in DIGITAL_SIZES:
            size_slug = size.split(" ")[0].replace(".", "").replace("x", "X")
            products.append({
                "sku": f"GLC-CNTYDIG-{si}-{size_slug}",
                "property_values": [
                    {"property_id": 513, "property_name": "Style", "values": [style]},
                    {"property_id": 514, "property_name": "Size", "values": [size]},
                ],
                "offerings": [{
                    "price": DIGITAL_PRICE,
                    "quantity": 999,
                    "is_enabled": True,
                }],
            })
    return products


def build_print_products() -> list[dict]:
    """Build product variants for print listing: 12 styles × 5 sizes."""
    products = []
    for si, style in enumerate(STYLES, 1):
        for size, price in PRINT_VARIANTS:
            products.append({
                "sku": f"GLC-CNTY-{si}-{size.replace('x', 'X')}",
                "property_values": [
                    {"property_id": 513, "property_name": "Style", "values": [style]},
                    {"property_id": 514, "property_name": "Size", "values": [size]},
                ],
                "offerings": [{
                    "price": price,
                    "quantity": 999,
                    "is_enabled": True,
                    "readiness_state_id": READINESS_STATE_ID,
                }],
            })
    return products


def main() -> None:
    client = EtsyClient()

    # Digital variants
    print(f"=== DIGITAL (listing {DIGITAL_LISTING_ID}) ===")
    digital_products = build_digital_products()
    print(f"  Pushing {len(digital_products)} variants (12 styles x 18 sizes)...")
    result = client.update_listing_inventory(
        listing_id=DIGITAL_LISTING_ID,
        products=digital_products,
        price_on_property=[513, 514],
        quantity_on_property=[513, 514],
        sku_on_property=[513, 514],
    )
    print(f"  OK — {len(result.get('products', []))} variants set")

    # Print variants
    print(f"\n=== PRINT (listing {PRINT_LISTING_ID}) ===")
    print_products = build_print_products()
    print(f"  Pushing {len(print_products)} variants (12 styles x 5 sizes)...")
    result = client.update_listing_inventory(
        listing_id=PRINT_LISTING_ID,
        products=print_products,
        price_on_property=[513, 514],
        quantity_on_property=[513, 514],
        sku_on_property=[513, 514],
    )
    print(f"  OK — {len(result.get('products', []))} variants set")

    print("\nDone! Check Etsy Listing Manager to verify dropdowns.")


if __name__ == "__main__":
    main()
