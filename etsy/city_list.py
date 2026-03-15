"""GeoLine Collective — 25 Priority Cities for Etsy Launch.

Curated from GeoLine_Task5_FinalReport.docx.md Section 4.3.
Cities selected for Etsy search demand, visual map quality,
regional diversity, and gift market strength.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CityListing:
    """A city entry for Etsy listing generation."""
    city: str
    state: str          # State/region for US cities, country for international
    country: str
    lat: float
    lon: float
    distance: int       # Map radius in meters
    tier: int           # 1 = launch day, 2 = month 1-2, 3 = month 2-3
    hero_feature: str   # What makes this city's map visually compelling
    display_city: str = ""   # Override poster title (empty = use city)
    display_subtitle: str = ""  # Override subtitle (empty = use state/country)

    @property
    def slug(self) -> str:
        return self.city.lower().replace(" ", "_").replace("'", "")


# ---------------------------------------------------------------------------
# Tier 1 — Launch Day (Weeks 1-2)
# ---------------------------------------------------------------------------
TIER_1: list[CityListing] = [
    CityListing(
        city="Chicago", state="Illinois", country="USA",
        lat=41.8781, lon=-87.6298, distance=10000, tier=1,
        hero_feature="Lakefront + the Loop dense grid",
    ),
    CityListing(
        city="New York", state="New York", country="USA",
        lat=40.7580, lon=-73.9855, distance=10000, tier=1,
        hero_feature="Grid + Central Park + rivers",
        display_city="New York", display_subtitle="New York",
    ),
    CityListing(
        city="Washington DC", state="DC", country="USA",
        lat=38.9072, lon=-77.0369, distance=8000, tier=1,
        hero_feature="L'Enfant radial grid overlaid on blocks",
        display_city="Washington DC", display_subtitle="United States",
    ),
    CityListing(
        city="New Orleans", state="Louisiana", country="USA",
        lat=29.9511, lon=-90.0715, distance=8000, tier=1,
        hero_feature="The Crescent — river bend around French Quarter",
    ),
    CityListing(
        city="Nashville", state="Tennessee", country="USA",
        lat=36.1627, lon=-86.7816, distance=8000, tier=1,
        hero_feature="Cumberland River curves through city",
    ),
    CityListing(
        city="Austin", state="Texas", country="USA",
        lat=30.2672, lon=-97.7431, distance=8000, tier=1,
        hero_feature="Colorado River + tech-era grid expansion",
    ),
    CityListing(
        city="Seattle", state="Washington", country="USA",
        lat=47.6062, lon=-122.3321, distance=8000, tier=1,
        hero_feature="Puget Sound + irregular grid",
    ),
    CityListing(
        city="San Francisco", state="California", country="USA",
        lat=37.7749, lon=-122.4194, distance=8000, tier=1,
        hero_feature="Bay + grid compressed by hills + Golden Gate",
    ),
    CityListing(
        city="Portland", state="Oregon", country="USA",
        lat=45.5152, lon=-122.6784, distance=8000, tier=1,
        hero_feature="Willamette River splits city grid",
    ),
    CityListing(
        city="Denver", state="Colorado", country="USA",
        lat=39.7392, lon=-104.9903, distance=8000, tier=1,
        hero_feature="Grid city + mountain backdrop context",
    ),
]

# ---------------------------------------------------------------------------
# Tier 2 — Month 1-2
# ---------------------------------------------------------------------------
TIER_2: list[CityListing] = [
    CityListing(
        city="Boston", state="Massachusetts", country="USA",
        lat=42.3601, lon=-71.0589, distance=8000, tier=2,
        hero_feature="Organic colonial streets vs Back Bay grid contrast",
    ),
    CityListing(
        city="Miami", state="Florida", country="USA",
        lat=25.7617, lon=-80.1918, distance=8000, tier=2,
        hero_feature="Barrier island geography + Biscayne Bay",
    ),
    CityListing(
        city="Atlanta", state="Georgia", country="USA",
        lat=33.7490, lon=-84.3880, distance=10000, tier=2,
        hero_feature="Sprawling radial street system",
    ),
    CityListing(
        city="Minneapolis", state="Minnesota", country="USA",
        lat=44.9778, lon=-93.2650, distance=8000, tier=2,
        hero_feature="Chain of Lakes embedded in street grid",
    ),
    CityListing(
        city="Pittsburgh", state="Pennsylvania", country="USA",
        lat=40.4406, lon=-79.9959, distance=7000, tier=2,
        hero_feature="Three rivers confluence",
    ),
    CityListing(
        city="Savannah", state="Georgia", country="USA",
        lat=32.0809, lon=-81.0912, distance=6000, tier=2,
        hero_feature="Famous grid of 22 public squares",
    ),
    CityListing(
        city="Charleston", state="South Carolina", country="USA",
        lat=32.7765, lon=-79.9311, distance=6000, tier=2,
        hero_feature="Peninsula city + historic street grid",
    ),
    CityListing(
        city="Asheville", state="North Carolina", country="USA",
        lat=35.5951, lon=-82.5515, distance=6000, tier=2,
        hero_feature="French Broad River + mountain street geometry",
    ),
    CityListing(
        city="Salt Lake City", state="Utah", country="USA",
        lat=40.7608, lon=-111.8910, distance=8000, tier=2,
        hero_feature="Ultra-wide grid blocks + mountain backdrop",
    ),
    CityListing(
        city="Honolulu", state="Hawaii", country="USA",
        lat=21.3069, lon=-157.8583, distance=6000, tier=2,
        hero_feature="Diamond Head + harbor + Waikiki peninsula",
    ),
]

# ---------------------------------------------------------------------------
# Tier 3 — Month 2-3
# ---------------------------------------------------------------------------
TIER_3: list[CityListing] = [
    CityListing(
        city="Richmond", state="Virginia", country="USA",
        lat=37.5407, lon=-77.4360, distance=7000, tier=3,
        hero_feature="James River S-curves through city",
    ),
    CityListing(
        city="Chattanooga", state="Tennessee", country="USA",
        lat=35.0456, lon=-85.3097, distance=7000, tier=3,
        hero_feature="Tennessee River gorge geography",
    ),
    CityListing(
        city="Boise", state="Idaho", country="USA",
        lat=43.6150, lon=-116.2023, distance=7000, tier=3,
        hero_feature="Boise River + flat grid surrounded by foothills",
    ),
    CityListing(
        city="Raleigh", state="North Carolina", country="USA",
        lat=35.7796, lon=-78.6382, distance=7000, tier=3,
        hero_feature="Research Triangle urban grid",
    ),
    CityListing(
        city="Charlotte", state="North Carolina", country="USA",
        lat=35.2271, lon=-80.8431, distance=8000, tier=3,
        hero_feature="Banking district grid + light rail corridors",
    ),
]

# ---------------------------------------------------------------------------
# Tier 4 — SEO Expansion (World + US cities)
# ---------------------------------------------------------------------------
TIER_4: list[CityListing] = [
    # World cities
    CityListing(
        city="London", state="England", country="UK",
        lat=51.5074, lon=-0.1278, distance=12000, tier=4,
        hero_feature="Thames + dense historic street web",
        display_subtitle="England",
    ),
    CityListing(
        city="Paris", state="Île-de-France", country="France",
        lat=48.8566, lon=2.3522, distance=10000, tier=4,
        hero_feature="Haussmann boulevards radiating from Arc de Triomphe",
        display_subtitle="France",
    ),
    CityListing(
        city="Tokyo", state="Kantō", country="Japan",
        lat=35.6762, lon=139.6503, distance=12000, tier=4,
        hero_feature="Dense organic street network + Imperial Palace void",
        display_subtitle="Japan",
    ),
    CityListing(
        city="Rome", state="Lazio", country="Italy",
        lat=41.9028, lon=12.4964, distance=10000, tier=4,
        hero_feature="Tiber River + ancient radial streets",
        display_subtitle="Italy",
    ),
    CityListing(
        city="Barcelona", state="Catalonia", country="Spain",
        lat=41.3874, lon=2.1686, distance=10000, tier=4,
        hero_feature="Eixample superblock grid + Gothic quarter contrast",
        display_subtitle="Spain",
    ),
    CityListing(
        city="Amsterdam", state="North Holland", country="Netherlands",
        lat=52.3676, lon=4.9041, distance=8000, tier=4,
        hero_feature="Concentric canal rings",
        display_subtitle="Netherlands",
    ),
    CityListing(
        city="Lisbon", state="Lisboa", country="Portugal",
        lat=38.7223, lon=-9.1393, distance=8000, tier=4,
        hero_feature="Hillside streets + Tagus riverfront",
        display_subtitle="Portugal",
    ),
    # US cities not in Tiers 1-3
    CityListing(
        city="Philadelphia", state="Pennsylvania", country="USA",
        lat=39.9526, lon=-75.1652, distance=10000, tier=4,
        hero_feature="Original grid plan + Schuylkill/Delaware rivers",
    ),
    CityListing(
        city="San Diego", state="California", country="USA",
        lat=32.7157, lon=-117.1611, distance=10000, tier=4,
        hero_feature="Harbor + Coronado + sprawling coast grid",
    ),
]

ALL_CITIES: list[CityListing] = TIER_1 + TIER_2 + TIER_3 + TIER_4


def get_cities_by_tier(tier: int) -> list[CityListing]:
    """Return cities for a specific tier (1, 2, 3, or 4)."""
    return [c for c in ALL_CITIES if c.tier == tier]


def get_city(name: str) -> CityListing | None:
    """Look up a city by name (case-insensitive)."""
    name_lower = name.lower()
    for c in ALL_CITIES:
        if c.city.lower() == name_lower:
            return c
    return None
