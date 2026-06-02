"""Render all missing assets for CustomMapPack listings.

Renders Chicago at 24x36 and 18x24 for all themes/colors needed for mockups.
Also renders Paris as alternate city for variety in listing images.
"""

import gc
import os
import sys
import subprocess
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

PYTHON = sys.executable
OUT_DIR = os.path.join("etsy", "renders", "CustomMapPack")

# Amsterdam — dense canal grid, fills frame well
AMS_LAT, AMS_LON = 52.3731, 4.8925
AMS_NAME, AMS_STATE = "Amsterdam", "Netherlands"

# Washington DC — radial grid, no water edge issues
DC_LAT, DC_LON = 38.8950, -77.0365
DC_NAME, DC_STATE = "Washington DC", "United States"

# MonoMap colors (flat single color)
MONO_COLORS = {
    "charcoal": "#4A4A4A",
    "navy": "#1C3D6E",
    "forest": "#2A5A2A",
    "terracotta": "#B5553A",
    "dusty_rose": "#A35580",
    "black": "#1A1A1A",
}

# Blueprint shaded palettes
BLUEPRINT_PALETTES = {
    "navy": ["#0A1628", "#132744", "#1C3D6E", "#2B5EA2", "#3A7BD5", "#5B9BD5", "#8BB8E8", "#B5D4F0"],
    "forest": ["#0B1F0B", "#1A3A1A", "#2A5A2A", "#3B7A3B", "#4E944E", "#6BAF6B", "#8FCA8F", "#B5DEB5"],
    "terracotta": ["#4A1A0A", "#6B2E14", "#8C4422", "#A85A35", "#C4734D", "#D4906B", "#E4AD8E", "#F0CAB5"],
    "charcoal": ["#1A1A1A", "#2D2D2D", "#404040", "#555555", "#6E6E6E", "#8A8A8A", "#A3A3A3", "#BFBFBF"],
}

SIZES_NEEDED = ["18x24", "24x36"]
DPI = 300


def render_florence(slug, lat, lon, distance, size, out_path, city_name="Amsterdam", state_name="Netherlands"):
    """Render Florence style."""
    out_path = out_path.replace("\\", "/")
    script = f"""
import sys, os, gc
sys.path.insert(0, os.getcwd())
from engine.florence_renderer import render_florence_poster
from engine.renderer import load_theme
theme = load_theme("florence")
render_florence_poster(
    location="{lat},{lon}",
    theme_data=theme,
    size="{size}",
    dpi={DPI},
    output_path="{out_path}",
    distance={distance},
    city_name="{city_name}",
    state_name="{state_name}",
)
gc.collect()
"""
    subprocess.run([PYTHON, "-c", script], cwd=os.getcwd(), timeout=1800)


def render_classic(slug, lat, lon, distance, size, out_path):
    """Render 37th_parallel (classic/default) style."""
    out_path = out_path.replace("\\", "/")
    script = f"""
import sys, os, gc
sys.path.insert(0, os.getcwd())
from engine.renderer import render_poster
render_poster(
    location="{lat},{lon}",
    theme="37th_parallel",
    size="{size}",
    distance={distance},
    output_path="{out_path}",
)
gc.collect()
"""
    subprocess.run([PYTHON, "-c", script], cwd=os.getcwd(), timeout=1800)


def render_mono(slug, lat, lon, distance, size, color_hex, color_name, out_path, city_name="Amsterdam", state_name="Netherlands"):
    """Render flat monochrome style."""
    out_path = out_path.replace("\\", "/")
    theme = json.dumps({
        "palette": [color_hex],
        "bg_color": "#FFFFFF",
        "water_color": "#FFFFFF",
        "street_color": "#FFFFFF",
        "poster_bg": "#FFFFFF",
        "text_color": color_hex,
        "font": "Switzer-Bold.ttf",
    })
    script = f"""
import sys, os, gc
sys.path.insert(0, os.getcwd())
from engine.florence_renderer import render_florence_poster
import json
theme = json.loads('''{theme}''')
render_florence_poster(
    location="{lat},{lon}",
    theme_data=theme,
    size="{size}",
    dpi={DPI},
    output_path="{out_path}",
    distance={distance},
    city_name="{city_name}",
    state_name="{state_name}",
)
gc.collect()
"""
    subprocess.run([PYTHON, "-c", script], cwd=os.getcwd(), timeout=1800)


def render_blueprint(slug, lat, lon, distance, size, palette, color_name, out_path, city_name="Amsterdam", state_name="Netherlands"):
    """Render Blueprint (shaded gradient) style with detailed road overlay."""
    out_path = out_path.replace("\\", "/")
    pal_json = json.dumps(palette)
    text_color = palette[0]
    script = f"""
import sys, os, gc, random, json
sys.path.insert(0, os.getcwd())

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import osmnx as ox
from shapely.geometry import Point, box, LineString
from shapely.ops import polygonize, unary_union

from engine.florence_renderer import DROP_HIGHWAY, WATER_TAGS, _road_weight
from engine.florence_text_layout import compose_florence_poster as compose
from export.output_sizes import get_size_config

random.seed(42)
palette = json.loads('''{pal_json}''')
lat, lon = {lat}, {lon}
distance = {distance}
size = "{size}"
dpi = {DPI}

sc = get_size_config(size)
fw, fh = sc["width_in"], sc["height_in"]
aspect = fh / fw
rx, ry = distance, int(distance * aspect)
cp = Point(lon, lat)
cg = gpd.GeoDataFrame(geometry=[cp], crs="EPSG:4326")
utm = cg.estimate_utm_crs()
center = cg.to_crs(utm).geometry[0]
aoi = box(center.x - rx, center.y - ry, center.x + rx, center.y + ry)
fr = int(max(rx, ry) * 1.25)

G = ox.graph_from_point((lat, lon), dist=fr, network_type="all")
all_e = ox.graph_to_gdfs(G, nodes=False).to_crs(utm)
all_e = gpd.clip(all_e, aoi)
edges = all_e.copy()
if "highway" in edges.columns:
    edges = edges[~edges["highway"].apply(lambda h: str(h).lower() in DROP_HIGHWAY if h else False)].copy()
all_e["lw"] = all_e.apply(_road_weight, axis=1)
if "highway" in all_e.columns:
    mask = all_e["highway"].apply(lambda h: str(h).lower() in DROP_HIGHWAY if h else False)
    all_e.loc[mask, "lw"] = 0.15

boundary = LineString(aoi.exterior.coords)
lines = unary_union(list(edges.geometry) + [boundary])
polys = list(polygonize(lines))
blocks = gpd.GeoDataFrame(geometry=polys, crs=utm)
blocks = gpd.clip(blocks, aoi)
blocks = blocks[blocks.geometry.area >= 500].copy()
blocks["color"] = [random.choice(palette) for _ in range(len(blocks))]

try:
    water = ox.features_from_point((lat, lon), WATER_TAGS, dist=fr)
    water = water[water.geometry.type.isin(["Polygon","MultiPolygon"])].to_crs(utm)
    water = gpd.clip(water, aoi)
    has_w = len(water) > 0
except: has_w = False

try:
    from engine.ocean import build_ocean_polygons
    ocean = build_ocean_polygons((lat,lon), max(rx,ry), utm, (center.x-rx,center.x+rx), (center.y-ry,center.y+ry))
except: ocean = []

fig, ax = plt.subplots(1, 1, figsize=(fw, fh))
fig.patch.set_facecolor("#FFFFFF")
ax.set_facecolor("#FFFFFF")
ax.set_aspect("equal"); ax.axis("off")
base = gpd.GeoDataFrame(geometry=[aoi], crs=utm)
base.plot(ax=ax, color=random.choice(palette), edgecolor="none", zorder=0)
if ocean:
    gpd.GeoDataFrame(geometry=ocean, crs=utm).plot(ax=ax, color="#FFFFFF", edgecolor="none", zorder=0.5)
blocks.plot(ax=ax, color=blocks["color"], edgecolor="none", zorder=1)
if has_w:
    water.plot(ax=ax, color="#FFFFFF", edgecolor="none", zorder=3)
for lw, grp in all_e.groupby("lw"):
    grp.plot(ax=ax, color="#FFFFFF", linewidth=lw, alpha=1.0, zorder=4)
ax.set_xlim(center.x-rx, center.x+rx)
ax.set_ylim(center.y-ry, center.y+ry)

tmp = "{out_path}.tmp_map.png"
fig.savefig(tmp, dpi=dpi, bbox_inches="tight", pad_inches=0, facecolor="#FFFFFF")
plt.close(fig); gc.collect()

compose(
    map_image_path=tmp, city_name="{city_name}", state_or_region="{state_name}",
    lat=lat, lon=lon, palette=palette, size_name=size, dpi=dpi,
    bg_color="#FFFFFF", text_color="{text_color}",
    font_path=os.path.join("fonts", "Switzer-Bold.ttf"),
    output_path="{out_path}",
)
os.remove(tmp)
gc.collect()
"""
    subprocess.run([PYTHON, "-c", script], cwd=os.getcwd(), timeout=600,
                   env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # Use Amsterdam for Florence/MonoMap/Blueprint, DC for Classic
    # Amsterdam: 5000m for Florence, 5000m for Mono, 3500m for Blueprint
    # DC: 5500m for Classic

    # === Florence (Amsterdam) ===
    print("\n=== Florence ===")
    for size in SIZES_NEEDED:
        out = os.path.join(OUT_DIR, "florence_digital", f"amsterdam_{size}.png")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if not os.path.exists(out):
            print(f"  Florence Amsterdam {size}...")
            render_florence("amsterdam", AMS_LAT, AMS_LON, 5000, size, out,
                           city_name=AMS_NAME, state_name=AMS_STATE)
        else:
            print(f"  Florence Amsterdam {size} — exists")

    # === Classic (Washington DC) ===
    print("\n=== Classic (37th_parallel) ===")
    for size in SIZES_NEEDED:
        out = os.path.join(OUT_DIR, "classic_digital", f"washington_dc_{size}.png")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if not os.path.exists(out):
            print(f"  Classic DC {size}...")
            render_classic("washington_dc", DC_LAT, DC_LON, 5500, size, out)
        else:
            print(f"  Classic DC {size} — exists")

    # === MonoMap — Amsterdam, one hero color (navy) + one alt (terracotta) ===
    print("\n=== MonoMap ===")
    for color_name in ["navy", "terracotta"]:
        hex_val = MONO_COLORS[color_name]
        for size in SIZES_NEEDED:
            out = os.path.join(OUT_DIR, "monomap_digital", f"amsterdam_{color_name}_{size}.png")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            if not os.path.exists(out):
                print(f"  MonoMap Amsterdam {color_name} {size}...")
                render_mono("amsterdam", AMS_LAT, AMS_LON, 5000, size, hex_val, color_name, out,
                           city_name=AMS_NAME, state_name=AMS_STATE)
            else:
                print(f"  MonoMap Amsterdam {color_name} {size} — exists")

    # === Blueprint — Amsterdam, one hero color (navy) + one alt (terracotta) ===
    print("\n=== Blueprint ===")
    for color_name in ["navy", "terracotta"]:
        palette = BLUEPRINT_PALETTES[color_name]
        for size in SIZES_NEEDED:
            out = os.path.join(OUT_DIR, "blueprint_digital", f"amsterdam_{color_name}_{size}.png")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            if not os.path.exists(out):
                print(f"  Blueprint Amsterdam {color_name} {size}...")
                render_blueprint("amsterdam", AMS_LAT, AMS_LON, 3500, size, palette, color_name, out,
                                city_name=AMS_NAME, state_name=AMS_STATE)
            else:
                print(f"  Blueprint Amsterdam {color_name} {size} — exists")

    print("\nAll renders complete!")


if __name__ == "__main__":
    main()
