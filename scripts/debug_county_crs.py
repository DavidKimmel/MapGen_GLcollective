#!/usr/bin/env python3
"""
Quick CRS diagnostic for CountyMap — no rendering, just coordinate comparison.
Checks if the county polygon aligns with the matplotlib axes bounds.
"""

import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

import math
import osmnx as ox
from shapely.geometry import Point

from engine.county_mask import get_county_bounds, county_polygon_in_crs, lookup_county


def main():
    county_name = "Arlington"
    state = "VA"

    # 1. Get county center and bbox
    center_lat, center_lon, bbox = get_county_bounds(county_name, state)
    print(f"County: {county_name}, {state}")
    print(f"Center (lat/lon): {center_lat:.4f}, {center_lon:.4f}")
    print(f"Bbox (EPSG:4269): minlon={bbox[0]:.4f}, minlat={bbox[1]:.4f}, maxlon={bbox[2]:.4f}, maxlat={bbox[3]:.4f}")

    # 2. Calculate distance (same as generate_county.py)
    min_lon, min_lat, max_lon, max_lat = bbox
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(center_lat))
    width_m = (max_lon - min_lon) * m_per_deg_lon
    height_m = (max_lat - min_lat) * m_per_deg_lat
    half_extent = max(width_m, height_m) / 2.0
    distance = int(half_extent * 1.15)
    print(f"\nCalculated distance: {distance}m")

    # 3. Fetch a tiny graph just to get the CRS (use cached if available)
    print(f"\nFetching graph to determine CRS...")
    g = ox.graph_from_point((center_lat, center_lon), dist=distance, network_type="drive")
    g_proj = ox.project_graph(g)
    target_crs = g_proj.graph['crs']
    print(f"Target CRS: {target_crs}")

    # 4. Compute axes limits (same as get_crop_limits in map_engine.py)
    center_proj = ox.projection.project_geometry(
        Point(center_lon, center_lat), crs="EPSG:4326", to_crs=target_crs
    )[0]
    cx, cy = center_proj.x, center_proj.y

    # 16x20 aspect ratio (most common size)
    axes_w = 16.0
    axes_h = 16.0  # approximate map area height (text zone takes some)
    aspect = axes_w / axes_h
    if aspect >= 1:
        half_x = distance
        half_y = distance / aspect
    else:
        half_y = distance
        half_x = distance * aspect

    xlim = (cx - half_x, cx + half_x)
    ylim = (cy - half_y, cy + half_y)
    print(f"\nAxes limits (target CRS):")
    print(f"  xlim: {xlim[0]:.1f} to {xlim[1]:.1f}  (range: {xlim[1]-xlim[0]:.1f})")
    print(f"  ylim: {ylim[0]:.1f} to {ylim[1]:.1f}  (range: {ylim[1]-ylim[0]:.1f})")

    # 5. Reproject county polygon to same CRS
    county_proj = county_polygon_in_crs(county_name, state, target_crs)
    cb = county_proj.bounds  # (minx, miny, maxx, maxy)
    print(f"\nCounty polygon bounds (target CRS):")
    print(f"  x: {cb[0]:.1f} to {cb[2]:.1f}  (range: {cb[2]-cb[0]:.1f})")
    print(f"  y: {cb[1]:.1f} to {cb[3]:.1f}  (range: {cb[3]-cb[1]:.1f})")

    # 6. Check overlap
    x_overlap = (cb[0] < xlim[1]) and (cb[2] > xlim[0])
    y_overlap = (cb[1] < ylim[1]) and (cb[3] > ylim[0])
    print(f"\nOverlap check:")
    print(f"  X overlaps: {x_overlap}")
    print(f"  Y overlaps: {y_overlap}")
    print(f"  Aligned: {x_overlap and y_overlap}")

    if x_overlap and y_overlap:
        # Check how well centered the county is
        county_cx = (cb[0] + cb[2]) / 2
        county_cy = (cb[1] + cb[3]) / 2
        print(f"\n  Axes center:  ({cx:.1f}, {cy:.1f})")
        print(f"  County center: ({county_cx:.1f}, {county_cy:.1f})")
        print(f"  Offset: ({county_cx - cx:.1f}, {county_cy - cy:.1f})")
    else:
        print(f"\n  *** MISALIGNED — county polygon is NOT within axes bounds ***")
        print(f"  Axes center:  ({cx:.1f}, {cy:.1f})")
        county_cx = (cb[0] + cb[2]) / 2
        county_cy = (cb[1] + cb[3]) / 2
        print(f"  County center: ({county_cx:.1f}, {county_cy:.1f})")
        print(f"  Offset: ({county_cx - cx:.1f}, {county_cy - cy:.1f})")


if __name__ == "__main__":
    main()
