"""
MapGen — Crop Mask System.

Applies circle, house, or heart-shaped clip masks to the map area.
Uses an "inverted fill" approach: draw a rectangle covering the axes,
cut a hole in the desired shape, fill outside with bg_color.

Ported from GeoLineCollective's crop_masks.py.
"""

import numpy as np
from matplotlib.patches import Circle, PathPatch
from matplotlib.path import Path as MplPath

from utils.logging import safe_print


def apply_circle_crop(ax, fig, bg_color="#FFFFFF"):
    """Apply a circular crop mask to the map area."""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    cx = (xlim[0] + xlim[1]) / 2
    cy = (ylim[0] + ylim[1]) / 2
    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]

    pos = ax.get_position()
    ax_width = pos.width * fig.get_figwidth()
    ax_height = pos.height * fig.get_figheight()

    if ax_width <= ax_height:
        radius_data = x_range / 2
    else:
        radius_data = y_range / 2
    radius_data *= 0.98

    theta = np.linspace(0, 2 * np.pi, 300)
    circle_x = cx + radius_data * np.cos(theta)
    circle_y = cy + radius_data * np.sin(theta)

    pad = max(x_range, y_range) * 0.15
    rect_verts = [
        (xlim[0] - pad, ylim[0] - pad),
        (xlim[1] + pad, ylim[0] - pad),
        (xlim[1] + pad, ylim[1] + pad),
        (xlim[0] - pad, ylim[1] + pad),
        (xlim[0] - pad, ylim[0] - pad),
    ]

    circle_verts = list(zip(circle_x[::-1], circle_y[::-1]))
    circle_verts.append(circle_verts[0])

    all_verts = rect_verts + circle_verts
    all_codes = (
        [MplPath.MOVETO] + [MplPath.LINETO] * 3 + [MplPath.CLOSEPOLY]
        + [MplPath.MOVETO] + [MplPath.LINETO] * (len(circle_verts) - 2)
        + [MplPath.CLOSEPOLY]
    )

    mask_path = MplPath(all_verts, all_codes)
    mask_patch = PathPatch(
        mask_path, facecolor=bg_color, edgecolor='none',
        zorder=14, antialiased=True,
    )
    ax.add_patch(mask_patch)

    border_circle = Circle(
        (cx, cy), radius_data,
        transform=ax.transData,
        facecolor='none',
        edgecolor=_border_color(bg_color),
        linewidth=1.5,
        zorder=15,
    )
    ax.add_patch(border_circle)
    safe_print("  Circle crop applied")


def apply_house_crop(ax, fig, bg_color="#FFFFFF"):
    """Apply a house-shaped crop mask with chimney and floating hearts."""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]

    inset_x = x_range * 0.10
    inset_y = y_range * 0.04

    left = xlim[0] + inset_x
    right = xlim[1] - inset_x
    bottom = ylim[0] + inset_y
    top = ylim[1] - inset_y

    inner_x = right - left
    inner_y = top - bottom

    wall_top = bottom + inner_y * 0.55
    roof_peak_y = top
    center_x = (left + right) / 2

    overhang = inner_x * 0.12
    roof_left = left - overhang
    roof_right = right + overhang

    chimney_center_x = center_x + inner_x * 0.25
    chimney_width = inner_x * 0.09
    chimney_left = chimney_center_x - chimney_width / 2
    chimney_right = chimney_center_x + chimney_width / 2

    t_left = (chimney_left - center_x) / (roof_right - center_x)
    t_right = (chimney_right - center_x) / (roof_right - center_x)
    roof_y_at_chim_left = roof_peak_y + t_left * (wall_top - roof_peak_y)
    roof_y_at_chim_right = roof_peak_y + t_right * (wall_top - roof_peak_y)
    chimney_top = roof_y_at_chim_left + inner_y * 0.04

    house_verts = [
        (left, bottom),
        (right, bottom),
        (right, wall_top),
        (roof_right, wall_top),
        (chimney_right, roof_y_at_chim_right),
        (chimney_right, chimney_top),
        (chimney_left, chimney_top),
        (chimney_left, roof_y_at_chim_left),
        (center_x, roof_peak_y),
        (roof_left, wall_top),
        (left, wall_top),
        (left, bottom),
    ]
    house_codes = [
        MplPath.MOVETO,
        MplPath.LINETO, MplPath.LINETO, MplPath.LINETO,
        MplPath.LINETO, MplPath.LINETO, MplPath.LINETO,
        MplPath.LINETO, MplPath.LINETO, MplPath.LINETO,
        MplPath.LINETO,
        MplPath.CLOSEPOLY,
    ]
    house_path = MplPath(house_verts, house_codes)

    pad = max(x_range, y_range) * 0.15
    rect_verts = [
        (xlim[0] - pad, ylim[0] - pad),
        (xlim[1] + pad, ylim[0] - pad),
        (xlim[1] + pad, ylim[1] + pad),
        (xlim[0] - pad, ylim[1] + pad),
        (xlim[0] - pad, ylim[0] - pad),
    ]

    house_hole = list(reversed(house_verts[:-1]))
    house_hole.append(house_hole[0])

    all_verts = rect_verts + house_hole
    all_codes = (
        [MplPath.MOVETO] + [MplPath.LINETO] * 3 + [MplPath.CLOSEPOLY]
        + [MplPath.MOVETO] + [MplPath.LINETO] * (len(house_hole) - 2)
        + [MplPath.CLOSEPOLY]
    )

    mask_path = MplPath(all_verts, all_codes)
    mask_patch = PathPatch(
        mask_path, facecolor=bg_color, edgecolor='none',
        zorder=14, antialiased=True,
    )
    ax.add_patch(mask_patch)

    border_patch = PathPatch(
        house_path,
        transform=ax.transData,
        facecolor='none',
        edgecolor=_border_color(bg_color),
        linewidth=2.5,
        zorder=15,
        joinstyle='miter',
        capstyle='projecting',
    )
    ax.add_patch(border_patch)

    _draw_chimney_hearts(ax, fig, chimney_center_x, chimney_top, inner_x, inner_y,
                         stroke_color=_border_color(bg_color))
    safe_print("  House crop applied (with chimney + hearts)")


def _draw_chimney_hearts(ax, fig, chimney_cx, chimney_top, house_w, house_h,
                         stroke_color="#000000"):
    """Draw small decorative hearts floating above the chimney."""
    inv = ax.transData + fig.transFigure.inverted()
    fig_x, fig_y = inv.transform((chimney_cx, chimney_top))

    hearts = [
        (0.004,  0.028, 0.018, 1.0,  10),
        (0.022,  0.058, 0.013, 1.0,  -8),
        (0.012,  0.082, 0.009, 1.0,  15),
    ]

    for dx, dy, size, alpha, rot in hearts:
        hx = fig_x + dx
        hy = fig_y + dy
        _draw_heart_glyph(fig, hx, hy, size, alpha, rot, stroke_color=stroke_color)


def _draw_heart_glyph(fig, cx, cy, size, alpha, rotation=0, stroke_color="#000000"):
    """Draw a single small heart glyph in figure coordinates."""
    t = np.linspace(0, 2 * np.pi, 80)
    hx = 16 * np.sin(t) ** 3
    hy = 13 * np.cos(t) - 5 * np.cos(2*t) - 2 * np.cos(3*t) - np.cos(4*t)
    hx = hx / 16.0
    hy = hy / 17.0
    hx = cx + hx * size
    hy = cy + hy * size

    if rotation != 0:
        angle = np.radians(rotation)
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        rx = cx + (hx - cx) * cos_a - (hy - cy) * sin_a
        ry = cy + (hx - cx) * sin_a + (hy - cy) * cos_a
        hx, hy = rx, ry

    verts = list(zip(hx, hy))
    verts.append(verts[0])
    codes = ([MplPath.MOVETO] + [MplPath.LINETO] * (len(verts) - 2)
             + [MplPath.CLOSEPOLY])
    heart_path = MplPath(verts, codes)

    patch = PathPatch(
        heart_path,
        transform=fig.transFigure,
        facecolor='none',
        edgecolor=stroke_color,
        linewidth=2.5,
        alpha=alpha,
        zorder=16,
    )
    fig.patches.append(patch)


def _sample_bezier_path(verts, codes, n_per_seg=60):
    """Sample a path with cubic bezier segments into a dense polyline."""
    points = []
    i = 0
    c = 0
    current = None

    while c < len(codes):
        code = codes[c]
        if code == MplPath.MOVETO:
            current = verts[i]
            points.append(current)
            i += 1
            c += 1
        elif code == MplPath.CURVE4:
            cp1 = verts[i]
            cp2 = verts[i + 1]
            end = verts[i + 2]
            i += 3
            c += 3
            p0 = np.array(current)
            p1 = np.array(cp1)
            p2 = np.array(cp2)
            p3 = np.array(end)
            t_vals = np.linspace(0, 1, n_per_seg + 1)[1:]
            for t in t_vals:
                u = 1 - t
                pt = u**3 * p0 + 3 * u**2 * t * p1 + 3 * u * t**2 * p2 + t**3 * p3
                points.append(tuple(pt))
            current = end
        elif code == MplPath.CLOSEPOLY:
            break
        else:
            i += 1
            c += 1

    return np.array(points)


def _heart_svg_verts(cx, cy, sx, sy):
    """Generate heart vertices from SVG path data (noun-heart-8061390.svg)."""
    segs = [
        (( 0.4580, 0.8506), ( 0.2722, 0.8507), ( 0.0993, 0.7556), ( 0.0000, 0.5985)),
        (( 0.0000, 0.5985), (-0.0843, 0.7317), (-0.2225, 0.8216), (-0.3784, 0.8447)),
        ((-0.3784, 0.8447), (-0.5343, 0.8679), (-0.6926, 0.8220), (-0.8120, 0.7190)),
        ((-0.8120, 0.7190), (-0.9313, 0.6160), (-1.0000, 0.4662), (-1.0000, 0.3086)),
        ((-1.0000, 0.3086), (-1.0000,-0.2350), (-0.1950,-0.6855), ( 0.0000,-0.8506)),
        (( 0.0000,-0.8506), ( 0.1950,-0.6855), ( 1.0000,-0.2350), ( 1.0000, 0.3086)),
        (( 1.0000, 0.3086), ( 1.0000, 0.4523), ( 0.9429, 0.5902), ( 0.8412, 0.6918)),
        (( 0.8412, 0.6918), ( 0.7396, 0.7935), ( 0.6017, 0.8506), ( 0.4580, 0.8506)),
    ]

    verts_norm = [segs[0][0]]
    for _start, cp1, cp2, end in segs:
        verts_norm.extend([cp1, cp2, end])

    verts = [(cx + x * sx, cy + y * sy) for x, y in verts_norm]

    codes = [MplPath.MOVETO]
    for _ in range(8):
        codes += [MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4]
    codes[-1] = MplPath.CLOSEPOLY

    return verts, codes


def apply_heart_crop(ax, fig, bg_color="#FFFFFF", heart_scale=1.0):
    """Apply a heart-shaped crop mask to the map area.

    Args:
        heart_scale: Multiplier for heart size (1.0 = default, 1.15 = date_night).
    """
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    cx = (xlim[0] + xlim[1]) / 2
    cy = (ylim[0] + ylim[1]) / 2
    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]

    sx = x_range * 0.50 * heart_scale
    sy = y_range * 0.54 * heart_scale
    center_y = cy + y_range * 0.02

    heart_verts, heart_codes = _heart_svg_verts(cx, center_y, sx, sy)
    heart_path = MplPath(heart_verts, heart_codes)

    pad = max(x_range, y_range) * 0.15
    rect_verts = [
        (xlim[0] - pad, ylim[0] - pad),
        (xlim[1] + pad, ylim[0] - pad),
        (xlim[1] + pad, ylim[1] + pad),
        (xlim[0] - pad, ylim[1] + pad),
        (xlim[0] - pad, ylim[0] - pad),
    ]
    rect_codes = [MplPath.MOVETO] + [MplPath.LINETO] * 3 + [MplPath.CLOSEPOLY]

    hole_pts = _sample_bezier_path(heart_verts, heart_codes, n_per_seg=60)
    hole_pts_rev = hole_pts[::-1]
    hole_verts_list = list(map(tuple, hole_pts_rev))
    hole_verts_list.append(hole_verts_list[0])
    hole_codes = ([MplPath.MOVETO]
                  + [MplPath.LINETO] * (len(hole_verts_list) - 2)
                  + [MplPath.CLOSEPOLY])

    all_verts = rect_verts + hole_verts_list
    all_codes = rect_codes + hole_codes

    mask_path = MplPath(all_verts, all_codes)
    mask_patch = PathPatch(
        mask_path, facecolor=bg_color, edgecolor='none',
        zorder=14, antialiased=True,
    )
    ax.add_patch(mask_patch)

    border_sampled = _sample_bezier_path(heart_verts, heart_codes, n_per_seg=60)
    border_pts = list(map(tuple, border_sampled))
    border_pts.append(border_pts[0])
    border_codes_b = ([MplPath.MOVETO]
                      + [MplPath.LINETO] * (len(border_pts) - 2)
                      + [MplPath.CLOSEPOLY])
    border_path = MplPath(border_pts, border_codes_b)
    border_patch = PathPatch(
        border_path,
        transform=ax.transData,
        facecolor='none',
        edgecolor=_border_color(bg_color),
        linewidth=1.5,
        zorder=15,
    )
    ax.add_patch(border_patch)
    safe_print("  Heart crop applied")


def _border_color(bg_color: str) -> str:
    """Return a suitable border color based on background luminance."""
    r = int(bg_color[1:3], 16)
    g = int(bg_color[3:5], 16)
    b = int(bg_color[5:7], 16)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b

    if luminance > 180:
        return "#2C2C2C"
    elif luminance > 80:
        factor = 0.6
        return f"#{max(0,int(r*factor)):02x}{max(0,int(g*factor)):02x}{max(0,int(b*factor)):02x}"
    else:
        factor = 1.4
        return f"#{min(255,int(r*factor)):02x}{min(255,int(g*factor)):02x}{min(255,int(b*factor)):02x}"
