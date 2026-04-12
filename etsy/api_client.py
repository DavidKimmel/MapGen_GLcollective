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

    def _auth_headers(self) -> dict[str, str]:
        """Build auth headers (no Content-Type — let requests set it)."""
        token = get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "x-api-key": self._client_id,
        }

    def _headers(self) -> dict[str, str]:
        """Build request headers with JSON content type."""
        h = self._auth_headers()
        h["Content-Type"] = "application/json"
        return h

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        global _last_request_time
        elapsed = time.time() - _last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        _last_request_time = time.time()

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make an authenticated API request (JSON)."""
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

    def _form_request(self, method: str, path: str, data: dict) -> dict:
        """Make an authenticated request with form-urlencoded body.

        Etsy's createDraftListing requires application/x-www-form-urlencoded.
        """
        self._rate_limit()
        url = f"{API_BASE}{path}"
        headers = self._auth_headers()
        resp = self._session.request(method, url, headers=headers, data=data)

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

    def _upload(self, path: str, file_path: str, field: str = "image",
                extra_fields: dict | None = None) -> dict:
        """Upload a file (image/digital) to an Etsy endpoint."""
        self._rate_limit()
        url = f"{API_BASE}{path}"
        headers = self._auth_headers()

        ext = file_path.lower().rsplit(".", 1)[-1]
        mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "pdf": "application/pdf"}
        mime = mime_map.get(ext, "application/octet-stream")
        with open(file_path, "rb") as f:
            files = {field: (Path(file_path).name, f, mime)}
            resp = self._session.post(url, headers=headers, files=files,
                                      data=extra_fields or {})

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
        # shop_id may be directly in the response
        if user.get("shop_id"):
            return user["shop_id"]
        # Otherwise try the shops endpoint
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

    def get_return_policies(self, shop_id: int) -> list[dict]:
        """List return policies for the shop."""
        resp = self._request("GET", f"/application/shops/{shop_id}/policies/return")
        return resp.get("results", [])

    def get_shop_sections(self, shop_id: int) -> list[dict]:
        """List shop sections."""
        resp = self._request("GET", f"/application/shops/{shop_id}/sections")
        return resp.get("results", [])

    # ------------------------------------------------------------------
    # Listing operations
    # ------------------------------------------------------------------

    def get_listings_by_shop(
        self, shop_id: int, state: str = "active",
        limit: int = 25, offset: int = 0,
    ) -> dict:
        """Get listings for a shop."""
        params = {"state": state, "limit": limit, "offset": offset}
        return self._request("GET", f"/application/shops/{shop_id}/listings",
                             params=params)

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
        taxonomy_id: int = 67,
        listing_type: str = "physical",
        shipping_profile_id: int | None = None,
        return_policy_id: int | None = None,
        shop_section_id: int | None = None,
        readiness_state_id: int | None = None,
        is_supply: bool = False,
        should_auto_renew: bool = True,
        is_taxable: bool = True,
    ) -> dict:
        """Create a draft listing using form-urlencoded body.

        Returns created listing data including listing_id.
        """
        data: dict = {
            "title": title[:140],
            "description": description,
            "price": str(price),
            "quantity": str(quantity),
            "who_made": who_made,
            "when_made": when_made,
            "taxonomy_id": str(taxonomy_id),
            "type": listing_type,
            "is_supply": str(is_supply).lower(),
            "should_auto_renew": str(should_auto_renew).lower(),
            "is_taxable": str(is_taxable).lower(),
        }

        if tags:
            data["tags[]"] = tags[:13]

        if shipping_profile_id and listing_type == "physical":
            data["shipping_profile_id"] = str(shipping_profile_id)

        if return_policy_id:
            data["return_policy_id"] = str(return_policy_id)

        if shop_section_id:
            data["shop_section_id"] = str(shop_section_id)

        if readiness_state_id:
            data["readiness_state_id"] = str(readiness_state_id)

        # legacy=true enables readiness_state_id support
        path = f"/application/shops/{shop_id}/listings?legacy=true"
        return self._form_request("POST", path, data=data)

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
        alt_text: str = "",
    ) -> dict:
        """Upload an image to a listing.

        Args:
            shop_id: Shop ID
            listing_id: Listing ID
            image_path: Path to PNG/JPG file
            rank: Image position (1 = primary/hero image, up to 10)
            alt_text: Alt text for SEO (max 500 chars)
        """
        extra = {"rank": str(rank)}
        if alt_text:
            extra["alt_text"] = alt_text[:500]
        return self._upload(
            f"/application/shops/{shop_id}/listings/{listing_id}/images",
            image_path,
            field="image",
            extra_fields=extra,
        )

    def get_listing_images(self, shop_id: int, listing_id: int) -> list[dict]:
        """Get all images for a listing."""
        resp = self._request(
            "GET",
            f"/application/listings/{listing_id}/images",
        )
        return resp.get("results", [])

    def delete_listing_image(
        self, shop_id: int, listing_id: int, listing_image_id: int
    ) -> dict:
        """Delete a specific image from a listing."""
        return self._request(
            "DELETE",
            f"/application/shops/{shop_id}/listings/{listing_id}/images/{listing_image_id}",
        )

    # ------------------------------------------------------------------
    # Digital file operations
    # ------------------------------------------------------------------

    def upload_listing_file(
        self,
        shop_id: int,
        listing_id: int,
        file_path: str,
        name: str = "",
    ) -> dict:
        """Upload a digital file to a listing for buyer download.

        Args:
            shop_id: Shop ID
            listing_id: Listing ID
            file_path: Path to the file (PDF, ZIP, PNG, etc.)
            name: Display name for the file (shown to buyer)
        """
        extra = {}
        if name:
            extra["name"] = name
        return self._upload(
            f"/application/shops/{shop_id}/listings/{listing_id}/files",
            file_path,
            field="file",
            extra_fields=extra,
        )

    def get_listing_files(self, shop_id: int, listing_id: int) -> list[dict]:
        """Get digital files attached to a listing."""
        resp = self._request(
            "GET",
            f"/application/shops/{shop_id}/listings/{listing_id}/files",
        )
        return resp.get("results", [])

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
        """Update listing inventory (add size/format variants).

        Args:
            listing_id: The listing to update
            products: List of product variant dicts with sku, property_values, offerings
            price_on_property: Property IDs that affect price
            quantity_on_property: Property IDs that affect quantity
            sku_on_property: Property IDs that affect SKU
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
