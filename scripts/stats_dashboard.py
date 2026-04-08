#!/usr/bin/env python3
"""
GeoLine Collective — Stats Dashboard Generator.

Pulls listing stats, orders, and revenue from Etsy API and generates
a self-contained HTML dashboard.

Usage:
    python scripts/stats_dashboard.py
    python scripts/stats_dashboard.py --output custom_path.html
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from etsy.api_client import EtsyClient
from etsy.style_config import SHOP_ID

OUTPUT_DEFAULT = os.path.join(_PROJECT_DIR, "etsy", "dashboard.html")


def fetch_all_listings(client: EtsyClient) -> list[dict]:
    """Fetch all active listings (paginated)."""
    all_listings = []
    offset = 0
    while True:
        result = client._request(
            "GET", f"/application/shops/{SHOP_ID}/listings/active",
            params={"limit": 100, "offset": offset},
        )
        listings = result.get("results", [])
        all_listings.extend(listings)
        if len(listings) < 100:
            break
        offset += 100
    return all_listings


def fetch_listing_thumbnail(client: EtsyClient, listing_id: int) -> str:
    """Get the first image URL for a listing."""
    try:
        result = client._request("GET", f"/application/listings/{listing_id}/images")
        images = result.get("results", [])
        if images:
            return images[0].get("url_570xN", "")
    except Exception:
        pass
    return ""


def fetch_all_receipts(client: EtsyClient) -> list[dict]:
    """Fetch all receipts/orders."""
    all_receipts = []
    offset = 0
    while True:
        result = client._request(
            "GET", f"/application/shops/{SHOP_ID}/receipts",
            params={"limit": 25, "offset": offset},
        )
        receipts = result.get("results", [])
        all_receipts.extend(receipts)
        if len(receipts) < 25:
            break
        offset += 25
    return all_receipts


def fetch_transactions(client: EtsyClient) -> list[dict]:
    """Fetch all transactions (line items)."""
    all_txns = []
    offset = 0
    while True:
        result = client._request(
            "GET", f"/application/shops/{SHOP_ID}/transactions",
            params={"limit": 25, "offset": offset},
        )
        txns = result.get("results", [])
        all_txns.extend(txns)
        if len(txns) < 25:
            break
        offset += 25
    return all_txns


def categorize_listing(title: str) -> str:
    """Categorize a listing by product line based on title."""
    t = title.lower()
    if "county" in t:
        return "CountyMap"
    if "mosaic" in t or "colorful" in t:
        return "Florence"
    if "monochrome" in t or "monomap" in t or "mono" in t:
        return "MonoMap"
    if "blueprint" in t or "shaded" in t:
        return "Blueprint"
    if "house" in t or "home" in t:
        return "Custom House"
    if "custom" in t:
        return "Custom"
    return "Classic"


def generate_html(listings: list, receipts: list, transactions: list,
                   thumbnails: dict[int, str] | None = None) -> str:
    """Generate the HTML dashboard."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # --- Listing stats ---
    total_views = sum(l.get("views", 0) for l in listings)
    total_favs = sum(l.get("num_favorers", 0) for l in listings)
    total_listings = len(listings)

    # Top by views
    by_views = sorted(listings, key=lambda x: x.get("views", 0), reverse=True)[:20]

    # By category
    cat_stats: dict[str, dict] = {}
    for l in listings:
        cat = categorize_listing(l.get("title", ""))
        if cat not in cat_stats:
            cat_stats[cat] = {"count": 0, "views": 0, "favs": 0}
        cat_stats[cat]["count"] += 1
        cat_stats[cat]["views"] += l.get("views", 0)
        cat_stats[cat]["favs"] += l.get("num_favorers", 0)

    # --- Order stats ---
    total_orders = len(receipts)
    total_revenue = sum(
        r.get("grandtotal", {}).get("amount", 0) / r.get("grandtotal", {}).get("divisor", 100)
        for r in receipts
    )
    total_subtotal = sum(
        r.get("subtotal", {}).get("amount", 0) / r.get("subtotal", {}).get("divisor", 100)
        for r in receipts
    )

    # --- Transaction details ---
    txn_rows = ""
    for t in transactions:
        title = t.get("title", "")[:50]
        price = t.get("price", {}).get("amount", 0) / t.get("price", {}).get("divisor", 100)
        qty = t.get("quantity", 1)
        created = datetime.fromtimestamp(t.get("created_timestamp", 0), tz=timezone.utc).strftime("%Y-%m-%d")
        txn_rows += f"""
            <tr>
                <td>{created}</td>
                <td>{title}</td>
                <td>${price:.2f}</td>
                <td>{qty}</td>
            </tr>"""

    # --- Top listings cards ---
    if thumbnails is None:
        thumbnails = {}
    top_cards = ""
    for l in by_views:
        title = l.get("title", "")[:55]
        cat = categorize_listing(l.get("title", ""))
        views = l.get("views", 0)
        favs = l.get("num_favorers", 0)
        lid = l.get("listing_id", "")
        thumb = thumbnails.get(lid, "")
        img_html = f'<img src="{thumb}" alt="" class="listing-thumb">' if thumb else '<div class="listing-thumb-placeholder"></div>'
        top_cards += f"""
            <a href="https://www.etsy.com/listing/{lid}" target="_blank" class="listing-card">
                {img_html}
                <div class="listing-card-body">
                    <div class="listing-card-title">{title}</div>
                    <span class="badge badge-{cat.lower().replace(' ', '')}">{cat}</span>
                    <div class="listing-card-stats">
                        <span>{views} views</span>
                        <span>{favs} favs</span>
                    </div>
                </div>
            </a>"""

    # --- Category rows ---
    cat_rows = ""
    for cat in sorted(cat_stats.keys(), key=lambda c: cat_stats[c]["views"], reverse=True):
        s = cat_stats[cat]
        cat_rows += f"""
            <tr>
                <td><span class="badge badge-{cat.lower().replace(' ', '')}">{cat}</span></td>
                <td>{s['count']}</td>
                <td>{s['views']}</td>
                <td>{s['favs']}</td>
                <td>{s['views'] / s['count']:.1f}</td>
            </tr>"""

    # --- Order rows ---
    order_rows = ""
    for r in receipts:
        rid = r.get("receipt_id", "")
        total = r.get("grandtotal", {}).get("amount", 0) / r.get("grandtotal", {}).get("divisor", 100)
        status = r.get("status", "")
        created = datetime.fromtimestamp(r.get("create_timestamp", 0), tz=timezone.utc).strftime("%Y-%m-%d")
        buyer = r.get("name", "")
        order_rows += f"""
            <tr>
                <td>{created}</td>
                <td>{rid}</td>
                <td>{buyer}</td>
                <td>${total:.2f}</td>
                <td><span class="status status-{status.lower()}">{status}</span></td>
            </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GeoLine Collective — Dashboard</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0f1117; color: #e0e0e0; padding: 20px; }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    h1 {{ font-size: 1.8em; color: #fff; margin-bottom: 5px; }}
    .subtitle {{ color: #888; margin-bottom: 30px; font-size: 0.9em; }}

    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 30px; }}
    .card {{ background: #1a1d27; border-radius: 12px; padding: 20px; border: 1px solid #2a2d37; }}
    .card-label {{ font-size: 0.8em; color: #888; text-transform: uppercase; letter-spacing: 1px; }}
    .card-value {{ font-size: 2.2em; font-weight: 700; color: #fff; margin-top: 5px; }}
    .card-value.green {{ color: #4ade80; }}
    .card-value.blue {{ color: #60a5fa; }}
    .card-value.purple {{ color: #a78bfa; }}
    .card-value.amber {{ color: #fbbf24; }}

    .section {{ background: #1a1d27; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #2a2d37; }}
    .section h2 {{ font-size: 1.1em; color: #fff; margin-bottom: 15px; }}

    table {{ width: 100%; border-collapse: collapse; font-size: 0.85em; }}
    th {{ text-align: left; padding: 10px 12px; color: #888; border-bottom: 1px solid #2a2d37; font-weight: 500; text-transform: uppercase; font-size: 0.75em; letter-spacing: 1px; }}
    td {{ padding: 8px 12px; border-bottom: 1px solid #1f222e; }}
    tr:hover {{ background: #1f222e; }}
    a {{ color: #60a5fa; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}

    .badge {{ padding: 3px 10px; border-radius: 12px; font-size: 0.75em; font-weight: 600; }}
    .badge-classic {{ background: #2a3a2a; color: #86efac; }}
    .badge-florence {{ background: #3a2a2a; color: #fca5a5; }}
    .badge-blueprint {{ background: #2a2a3a; color: #93c5fd; }}
    .badge-monomap {{ background: #3a3a2a; color: #fde68a; }}
    .badge-countymap {{ background: #2a3a3a; color: #5eead4; }}
    .badge-custom {{ background: #3a2a3a; color: #d8b4fe; }}
    .badge-customhouse {{ background: #3a3020; color: #fdba74; }}

    .status {{ padding: 3px 10px; border-radius: 12px; font-size: 0.75em; font-weight: 600; }}
    .status-completed {{ background: #1a3a2a; color: #4ade80; }}
    .status-open {{ background: #3a3a1a; color: #fbbf24; }}
    .status-paid {{ background: #2a2a3a; color: #93c5fd; }}

    .listing-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }}
    .listing-card {{ background: #22252f; border-radius: 10px; overflow: hidden; border: 1px solid #2a2d37; text-decoration: none; color: #e0e0e0; transition: border-color 0.2s, transform 0.2s; display: flex; flex-direction: column; }}
    .listing-card:hover {{ border-color: #60a5fa; transform: translateY(-2px); }}
    .listing-thumb {{ width: 100%; aspect-ratio: 1; object-fit: cover; display: block; }}
    .listing-thumb-placeholder {{ width: 100%; aspect-ratio: 1; background: #2a2d37; }}
    .listing-card-body {{ padding: 10px 12px 12px; flex: 1; display: flex; flex-direction: column; gap: 6px; }}
    .listing-card-title {{ font-size: 0.8em; line-height: 1.3; color: #ccc; }}
    .listing-card-stats {{ display: flex; gap: 12px; font-size: 0.75em; color: #888; margin-top: auto; }}

    .footer {{ text-align: center; color: #555; font-size: 0.8em; margin-top: 30px; }}
</style>
</head>
<body>
<div class="container">
    <h1>GeoLine Collective</h1>
    <p class="subtitle">Dashboard updated {now}</p>

    <div class="cards">
        <div class="card">
            <div class="card-label">Active Listings</div>
            <div class="card-value blue">{total_listings}</div>
        </div>
        <div class="card">
            <div class="card-label">Total Views</div>
            <div class="card-value purple">{total_views}</div>
        </div>
        <div class="card">
            <div class="card-label">Favorites</div>
            <div class="card-value amber">{total_favs}</div>
        </div>
        <div class="card">
            <div class="card-label">Orders</div>
            <div class="card-value green">{total_orders}</div>
        </div>
        <div class="card">
            <div class="card-label">Revenue</div>
            <div class="card-value green">${total_revenue:.2f}</div>
        </div>
        <div class="card">
            <div class="card-label">Avg Order</div>
            <div class="card-value">${total_revenue / max(total_orders, 1):.2f}</div>
        </div>
    </div>

    <div class="section">
        <h2>Product Lines</h2>
        <table>
            <thead><tr><th>Product</th><th>Listings</th><th>Views</th><th>Favs</th><th>Avg Views</th></tr></thead>
            <tbody>{cat_rows}</tbody>
        </table>
    </div>

    <div class="section">
        <h2>Top Listings by Views</h2>
        <div class="listing-grid">
            {top_cards}
        </div>
    </div>

    <div class="section">
        <h2>Orders</h2>
        <table>
            <thead><tr><th>Date</th><th>Order ID</th><th>Buyer</th><th>Total</th><th>Status</th></tr></thead>
            <tbody>{order_rows}</tbody>
        </table>
    </div>

    <div class="section">
        <h2>Transaction Details</h2>
        <table>
            <thead><tr><th>Date</th><th>Item</th><th>Price</th><th>Qty</th></tr></thead>
            <tbody>{txn_rows}</tbody>
        </table>
    </div>

    <p class="footer">GeoLine Collective &mdash; Cartography as Craft &mdash; {now}</p>
</div>
</body>
</html>"""

    return html


def main() -> None:
    parser = argparse.ArgumentParser(description="GeoLine Stats Dashboard")
    parser.add_argument("--output", "-o", default=OUTPUT_DEFAULT)
    args = parser.parse_args()

    client = EtsyClient()

    print("Fetching listings...")
    listings = fetch_all_listings(client)
    print(f"  {len(listings)} active listings")

    print("Fetching orders...")
    receipts = fetch_all_receipts(client)
    print(f"  {len(receipts)} orders")

    print("Fetching transactions...")
    transactions = fetch_transactions(client)
    print(f"  {len(transactions)} transactions")

    print("Fetching thumbnails for top listings...")
    by_views = sorted(listings, key=lambda x: x.get("views", 0), reverse=True)[:20]
    thumbnails: dict[int, str] = {}
    for l in by_views:
        lid = l.get("listing_id", 0)
        thumb = fetch_listing_thumbnail(client, lid)
        if thumb:
            thumbnails[lid] = thumb
    print(f"  {len(thumbnails)} thumbnails fetched")

    print("Generating dashboard...")
    html = generate_html(listings, receipts, transactions, thumbnails)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\nDashboard saved: {args.output}")
    print(f"Open in browser: file:///{args.output.replace(os.sep, '/')}")


if __name__ == "__main__":
    main()
