#!/usr/bin/env python3
"""Check winding direction of county polygon exterior ring."""

import os, sys
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from shapely.geometry import LinearRing, MultiPolygon
from engine.county_mask import lookup_county

for county, state in [("Fairfax", "VA"), ("Arlington", "VA")]:
    geom = lookup_county(county, state)
    if isinstance(geom, MultiPolygon):
        print(f"{county}, {state}: MultiPolygon with {len(geom.geoms)} parts")
        geom = geom.geoms[0]
    ring = LinearRing(geom.exterior.coords)
    print(f"{county}, {state}: is_ccw={ring.is_ccw}")
    coords = list(geom.exterior.coords)
    reversed_ring = LinearRing(coords[::-1])
    print(f"  Reversed: is_ccw={reversed_ring.is_ccw}")
    print(f"  Rectangle winding (BL->BR->TR->TL): is_ccw={LinearRing([(0,0),(1,0),(1,1),(0,1)]).is_ccw}")
