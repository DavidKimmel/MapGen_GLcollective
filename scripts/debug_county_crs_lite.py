#!/usr/bin/env python3
"""
Lightweight CRS diagnostic — no OSM fetch needed.
Just checks county polygon reprojection to UTM vs what the axes would be.
"""

import os
import sys
import math

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

import pyproj
from shapely.geometry import Point
from shapely.ops import transform as shapely_transform

from engine.county_mask import get_county_bounds, county_polygon_in_crs

county_name = "Arlington"
state = "VA"

# 1. County center and bbox in EPSG:4269
center_lat, center_lon, bbox = get_county_bounds(county_name, state)
print(f"County: {county_name}, {state}")
print(f"Center (lat/lon): {center_lat:.6f}, {center_lon:.6f}")

# 2. Distance calculation (same as generate_county.py)
min_lon, min_lat, max_lon, max_lat = bbox
m_per_deg_lat = 111_320.0
m_per_deg_lon = 111_320.0 * math.cos(math.radians(center_lat))
width_m = (max_lon - min_lon) * m_per_deg_lon
height_m = (max_lat - min_lat) * m_per_deg_lat
distance = int(max(width_m, height_m) / 2.0 * 1.15)
print(f"Distance: {distance}m")

# 3. Determine UTM zone for this location (what OSMnx would use)
utm_zone = int((center_lon + 180) / 6) + 1
hemisphere = "north" if center_lat >= 0 else "south"
utm_crs = f"EPSG:{32600 + utm_zone}" if hemisphere == "north" else f"EPSG:{32700 + utm_zone}"
print(f"\nExpected UTM CRS: {utm_crs} (zone {utm_zone}{hemisphere[0].upper()})")

# 4. Project center to UTM (simulating what get_crop_limits does)
transformer_4326_to_utm = pyproj.Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True)
cx, cy = transformer_4326_to_utm.transform(center_lon, center_lat)
print(f"Center in UTM: ({cx:.1f}, {cy:.1f})")

# Axes limits for 16x20 poster
aspect = 16.0 / 16.0  # approximate map area
half_x = distance
half_y = distance / aspect
xlim = (cx - half_x, cx + half_x)
ylim = (cy - half_y, cy + half_y)
print(f"\nAxes bounds (UTM):")
print(f"  xlim: {xlim[0]:.1f} to {xlim[1]:.1f}")
print(f"  ylim: {ylim[0]:.1f} to {ylim[1]:.1f}")

# 5. County polygon reprojected to UTM
county_utm = county_polygon_in_crs(county_name, state, utm_crs)
cb = county_utm.bounds
print(f"\nCounty polygon bounds (UTM):")
print(f"  x: {cb[0]:.1f} to {cb[2]:.1f}")
print(f"  y: {cb[1]:.1f} to {cb[3]:.1f}")

# 6. Also try EPSG:3857 (Web Mercator) — what if OSMnx uses this?
county_3857 = county_polygon_in_crs(county_name, state, "EPSG:3857")
cb3 = county_3857.bounds
print(f"\nCounty polygon bounds (EPSG:3857):")
print(f"  x: {cb3[0]:.1f} to {cb3[2]:.1f}")
print(f"  y: {cb3[1]:.1f} to {cb3[3]:.1f}")

# 7. Check overlap
x_overlap = (cb[0] < xlim[1]) and (cb[2] > xlim[0])
y_overlap = (cb[1] < ylim[1]) and (cb[3] > ylim[0])
print(f"\nAlignment check (UTM):")
print(f"  Overlaps: {x_overlap and y_overlap}")

# Check if 3857 polygon accidentally overlaps UTM axes (would indicate CRS mismatch)
x_overlap_3857 = (cb3[0] < xlim[1]) and (cb3[2] > xlim[0])
y_overlap_3857 = (cb3[1] < ylim[1]) and (cb3[3] > ylim[0])
print(f"\nCross-CRS check (3857 polygon vs UTM axes):")
print(f"  Overlaps: {x_overlap_3857 and y_overlap_3857}  (should be False)")

# 8. Summary
print(f"\n{'='*60}")
if x_overlap and y_overlap:
    county_cx = (cb[0] + cb[2]) / 2
    county_cy = (cb[1] + cb[3]) / 2
    print(f"ALIGNED — county polygon is within axes bounds")
    print(f"  Offset from center: ({county_cx - cx:.1f}, {county_cy - cy:.1f})")
    print(f"\n  => CRS is NOT the bug. Problem is elsewhere (zoom/linewidth/save).")
else:
    print(f"MISALIGNED — county polygon does NOT overlap axes bounds")
    print(f"  => CRS mismatch confirmed. Fix the reprojection.")
