"""Generate diverse sample maps for Etsy mockups."""
from engine.text_layout import _font_cache
from engine.renderer import render_poster

# Clear font cache for fresh renders
_font_cache.clear()

PIN_COLOR = "#CC3333"

SAMPLES = [
    # (city, lat, lon, theme, crop, font, pin_style, line1, line2, line3, distance)

    # 1. Denver — 37th_parallel, full, font 1 (century gothic), heart pin
    ("denver", 39.7392, -104.9903,
     "37th_parallel", "full", 1, 1,
     "Denver", "Our Forever Home", "39.7392° N, 104.9903° W", None),

    # 2. Savannah — 37th_parallel, circle, font 5 (footlight), heart-pin
    ("savannah", 32.0809, -81.0912,
     "37th_parallel", "circle", 5, 2,
     "Michael & Grace", "Where We Said I Do", "15 October 2023", None),

    # 3. Prague — midnight_blue, full, font 3 (priestacy), classic pin
    ("prague", 50.0755, 14.4378,
     "midnight_blue", "full", 3, 3,
     "Our Honeymoon", "Prague, Czech Republic", "September 2024", None),

    # 4. New Orleans — midnight_blue, circle, font 4 (corsiva), heart pin
    ("nola", 29.9511, -90.0715,
     "midnight_blue", "circle", 4, 1,
     "Jack & Olivia", "Our First Date", "29.9511° N, 90.0715° W", None),

    # 5. Portland — clay_sage, full, font 2 (high tower text), house pin
    ("portland", 45.5152, -122.6784,
     "clay_sage", "full", 2, 4,
     "Our First Home", "Portland, Oregon", "Est. 2022", None),

    # 6. Lisbon — clay_sage, circle, font 5 (footlight), classic pin
    ("lisbon", 38.7223, -9.1393,
     "clay_sage", "circle", 5, 3,
     "Ben & Amelia", "Where It All Began", "38.7223° N, 9.1393° W", None),

    # 7. Charleston — gradient_roads, full, font 1 (century gothic), heart-pin
    ("charleston", 32.7765, -79.9311,
     "gradient_roads", "full", 1, 2,
     "Charleston", "Engaged", "32.7765° N, 79.9311° W", None),

    # 8. Edinburgh — gradient_roads, circle, font 2 (high tower text), house pin
    ("edinburgh", 55.9533, -3.1883,
     "gradient_roads", "circle", 2, 4,
     "Liam & Hannah", "Our Adventure Begins", "12 August 2023", None),
]

total = len(SAMPLES)
for idx, s in enumerate(SAMPLES, 1):
    city, lat, lon, theme, crop, font, pin, l1, l2, l3, dist = s
    fname = f"posters/sample_{idx:02d}_{city}_{theme}_{crop}.png"
    print(f"\n[{idx}/{total}] {city} | {theme} | {crop} | font {font} | pin {pin}")
    try:
        render_poster(
            location=f"{lat},{lon}",
            theme=theme,
            size="11x14",
            crop=crop,
            detail_layers=False,
            dpi=150,
            font_preset=font,
            pin_lat=lat,
            pin_lon=lon,
            pin_style=pin,
            pin_color=PIN_COLOR,
            text_line_1=l1,
            text_line_2=l2,
            text_line_3=l3,
            distance=dist,
            output_path=fname,
        )
        print(f"  -> {fname}")
    except Exception as e:
        print(f"  [ERROR] {e}")

print(f"\n{'='*60}")
print(f"Done! {total} samples generated in posters/")
