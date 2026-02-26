"""
MapGen — Print Size Definitions.

Maps Etsy/Gelato print sizes to figure dimensions and default
map distances.
"""

PRINT_SIZES = {
    "8x10": {"width_in": 8, "height_in": 10, "distance_m": 2500},
    "11x14": {"width_in": 11, "height_in": 14, "distance_m": 3500},
    "16x20": {"width_in": 16, "height_in": 20, "distance_m": 5000},
    "18x24": {"width_in": 18, "height_in": 24, "distance_m": 6500},
    "24x36": {"width_in": 24, "height_in": 36, "distance_m": 9000},
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
