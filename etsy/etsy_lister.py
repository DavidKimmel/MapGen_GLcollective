# etsy/etsy_lister.py
"""Orchestrates Etsy listing creation — draft + images + variants in one call."""

from __future__ import annotations

import os
import time
from pathlib import Path

from etsy.api_client import EtsyClient
from etsy.style_config import (
    StyleConfig, SHOP_ID, SHIPPING_PROFILE_ID, RETURN_POLICY_ID,
    READINESS_STATE_ID, TAXONOMY_ID,
)


def create_full_listing(
    client: EtsyClient,
    title: str,
    description: str,
    tags: list[str],
    style: StyleConfig,
    image_paths: list[str],
    image_alt_texts: list[str] | None = None,
) -> dict:
    """Create a complete Etsy draft listing with images and variants.

    Returns dict with listing_id and variant count.
    """
    # Ensure tags are max 20 chars
    clean_tags = [t[:20] for t in tags[:13]]

    # Create draft
    base_price = min(v.price for v in style.variants)
    result = client.create_draft_listing(
        shop_id=SHOP_ID,
        title=title,
        description=description,
        price=base_price,
        quantity=999,
        tags=clean_tags,
        who_made="i_did",
        when_made="made_to_order",
        taxonomy_id=TAXONOMY_ID,
        listing_type="physical",
        shipping_profile_id=SHIPPING_PROFILE_ID,
        return_policy_id=RETURN_POLICY_ID,
        shop_section_id=style.shop_section_id,
        readiness_state_id=READINESS_STATE_ID,
    )
    listing_id = result["listing_id"]

    # Upload images (max 10)
    alt_texts = image_alt_texts or [""] * len(image_paths)
    for rank, (img_path, alt) in enumerate(zip(image_paths[:10], alt_texts[:10]), 1):
        if os.path.exists(img_path):
            client.upload_listing_image(
                SHOP_ID, listing_id, img_path, rank=rank, alt_text=alt[:500],
            )
            time.sleep(0.3)

    # Set inventory variants
    products = []
    for v in style.variants:
        products.append({
            "sku": f"{style.sku_prefix}-{v.sku_suffix}".upper(),
            "property_values": [
                {"property_id": 513, "property_name": "Format", "values": [v.format_name]},
                {"property_id": 514, "property_name": "Size", "values": [v.size]},
            ],
            "offerings": [{
                "price": v.price,
                "quantity": 999,
                "is_enabled": True,
                "readiness_state_id": READINESS_STATE_ID,
            }],
        })

    client.update_listing_inventory(
        listing_id=listing_id,
        products=products,
        price_on_property=[513, 514],
        quantity_on_property=[513, 514],
        sku_on_property=[513, 514],
    )

    return {"listing_id": listing_id, "variant_count": len(products)}
