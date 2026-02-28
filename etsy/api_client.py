"""GeoLine Collective — Etsy Open API v3 Client.

Thin wrapper around the Etsy API for listing management.
Handles authentication, rate limiting, and common operations.

Usage:
    from etsy.api_client import EtsyClient

    client = EtsyClient()
    shop_id = client.get_shop_id()
    listing = client.create_draft_listing(shop_id, title=..., ...)
"""

from __future__ import annotations

import time
from pathlib import Path

import requests

from etsy.auth import get_access_token, get_client_id, _load_credentials

API_BASE = "https://openapi.etsy.com/v3"

# Etsy rate limit: 5 QPS. We stay under with a small delay.
_MIN_REQUEST_INTERVAL = 0.25  # 4 QPS max
_last_request_time = 0.0


class EtsyApiError(Exception):
    """Raised when an Etsy API call fails."""
    def __init__(self, status_code: int, message: str, response: dict | None = None):
        self.status_code = status_code
        self.response = response
        super().__init__(f"Etsy API error {status_code}: {message}")


class EtsyClient:
    """Client for Etsy Open API v3."""

    def __init__(self):
        self._client_id = get_client_id()
        self._session = requests.Session()

    def _headers(self) -> dict[str, str]:
        """Build request headers with current access token."""
        token = get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "x-api-key": self._client_id,
            "Content-Type": "application/json",
        }

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        global _last_request_time
        elapsed = time.time() - _last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        _last_request_time = time.time()

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make an authenticated API request."""
        self._rate_limit()
        url = f"{API_BASE}{path}"
        resp = self._session.request(method, url, headers=self._headers(), **kwargs)

        if resp.status_code >= 400:
            try:
                error_data = resp.json()
                msg = error_data.get("error", resp.text)
            except Exception:
                error_data = None
                msg = resp.text
            raise EtsyApiError(resp.status_code, msg, error_data)

        if resp.status_code == 204:
            return {}
        return resp.json()

    def _upload(self, path: str, file_path: str, field: str = "image") -> dict:
        """Upload a file (image) to an Etsy endpoint."""
        self._rate_limit()
        url = f"{API_BASE}{path}"
        token = get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "x-api-key": self._client_id,
        }
        with open(file_path, "rb") as f:
            files = {field: (Path(file_path).name, f, "image/png")}
            resp = self._session.post(url, headers=headers, files=files)

        if resp.status_code >= 400:
            try:
                error_data = resp.json()
                msg = error_data.get("error", resp.text)
            except Exception:
                error_data = None
                msg = resp.text
            raise EtsyApiError(resp.status_code, msg, error_data)

        return resp.json()

    # ------------------------------------------------------------------
    # Shop operations
    # ------------------------------------------------------------------

    def get_me(self) -> dict:
        """Get the authenticated user's info."""
        return self._request("GET", "/application/users/me")

    def get_shop_id(self) -> int:
        """Get the shop ID for the authenticated user."""
        user = self.get_me()
        user_id = user.get("user_id")
        if not user_id:
            raise EtsyApiError(0, "No user_id in response")
        shop = self._request("GET", f"/application/users/{user_id}/shops")
        results = shop.get("results", [])
        if not results:
            raise EtsyApiError(0, "No shop found for this user")
        return results[0]["shop_id"]

    def get_shipping_profiles(self, shop_id: int) -> list[dict]:
        """List shipping profiles for the shop."""
        resp = self._request("GET", f"/application/shops/{shop_id}/shipping-profiles")
        return resp.get("results", [])

    # ------------------------------------------------------------------
    # Listing operations
    # ------------------------------------------------------------------

    def create_draft_listing(
        self,
        shop_id: int,
        title: str,
        description: str,
        price: float,
        quantity: int = 999,
        tags: list[str] | None = None,
        who_made: str = "i_did",
        when_made: str = "made_to_order",
        taxonomy_id: int = 67,  # Art & Collectibles > Prints > Digital Prints
        is_digital: bool = True,
        shipping_profile_id: int | None = None,
    ) -> dict:
        """Create a draft listing.

        Args:
            shop_id: Your Etsy shop ID
            title: Listing title (max 140 chars)
            description: Full description
            price: Base price in USD
            quantity: Available quantity
            tags: Up to 13 search tags
            who_made: "i_did", "someone_else", "collective"
            when_made: "made_to_order", "2020_2024", etc.
            taxonomy_id: Etsy category ID (67 = digital prints)
            is_digital: True for digital downloads
            shipping_profile_id: Required for physical items

        Returns:
            Created listing data including listing_id.
        """
        body: dict = {
            "title": title[:140],
            "description": description,
            "price": price,
            "quantity": quantity,
            "who_made": who_made,
            "when_made": when_made,
            "taxonomy_id": taxonomy_id,
            "is_digital": is_digital,
            "type": "download" if is_digital else "physical",
        }

        if tags:
            body["tags"] = tags[:13]  # Etsy max 13

        if shipping_profile_id and not is_digital:
            body["shipping_profile_id"] = shipping_profile_id

        return self._request(
            "POST",
            f"/application/shops/{shop_id}/listings",
            json=body,
        )

    def update_listing(self, shop_id: int, listing_id: int, **fields) -> dict:
        """Update fields on an existing listing."""
        return self._request(
            "PATCH",
            f"/application/shops/{shop_id}/listings/{listing_id}",
            json=fields,
        )

    def activate_listing(self, shop_id: int, listing_id: int) -> dict:
        """Set a listing's state to active (publish it)."""
        return self.update_listing(shop_id, listing_id, state="active")

    def get_listing(self, listing_id: int) -> dict:
        """Get a listing by ID."""
        return self._request("GET", f"/application/listings/{listing_id}")

    # ------------------------------------------------------------------
    # Image operations
    # ------------------------------------------------------------------

    def upload_listing_image(
        self,
        shop_id: int,
        listing_id: int,
        image_path: str,
        rank: int = 1,
    ) -> dict:
        """Upload an image to a listing.

        Args:
            shop_id: Shop ID
            listing_id: Listing ID
            image_path: Path to PNG/JPG file
            rank: Image position (1 = primary/hero image)

        Returns:
            Uploaded image data.
        """
        return self._upload(
            f"/application/shops/{shop_id}/listings/{listing_id}/images",
            image_path,
            field="image",
        )

    # ------------------------------------------------------------------
    # Inventory / variant operations
    # ------------------------------------------------------------------

    def get_listing_inventory(self, listing_id: int) -> dict:
        """Get inventory/variants for a listing."""
        return self._request("GET", f"/application/listings/{listing_id}/inventory")

    def update_listing_inventory(
        self,
        listing_id: int,
        products: list[dict],
        price_on_property: list[int] | None = None,
        quantity_on_property: list[int] | None = None,
        sku_on_property: list[int] | None = None,
    ) -> dict:
        """Update listing inventory (add size/style variants).

        Args:
            listing_id: The listing to update
            products: List of product variant dicts
            price_on_property: Property IDs that affect price
            quantity_on_property: Property IDs that affect quantity
            sku_on_property: Property IDs that affect SKU

        Returns:
            Updated inventory data.
        """
        body: dict = {"products": products}
        if price_on_property is not None:
            body["price_on_property"] = price_on_property
        if quantity_on_property is not None:
            body["quantity_on_property"] = quantity_on_property
        if sku_on_property is not None:
            body["sku_on_property"] = sku_on_property

        return self._request(
            "PUT",
            f"/application/listings/{listing_id}/inventory",
            json=body,
        )
