"""Generate branded delivery PDFs for AtlasMap digital downloads.

Each PDF contains:
  - GeoLine Collective branding
  - State map preview thumbnail
  - Clickable Dropbox links for all 5 sizes
  - Print tips

Usage:
    python -m scripts.generate_delivery_pdf --state Alabama
    python -m scripts.generate_delivery_pdf --all
    python -m scripts.generate_delivery_pdf --all --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib import request, error

from fpdf import FPDF
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))

ATLAS_DIR = Path(r"C:\MapGen_GLcollective\etsy\renders\AtlasMap\print_ready")
FONTS_DIR = Path(r"C:\MapGen_GLcollective\fonts")
OUT_DIR = Path(r"C:\MapGen_GLcollective\etsy\renders\AtlasMap\delivery_pdfs")
DROPBOX_BASE = "/GeoLine/ElevationMaps"

# Load .env for Dropbox token
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

HORIZONTAL_STATES: set[str] = {
    "Alaska", "Arkansas", "Colorado", "Connecticut", "Florida", "Hawaii",
    "Iowa", "Kansas", "Kentucky", "Louisiana", "Maryland", "Massachusetts",
    "Missouri", "Montana", "Nebraska", "NewYork", "NorthCarolina",
    "NorthDakota", "Oklahoma", "Oregon", "Pennsylvania", "SouthCarolina",
    "SouthDakota", "Tennessee", "Texas", "Virginia", "Washington",
    "WestVirginia", "Wyoming",
}

# Brand colors
BG_DARK = (15, 17, 23)       # #0f1117
TEXT_WHITE = (224, 224, 224)  # #e0e0e0
ACCENT_CYAN = (96, 165, 250) # #60a5fa
TEXT_GRAY = (136, 136, 136)   # #888888
CARD_BG = (26, 29, 39)       # #1a1d27


def display_name(folder_name: str) -> str:
    return re.sub(r'([a-z])([A-Z])', r'\1 \2', folder_name)


def get_sizes(state: str) -> list[str]:
    if state in HORIZONTAL_STATES:
        return ["10x8", "14x11", "20x16", "24x18", "36x24"]
    return ["8x10", "11x14", "16x20", "18x24", "24x36"]


def get_display_sizes() -> list[str]:
    """Display sizes always shown in standard WxH format."""
    return ["8x10", "11x14", "16x20", "18x24", "24x36"]


def get_dropbox_shared_link(token: str, path: str) -> str | None:
    """Create or get a shared link for a Dropbox file."""
    # First try to create a new link
    url = "https://api.dropboxapi.com/2/sharing/create_shared_link_with_settings"
    body = json.dumps({
        "path": path,
        "settings": {"requested_visibility": "public"},
    })
    req = request.Request(url, data=body.encode(), headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    try:
        resp = request.urlopen(req)
        data = json.loads(resp.read())
        return data["url"].replace("?dl=0", "?dl=1")
    except error.HTTPError as e:
        body_text = e.read().decode()
        if "shared_link_already_exists" not in body_text:
            print(f"    Dropbox link error for {path}: {body_text[:200]}")
            return None

    # Link already exists — fetch it
    url2 = "https://api.dropboxapi.com/2/sharing/list_shared_links"
    body2 = json.dumps({"path": path, "direct_only": True})
    req2 = request.Request(url2, data=body2.encode(), headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    try:
        resp2 = request.urlopen(req2)
        data2 = json.loads(resp2.read())
        links = data2.get("links", [])
        if links:
            return links[0]["url"].replace("?dl=0", "?dl=1")
    except error.HTTPError as e2:
        print(f"    Dropbox list_shared_links error: {e2.read().decode()[:200]}")
    return None


def create_preview_thumbnail(state: str) -> Path:
    """Create a small JPEG preview from the smallest render."""
    sizes = get_sizes(state)
    smallest = sizes[0]
    render = None
    for f in (ATLAS_DIR / state).iterdir():
        if f.name.endswith(f"_{smallest}.png"):
            render = f
            break
    if not render:
        raise FileNotFoundError(f"No {smallest} render for {state}")

    img = Image.open(str(render)).convert("RGB")
    # Resize to fit nicely in the PDF (~400px wide)
    ratio = 400 / img.width
    img = img.resize((400, int(img.height * ratio)), Image.LANCZOS)

    thumb_path = ATLAS_DIR / state / f"_thumb_{state.lower()}.jpg"
    img.save(str(thumb_path), "JPEG", quality=85)
    return thumb_path


def generate_pdf(state: str, links: dict[str, str]) -> Path:
    """Generate the branded delivery PDF for a state."""
    name = display_name(state)
    display_sizes = get_display_sizes()

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.set_margin(0)
    pdf.add_page()

    # Register fonts
    pdf.add_font("Montserrat", "", str(FONTS_DIR / "Montserrat-Bold.ttf"))
    pdf.add_font("Cormorant", "", str(FONTS_DIR / "CormorantGaramond-Regular.ttf"))
    pdf.add_font("CormorantBold", "", str(FONTS_DIR / "CormorantGaramond-Bold.ttf"))
    pdf.add_font("CormorantLight", "", str(FONTS_DIR / "CormorantGaramond-Light.ttf"))

    w = pdf.w
    h = pdf.h

    # ── Dark background ──
    pdf.set_fill_color(*BG_DARK)
    pdf.rect(0, 0, w, h, "F")

    # ── Logo ──
    logo_path = Path(r"C:\MapGen_GLcollective\etsy\renders\ASSETS\nano-banana-2_Round_emblem_logo_for_a_map_company_called_GEOLINE_COLLECTIVE_cartography_inspir-1.jpg")
    logo_w = 30  # mm
    pdf.image(str(logo_path), x=(w - logo_w) / 2, y=10, w=logo_w)
    pdf.set_y(10 + logo_w + 4)

    # ── State name ──
    pdf.set_font("CormorantBold", size=32)
    pdf.set_text_color(*TEXT_WHITE)
    pdf.cell(w, 14, name.upper(), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    pdf.set_font("Cormorant", size=13)
    pdf.set_text_color(*TEXT_GRAY)
    pdf.cell(w, 6, "Topographic Elevation Map", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── Map preview (smaller) ──
    try:
        thumb = create_preview_thumbnail(state)
        img_w = 50  # mm — smaller since buyer already knows what it looks like
        img = Image.open(str(thumb))
        img_h = img_w * (img.height / img.width)
        x = (w - img_w) / 2
        pdf.image(str(thumb), x=x, y=pdf.get_y(), w=img_w)
        pdf.ln(img_h + 6)
    except Exception as e:
        print(f"    Preview failed: {e}")
        pdf.ln(8)

    # ── Download section ──
    pdf.set_font("Montserrat", size=10)
    pdf.set_text_color(*ACCENT_CYAN)
    pdf.cell(w, 6, "YOUR DOWNLOAD LINKS", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Thin line
    pdf.set_draw_color(40, 43, 55)
    pdf.set_line_width(0.3)
    pdf.line(40, pdf.get_y(), w - 40, pdf.get_y())
    pdf.ln(6)

    # Size links — centered cards
    margin = 40
    card_w = w - (margin * 2)
    actual_sizes = get_sizes(state)
    for display_size, actual_size in zip(display_sizes, actual_sizes):
        link_url = links.get(actual_size, "")
        y_start = pdf.get_y()

        # Card background
        pdf.set_fill_color(*CARD_BG)
        pdf.rect(margin, y_start, card_w, 11, "F")

        # Size label — left side of card
        pdf.set_xy(margin + 10, y_start + 1.5)
        pdf.set_font("CormorantBold", size=14)
        pdf.set_text_color(*TEXT_WHITE)
        pdf.cell(30, 8, f'{display_size}"')

        # Link — right side of card
        if link_url:
            pdf.set_xy(margin + card_w - 60, y_start + 2)
            pdf.set_font("Cormorant", size=11)
            pdf.set_text_color(*ACCENT_CYAN)
            pdf.cell(50, 7, "Click to Download", align="R", link=link_url)
        else:
            pdf.set_xy(margin + card_w - 60, y_start + 2)
            pdf.set_font("Cormorant", size=11)
            pdf.set_text_color(*TEXT_GRAY)
            pdf.cell(50, 7, "Link pending", align="R")

        pdf.set_y(y_start + 14)

    pdf.ln(6)

    # ── Print tips — centered ──
    pdf.set_draw_color(40, 43, 55)
    pdf.line(margin, pdf.get_y(), w - margin, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("Montserrat", size=9)
    pdf.set_text_color(*TEXT_GRAY)
    pdf.cell(w, 5, "PRINTING TIPS", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    tips = [
        "Print at 100% scale — do not resize or fit to page",
        "Use matte or luster paper for best results",
        "Any local print shop (FedEx, Staples) can print these files",
        "For the sharpest output, use the size that matches your frame",
    ]
    pdf.set_font("CormorantLight", size=10)
    pdf.set_text_color(*TEXT_GRAY)
    for tip in tips:
        pdf.set_x(margin)
        pdf.cell(card_w, 5.5, tip, align="C", new_x="LMARGIN", new_y="NEXT")

    # ── Footer (flows after content, not absolute positioned) ──
    pdf.ln(8)
    pdf.set_draw_color(40, 43, 55)
    pdf.line(40, pdf.get_y(), w - 40, pdf.get_y())
    pdf.ln(5)
    pdf.set_font("Cormorant", size=11)
    pdf.set_text_color(*TEXT_GRAY)
    pdf.cell(w, 5, "Thank you for your purchase!", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font("CormorantLight", size=9)
    pdf.cell(w, 5, "Questions? Message us on Etsy — we're happy to help.", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Montserrat", size=7)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(w, 4, "© GeoLine Collective — Cartography as Craft", align="C")

    # Save
    # Write into the state's own folder, not the central delivery_pdfs dir
    out_path = ATLAS_DIR / state / f"{state}_delivery.pdf"
    pdf.output(str(out_path))

    # Clean up thumbnail (may fail on Windows if fpdf holds the handle)
    thumb_file = OUT_DIR / f"_thumb_{state.lower()}.jpg"
    try:
        if thumb_file.exists():
            thumb_file.unlink()
    except PermissionError:
        pass  # cleaned up next run or manually

    return out_path


def generate_links_for_state(token: str, state: str) -> dict[str, str]:
    """Generate Dropbox shared links for all sizes of a state."""
    sizes = get_sizes(state)
    links: dict[str, str] = {}
    for size in sizes:
        # Find the actual filename
        for f in (ATLAS_DIR / state).iterdir():
            if f.name.endswith(f"_{size}.png"):
                dropbox_path = f"{DROPBOX_BASE}/{state}/{f.name}"
                link = get_dropbox_shared_link(token, dropbox_path)
                if link:
                    links[size] = link
                break
        time.sleep(0.3)  # rate limit
    return links


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AtlasMap delivery PDFs.")
    parser.add_argument("--state", help="Single state.")
    parser.add_argument("--all", action="store_true", help="All 50 states.")
    parser.add_argument("--dry-run", action="store_true", help="Generate PDF without Dropbox links.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    token = os.getenv("DROPBOX_ACCESS_TOKEN", "")

    if args.state:
        states = [args.state]
    elif args.all:
        states = sorted([d.name for d in ATLAS_DIR.iterdir()
                         if d.is_dir() and not d.name.startswith("_")
                         and d.name not in ("new_mockups", "new_mockups_fill")])
    else:
        print("Specify --state or --all")
        return 1

    print(f"Generating {len(states)} delivery PDFs\n")

    for i, state in enumerate(states, 1):
        print(f"[{i}/{len(states)}] {display_name(state)}")

        if args.dry_run or not token:
            links = {s: "" for s in get_sizes(state)}
            if not token:
                print("    (no Dropbox token — links will say 'pending')")
        else:
            links = generate_links_for_state(token, state)
            print(f"    {len(links)} Dropbox links generated")

        out = generate_pdf(state, links)
        size_kb = out.stat().st_size // 1024
        print(f"    wrote {out.name} ({size_kb} KB)")

    print(f"\nDone. PDFs in {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
