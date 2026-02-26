"""
MapGen — Pin/Marker System.

Geocodes a street address and renders a visual marker on the map.
5 pin styles: heart, heart-pin, pin, house, graduation cap.
All pins support custom color.

SVG path data from Font Awesome 6 Free (CC BY 4.0).
Ported from GeoLineCollective's pin_renderer.py.
"""

import math
import re
import time

import numpy as np
import pyproj
from geopy.geocoders import Nominatim
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MplPath

from utils.cache import cache_get, cache_set, CacheError
from utils.logging import safe_print

# ---------------------------------------------------------------------------
# Font Awesome 6 Free SVG paths (License: CC BY 4.0)
# ---------------------------------------------------------------------------
_FA_PIN_D = (
    "M384 192c0 87.4-117 243-168.3 307.2c-12.3 15.3-35.1 15.3-47.4 0"
    "C117 435 0 279.4 0 192C0 86 86 0 192 0S384 86 384 192z"
)
_FA_PIN_VBW, _FA_PIN_VBH = 384, 512

_FA_HEART_D = (
    "M47.6 300.4L228.3 469.1c7.5 7 17.4 10.9 27.7 10.9s20.2-3.9 27.7-10.9"
    "L464.4 300.4c30.4-28.3 47.6-68 47.6-109.5v-5.8c0-69.9-50.5-129.5-119.4-141"
    "C347 36.5 300.6 51.4 268 84L256 96 244 84c-32.6-32.6-79-47.5-124.6-39.9"
    "C50.5 55.6 0 115.2 0 185.1v5.8c0 41.5 17.2 81.2 47.6 109.5z"
)
_FA_HEART_VBW, _FA_HEART_VBH = 512, 512

_FA_HOUSE_D = (
    "M575.8 255.5c0 18-15 32.1-32 32.1h-32l.7 160.2c0 2.7-.2 5.4-.5 8.1V472"
    "c0 22.1-17.9 40-40 40H456c-1.1 0-2.2 0-3.3-.1c-1.4 .1-2.8 .1-4.2 .1H416"
    " 392c-22.1 0-40-17.9-40-40V448 384c0-17.7-14.3-32-32-32H256c-17.7 0-32"
    " 14.3-32 32v64 24c0 22.1-17.9 40-40 40H160 128.1c-1.5 0-3-.1-4.5-.2c-1.2"
    " .1-2.4 .2-3.6 .2H104c-22.1 0-40-17.9-40-40V360c0-.9 0-1.9 .1-2.8V287.6"
    "H32c-18 0-32-14-32-32.1c0-9 3-17 10-24L266.4 8c7-7 15-8 22-8s15 2 21 7"
    "L564.8 231.5c8 7 12 15 11 24z"
)
_FA_HOUSE_VBW, _FA_HOUSE_VBH = 576, 512

_FA_GRADCAP_D = (
    "M320 32c-8.1 0-16.1 1.4-23.7 4.1L15.8 137.4C6.3 140.9 0 149.9 0 160"
    "s6.3 19.1 15.8 22.6l57.9 20.9C57.3 229.3 48 259.8 48 291.9v28.1"
    "c0 28.4-10.8 57.7-22.3 80.8c-6.5 13-13.9 25.8-22.5 37.6C0 442.7-.9 448.3"
    " .9 453.4s6 8.9 11.2 10.2l64 16c4.2 1.1 8.7 .3 12.4-2s6.3-6.1 7.1-10.4"
    "c8.6-42.8 4.3-81.2-2.1-108.7C90.3 344.3 86 329.8 80 316.5V291.9"
    "c0-30.2 10.2-58.7 27.9-81.5c12.9-15.5 29.6-28 49.2-35.7l157-61.7"
    "c8.2-3.2 17.5 .8 20.7 9s-.8 17.5-9 20.7l-157 61.7c-12.4 4.9-23.3 12.4-32.2"
    " 21.6l159.6 57.6c7.6 2.7 15.6 4.1 23.7 4.1s16.1-1.4 23.7-4.1L624.2 182.6"
    "c9.5-3.4 15.8-12.5 15.8-22.6s-6.3-19.1-15.8-22.6L343.7 36.1C336.1 33.4"
    " 328.1 32 320 32zM128 408c0 35.3 86 72 192 72s192-36.7 192-72L496.7 262.6"
    " 354.5 314c-11.1 4-22.8 6-34.5 6s-23.5-2-34.5-6L143.3 262.6 128 408z"
)
_FA_GRADCAP_VBW, _FA_GRADCAP_VBH = 640, 512


_TOKEN_RE = re.compile(
    r'[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'
)

# Pre-tokenize SVG paths at module load (saves regex work per render)
_PARSED_TOKENS: dict[str, list[str]] = {}
for _d in (_FA_PIN_D, _FA_HEART_D, _FA_HOUSE_D, _FA_GRADCAP_D):
    _PARSED_TOKENS[_d] = _TOKEN_RE.findall(_d)


def _svg_path_to_mpl(d: str, cx: float, cy: float, size: float,
                     vbw: float, vbh: float) -> MplPath:
    """Convert an SVG path 'd' attribute to a matplotlib Path.

    Supports M, L, H, V, C, S, Q, T, A, Z (absolute & relative).
    Y axis is flipped (SVG y-down -> matplotlib y-up).
    """
    tokens = _PARSED_TOKENS.get(d) or _TOKEN_RE.findall(d)

    raw_verts, raw_codes = [], []
    cur_x = cur_y = 0.0
    start_x = start_y = 0.0
    last_ctrl_x = last_ctrl_y = 0.0
    last_cmd = ''
    i = 0

    def nf():
        nonlocal i
        i += 1
        return float(tokens[i])

    while i < len(tokens):
        tok = tokens[i]
        if tok[0] not in 'MmLlHhVvCcSsQqTtAaZz':
            tok = 'L' if last_cmd == 'M' else ('l' if last_cmd == 'm' else last_cmd)
            i -= 1
        cmd = tok
        last_cmd = cmd

        if cmd in ('M', 'm'):
            x, y = nf(), nf()
            if cmd == 'm':
                x += cur_x; y += cur_y
            cur_x, cur_y = x, y
            start_x, start_y = x, y
            raw_verts.append((x, y)); raw_codes.append(MplPath.MOVETO)
            last_ctrl_x, last_ctrl_y = cur_x, cur_y

        elif cmd in ('L', 'l'):
            x, y = nf(), nf()
            if cmd == 'l':
                x += cur_x; y += cur_y
            cur_x, cur_y = x, y
            raw_verts.append((x, y)); raw_codes.append(MplPath.LINETO)
            last_ctrl_x, last_ctrl_y = cur_x, cur_y

        elif cmd in ('H', 'h'):
            x = nf()
            if cmd == 'h':
                x += cur_x
            cur_x = x
            raw_verts.append((cur_x, cur_y)); raw_codes.append(MplPath.LINETO)
            last_ctrl_x, last_ctrl_y = cur_x, cur_y

        elif cmd in ('V', 'v'):
            y = nf()
            if cmd == 'v':
                y += cur_y
            cur_y = y
            raw_verts.append((cur_x, cur_y)); raw_codes.append(MplPath.LINETO)
            last_ctrl_x, last_ctrl_y = cur_x, cur_y

        elif cmd in ('C', 'c'):
            x1, y1 = nf(), nf()
            x2, y2 = nf(), nf()
            x, y = nf(), nf()
            if cmd == 'c':
                x1 += cur_x; y1 += cur_y
                x2 += cur_x; y2 += cur_y
                x += cur_x; y += cur_y
            raw_verts += [(x1, y1), (x2, y2), (x, y)]
            raw_codes += [MplPath.CURVE4] * 3
            last_ctrl_x, last_ctrl_y = x2, y2
            cur_x, cur_y = x, y

        elif cmd in ('S', 's'):
            x1 = 2 * cur_x - last_ctrl_x
            y1 = 2 * cur_y - last_ctrl_y
            x2, y2 = nf(), nf()
            x, y = nf(), nf()
            if cmd == 's':
                x2 += cur_x; y2 += cur_y
                x += cur_x; y += cur_y
            raw_verts += [(x1, y1), (x2, y2), (x, y)]
            raw_codes += [MplPath.CURVE4] * 3
            last_ctrl_x, last_ctrl_y = x2, y2
            cur_x, cur_y = x, y

        elif cmd in ('Q', 'q'):
            qx, qy = nf(), nf()
            x, y = nf(), nf()
            if cmd == 'q':
                qx += cur_x; qy += cur_y
                x += cur_x; y += cur_y
            c1x = cur_x + 2/3 * (qx - cur_x)
            c1y = cur_y + 2/3 * (qy - cur_y)
            c2x = x + 2/3 * (qx - x)
            c2y = y + 2/3 * (qy - y)
            raw_verts += [(c1x, c1y), (c2x, c2y), (x, y)]
            raw_codes += [MplPath.CURVE4] * 3
            last_ctrl_x, last_ctrl_y = qx, qy
            cur_x, cur_y = x, y

        elif cmd in ('A', 'a'):
            rx_a, ry_a = nf(), nf()
            x_rot = nf()
            large = int(nf())
            sweep = int(nf())
            x, y = nf(), nf()
            if cmd == 'a':
                x += cur_x; y += cur_y
            _arc_to_lines(raw_verts, raw_codes,
                          cur_x, cur_y, rx_a, ry_a, x_rot, large, sweep, x, y)
            last_ctrl_x, last_ctrl_y = x, y
            cur_x, cur_y = x, y

        elif cmd in ('Z', 'z'):
            raw_verts.append((start_x, start_y))
            raw_codes.append(MplPath.CLOSEPOLY)
            cur_x, cur_y = start_x, start_y
            last_ctrl_x, last_ctrl_y = cur_x, cur_y

        i += 1

    verts = np.array(raw_verts, dtype=float)
    scale = size / max(vbw, vbh)
    vb_cx, vb_cy = vbw / 2.0, vbh / 2.0
    verts[:, 0] = (verts[:, 0] - vb_cx) * scale + cx
    verts[:, 1] = -(verts[:, 1] - vb_cy) * scale + cy
    return MplPath(verts, raw_codes)


def _arc_to_lines(verts, codes, x1, y1, rx, ry, x_rot_deg,
                  large, sweep, x2, y2, n=24):
    """Approximate an SVG arc with line segments."""
    if (x1 == x2 and y1 == y2) or rx == 0 or ry == 0:
        verts.append((x2, y2)); codes.append(MplPath.LINETO); return
    rx, ry = abs(rx), abs(ry)
    phi = math.radians(x_rot_deg)
    cp, sp = math.cos(phi), math.sin(phi)
    dx2, dy2 = (x1 - x2) / 2, (y1 - y2) / 2
    x1p = cp * dx2 + sp * dy2
    y1p = -sp * dx2 + cp * dy2
    lam = x1p**2 / rx**2 + y1p**2 / ry**2
    if lam > 1:
        s = math.sqrt(lam); rx *= s; ry *= s
    num = max(0, rx**2 * ry**2 - rx**2 * y1p**2 - ry**2 * x1p**2)
    den = rx**2 * y1p**2 + ry**2 * x1p**2
    if den == 0:
        verts.append((x2, y2)); codes.append(MplPath.LINETO); return
    sq = math.sqrt(num / den) * (-1 if large == sweep else 1)
    cxp = sq * rx * y1p / ry
    cyp = -sq * ry * x1p / rx
    cx_a = cp * cxp - sp * cyp + (x1 + x2) / 2
    cy_a = sp * cxp + cp * cyp + (y1 + y2) / 2

    def _angle(ux, uy, vx, vy):
        d = ux * vx + uy * vy
        m = math.sqrt((ux**2 + uy**2) * (vx**2 + vy**2))
        a = math.acos(max(-1, min(1, d / m))) if m else 0
        return -a if ux * vy - uy * vx < 0 else a

    t1 = _angle(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = _angle((x1p - cxp) / rx, (y1p - cyp) / ry,
                (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if sweep == 0 and dt > 0:
        dt -= 2 * math.pi
    elif sweep == 1 and dt < 0:
        dt += 2 * math.pi
    for seg in range(1, n + 1):
        t = t1 + dt * seg / n
        xp, yp = rx * math.cos(t), ry * math.sin(t)
        verts.append((cp * xp - sp * yp + cx_a, sp * xp + cp * yp + cy_a))
        codes.append(MplPath.LINETO)


def _svg_teardrop(cx, cy, size):
    path = _svg_path_to_mpl(_FA_PIN_D, cx, cy, size, _FA_PIN_VBW, _FA_PIN_VBH)
    head_offset = (256 - 192) * (size / _FA_PIN_VBH)
    head_cy = cy + head_offset
    return path, head_cy


def _svg_heart(cx, cy, size):
    return _svg_path_to_mpl(_FA_HEART_D, cx, cy, size, _FA_HEART_VBW, _FA_HEART_VBH)


def _svg_house(cx, cy, size):
    return _svg_path_to_mpl(_FA_HOUSE_D, cx, cy, size, _FA_HOUSE_VBW, _FA_HOUSE_VBH)


def _svg_gradcap(cx, cy, size):
    return _svg_path_to_mpl(_FA_GRADCAP_D, cx, cy, size, _FA_GRADCAP_VBW, _FA_GRADCAP_VBH)


def geocode_address(address: str, near_city: str | None = None) -> tuple[float, float]:
    """Geocode a street address to (lat, lon) using Nominatim with caching.

    If near_city is provided and the address doesn't already contain a comma,
    it is appended to bias geocoding toward the correct city.
    """
    # Build the full query, biased toward the map's city
    query = address
    if near_city and "," not in address:
        query = f"{address}, {near_city}"

    cache_key = f"geocode_{query.lower().replace(' ', '_')[:80]}"
    cached = cache_get(cache_key)
    if cached is not None:
        safe_print(f"[OK] Using cached geocode for '{query}'")
        return cached

    safe_print(f"  Geocoding '{query}'...")
    geolocator = Nominatim(user_agent="mapgen_poster", timeout=10)
    time.sleep(1)

    location = geolocator.geocode(query)
    if location is None:
        raise ValueError(f"Could not geocode address: {query}")

    result = (location.latitude, location.longitude)
    safe_print(f"[OK] Geocoded: {result[0]:.6f}, {result[1]:.6f}")

    try:
        cache_set(cache_key, result)
    except CacheError as e:
        safe_print(str(e))

    return result


def latlon_to_projected(lat: float, lon: float, crs) -> tuple[float, float]:
    """Convert lat/lon (EPSG:4326) to projected coordinates."""
    transformer = pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    x, y = transformer.transform(lon, lat)
    return x, y


def render_pin(ax, lat: float, lon: float, crs, pin_style: int = 1,
               style_colors: dict | None = None,
               pin_color: str | None = None) -> None:
    """Render a pin marker at the given location on the map axes.

    Args:
        pin_style: 1=heart, 2=heart-pin, 3=classic pin, 4=house, 5=graduation cap
        pin_color: Custom hex color (default: #D4736B)
    """
    x, y = latlon_to_projected(lat, lon, crs)

    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    if not (xlim[0] <= x <= xlim[1] and ylim[0] <= y <= ylim[1]):
        safe_print(f"  [!] Pin at ({lat:.4f}, {lon:.4f}) is outside map bounds")
        return

    map_extent = max(xlim[1] - xlim[0], ylim[1] - ylim[0])
    pin_size = map_extent * 0.035
    color = pin_color or "#D4736B"

    if pin_style == 1:
        path = _svg_heart(x, y, pin_size)
        ax.add_patch(PathPatch(
            path, facecolor=color, edgecolor='white',
            linewidth=1.5, zorder=20, clip_on=False,
        ))
        safe_print(f"  Pin (heart): ({lat:.4f}, {lon:.4f})")

    elif pin_style == 2:
        path, head_cy = _svg_teardrop(x, y, pin_size)
        ax.add_patch(PathPatch(
            path, facecolor=color, edgecolor='white',
            linewidth=1.5, zorder=20, clip_on=False,
        ))
        inner = _svg_heart(x, head_cy, pin_size * 0.35)
        ax.add_patch(PathPatch(
            inner, facecolor='white', edgecolor='none',
            zorder=21, clip_on=False,
        ))
        safe_print(f"  Pin (heart-pin): ({lat:.4f}, {lon:.4f})")

    elif pin_style == 3:
        path, head_cy = _svg_teardrop(x, y, pin_size)
        ax.add_patch(PathPatch(
            path, facecolor=color, edgecolor='white',
            linewidth=1.5, zorder=20, clip_on=False,
        ))
        circle_r = pin_size * 0.14
        t = np.linspace(0, 2 * np.pi, 40)
        cx_pts = x + circle_r * np.cos(t)
        cy_pts = head_cy + circle_r * np.sin(t)
        cverts = list(zip(cx_pts, cy_pts))
        cverts.append(cverts[0])
        ccodes = [MplPath.MOVETO] + [MplPath.LINETO] * (len(cverts) - 2) + [MplPath.CLOSEPOLY]
        ax.add_patch(PathPatch(
            MplPath(cverts, ccodes), facecolor='white', edgecolor='none',
            zorder=21, clip_on=False,
        ))
        safe_print(f"  Pin (classic): ({lat:.4f}, {lon:.4f})")

    elif pin_style == 4:
        path = _svg_house(x, y, pin_size)
        ax.add_patch(PathPatch(
            path, facecolor=color, edgecolor='white',
            linewidth=1.5, zorder=20, clip_on=False,
        ))
        safe_print(f"  Pin (house): ({lat:.4f}, {lon:.4f})")

    elif pin_style == 5:
        path = _svg_gradcap(x, y, pin_size)
        ax.add_patch(PathPatch(
            path, facecolor=color, edgecolor='white',
            linewidth=1.5, zorder=20, clip_on=False,
        ))
        safe_print(f"  Pin (grad cap): ({lat:.4f}, {lon:.4f})")

    else:
        safe_print(f"  [!] Unknown pin style: {pin_style}, using heart")
        path = _svg_heart(x, y, pin_size)
        ax.add_patch(PathPatch(
            path, facecolor=color, edgecolor='white',
            linewidth=1.5, zorder=20, clip_on=False,
        ))
