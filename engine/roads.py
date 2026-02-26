"""
MapGen — Road Hierarchy, Colors, and Widths.

Defines the 7-tier road hierarchy with zoom-dependent scaling.
Ported from MapToPoster's create_map_poster.py.
"""

import pandas as pd

from utils.logging import safe_print

# Reference distance for zoom scaling (tuned for close-up city center views)
REFERENCE_DIST = 8000

# Road tiers: (tier_name, set_of_highway_types, zorder)
ROAD_TIERS = [
    ("service",     {"service", "pedestrian", "footway", "cycleway",
                     "path", "track", "steps"}, 1.0),
    ("residential", {"residential", "living_street", "unclassified"}, 1.1),
    ("tertiary",    {"tertiary", "tertiary_link"}, 1.2),
    ("secondary",   {"secondary", "secondary_link"}, 1.3),
    ("primary",     {"primary", "primary_link"}, 1.4),
    ("trunk",       {"trunk", "trunk_link"}, 1.5),
    ("motorway",    {"motorway", "motorway_link"}, 1.6),
]

# Base widths for each road type (tuned for dist ~ 8000m)
ROAD_WIDTHS = {
    "motorway": 1.2, "motorway_link": 1.2,
    "trunk": 1.0, "trunk_link": 1.0,
    "primary": 0.8, "primary_link": 0.8,
    "secondary": 0.55, "secondary_link": 0.55,
    "tertiary": 0.4, "tertiary_link": 0.4,
    "residential": 0.3, "living_street": 0.3, "unclassified": 0.3,
    "service": 0.15, "pedestrian": 0.15,
}


def _build_color_map(theme: dict) -> dict[str, str]:
    """Build a highway-type to color lookup from theme."""
    m: dict[str, str] = {}
    for hw in ("motorway", "motorway_link"):
        m[hw] = theme["road_motorway"]
    for hw in ("trunk", "trunk_link", "primary", "primary_link"):
        m[hw] = theme["road_primary"]
    for hw in ("secondary", "secondary_link"):
        m[hw] = theme["road_secondary"]
    for hw in ("tertiary", "tertiary_link"):
        m[hw] = theme["road_tertiary"]
    for hw in ("residential", "living_street", "unclassified"):
        m[hw] = theme["road_residential"]
    return m


def get_edge_colors_by_type(highway_types: list[str], theme: dict) -> list[str]:
    """Assign colors to roads based on highway type and theme."""
    cmap = _build_color_map(theme)
    default = theme["road_default"]
    return [cmap.get(hw, default) for hw in highway_types]


def get_edge_widths_by_type(highway_types: list[str], zoom_scale: float) -> list[float]:
    """Assign line widths to roads based on highway type with zoom scaling."""
    return [ROAD_WIDTHS.get(hw, 0.15) * zoom_scale for hw in highway_types]


def render_roads(ax, gdf_edges_full, theme: dict, dist: int) -> None:
    """Render roads with hierarchy-based colors and widths.

    Roads are rendered in tier order (minor below major) so intersections
    look clean with major roads on top.
    """
    zoom_scale = min(1.5, max(0.3, REFERENCE_DIST / dist))
    safe_print(f"  Zoom scale: {zoom_scale:.2f} (dist={dist}m)")

    gdf_edges = gdf_edges_full["geometry"]
    hw_raw = gdf_edges_full["highway"] if "highway" in gdf_edges_full.columns else pd.Series("unclassified", index=gdf_edges_full.index)
    edge_highway_types = hw_raw.apply(
        lambda v: v[0] if isinstance(v, list) and v else (v if isinstance(v, str) else "unclassified")
    ).tolist()

    edge_colors = get_edge_colors_by_type(edge_highway_types, theme)
    edge_widths = get_edge_widths_by_type(edge_highway_types, zoom_scale)

    hw_series = pd.Series(edge_highway_types, index=gdf_edges.index)
    color_series = pd.Series(edge_colors, index=gdf_edges.index)
    width_series = pd.Series(edge_widths, index=gdf_edges.index, dtype=float)

    for tier_name, tier_types, tier_zorder in ROAD_TIERS:
        mask = hw_series.isin(tier_types)
        if not mask.any():
            continue
        tier_geoms = gdf_edges[mask]
        tier_colors_list = color_series[mask].tolist()
        tier_widths_list = width_series[mask].tolist()
        if tier_geoms.empty:
            continue
        tier_geoms.plot(
            ax=ax, color=tier_colors_list, linewidth=tier_widths_list,
            zorder=tier_zorder,
        )

    # Catch-all for road types not in any tier
    all_tier_types = set()
    for _, types, _ in ROAD_TIERS:
        all_tier_types.update(types)
    leftover_mask = ~hw_series.isin(all_tier_types)
    if leftover_mask.any():
        leftover_geoms = gdf_edges[leftover_mask]
        leftover_colors = color_series[leftover_mask].tolist()
        leftover_widths = width_series[leftover_mask].tolist()
        leftover_geoms.plot(
            ax=ax, color=leftover_colors, linewidth=leftover_widths,
            zorder=1.0,
        )

    safe_print(f"  Roads: {len(edge_highway_types)} segments rendered")
