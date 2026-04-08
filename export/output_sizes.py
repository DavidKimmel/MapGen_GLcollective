"""
MapGen — Print Size Definitions.

Maps Etsy/Gelato print sizes to figure dimensions and default
map distances.
"""

PRINT_SIZES = {
    # US & Canada (inches)
    "5x7":   {"width_in": 5,     "height_in": 7,     "distance_m": 1800},
    "8x10":  {"width_in": 8,     "height_in": 10,    "distance_m": 2500},
    "11x14": {"width_in": 11,    "height_in": 14,    "distance_m": 3500},
    "12x16": {"width_in": 12,    "height_in": 16,    "distance_m": 4000},
    "12x18": {"width_in": 12,    "height_in": 18,    "distance_m": 4000},
    "16x20": {"width_in": 16,    "height_in": 20,    "distance_m": 5000},
    "18x24": {"width_in": 18,    "height_in": 24,    "distance_m": 6500},
    "20x28": {"width_in": 20,    "height_in": 28,    "distance_m": 7000},
    "20x30": {"width_in": 20,    "height_in": 30,    "distance_m": 7500},
    "24x36": {"width_in": 24,    "height_in": 36,    "distance_m": 9000},
    # International / ISO (cm → inches for matplotlib)
    "A5":      {"width_in": 5.83,  "height_in": 8.27,  "distance_m": 2000},
    "A4":      {"width_in": 8.27,  "height_in": 11.69, "distance_m": 3000},
    "A3":      {"width_in": 11.69, "height_in": 16.54, "distance_m": 4500},
    "A2":      {"width_in": 16.54, "height_in": 23.39, "distance_m": 6000},
    "A1":      {"width_in": 23.39, "height_in": 33.11, "distance_m": 8500},
    "50x70cm": {"width_in": 19.69, "height_in": 27.56, "distance_m": 7000},
    "60x90cm": {"width_in": 23.62, "height_in": 35.43, "distance_m": 8500},
    "70x100cm":{"width_in": 27.56, "height_in": 39.37, "distance_m": 10000},
}


def get_size_config(size_name: str) -> dict:
    """Get the config dict for a print size name."""
    if size_name not in PRINT_SIZES:
        raise ValueError(
            f"Unknown size '{size_name}'. "
            f"Available: {', '.join(PRINT_SIZES.keys())}"
        )
    return PRINT_SIZES[size_name]


def get_pixel_dimensions(size_name: str, dpi: int = 300) -> tuple[int, int]:
    """Get exact pixel dimensions for a print size at given DPI."""
    config = get_size_config(size_name)
    return (
        int(config["width_in"] * dpi),
        int(config["height_in"] * dpi),
    )
