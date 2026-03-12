"""Generate diverse sample maps for Etsy mockups."""
from engine.text_layout import _font_cache
from engine.renderer import render_poster

# Clear font cache for fresh renders
_font_cache.clear()

PIN_COLOR = "#CC3333"

SAMPLES = [
    # (city, lat, lon, theme, crop, font, pin_style, line1, line2, line3, distance)

    # 1. NYC — default theme, full, font 1 (sans), heart pin
    ("nyc", 40.7580, -73.9855,
     "37th_parallel", "full", 1, 1,
     "New York City", "United States", "40.7128° N, 74.0060° W", None),

    # 2. Paris — pastel_dream, circle, font 3 (priestacy), heart-pin
    ("paris", 48.8566, 2.3522,
     "pastel_dream", "circle", 3, 2,
     "James & Sophie", "Our First Date", "48.8566° N, 2.3522° E", None),

    # 3. Chicago — clay_sage, full, font 2 (perpetua titling), classic pin
    ("chicago", 41.8827, -87.6233,
     "clay_sage", "full", 2, 3,
     "Daniel & Emma", "Engaged", "22 March 2024", None),

    # 4. London — forest, circle, font 5 (footlight), house pin
    ("london", 51.5074, -0.1278,
     "forest", "circle", 5, 4,
     "Our First Home", "London, England", "Est. 2023", None),

    # 5. San Francisco — gradient_roads, full, font 4 (corsiva), heart pin
    ("sf", 37.7749, -122.4194,
     "gradient_roads", "full", 4, 1,
     "Ethan & Lily", "Where It All Began", "7 June 2021", None),

    # 6. Tokyo — pastel_dream, full, font 3 (priestacy), grad cap
    ("tokyo", 35.6762, 139.6503,
     "pastel_dream", "full", 3, 5,
     "Tokyo", "Japan", "35.6762° N, 139.6503° E", None),

    # 7. Austin — 37th_parallel, circle, font 1 (sans), heart-pin, zoomed in
    ("austin", 30.2672, -97.7431,
     "37th_parallel", "circle", 1, 2,
     "Ryan & Charlotte", "Where We First Met", "30 December 2022", 3000),

    # 8. Rome — clay_sage, full, font 5 (footlight), classic pin
    ("rome", 41.9028, 12.4964,
     "clay_sage", "full", 5, 3,
     "Rome", "Italy", "41.9028° N, 12.4964° E", None),

    # 9. Seattle — forest, full, font 2 (perpetua), house pin, zoomed in
    ("seattle", 47.6062, -122.3321,
     "forest", "full", 2, 4,
     "Our Forever Home", "Seattle, Washington", "Est. August 2024", 3500),

    # 10. Barcelona — gradient_roads, circle, font 4 (corsiva), heart pin
    ("barcelona", 41.3874, 2.1686,
     "gradient_roads", "circle", 4, 1,
     "Noah & Isabella", "Our First Date", "5 November 2023", None),

    # 11. Nashville — pastel_dream, full, font 1 (sans), house pin, zoomed out
    ("nashville", 36.1627, -86.7816,
     "pastel_dream", "full", 1, 4,
     "Nashville", "Tennessee", "Music City", 7000),

    # 12. Amsterdam — 37th_parallel, circle, font 5 (footlight), heart-pin
    ("amsterdam", 52.3676, 4.9041,
     "37th_parallel", "circle", 5, 2,
     "Lucas & Mia", "Where We First Met", "52.3676° N, 4.9041° E", None),
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
            size="16x20",
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
