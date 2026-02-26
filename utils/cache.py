"""
MapGen — Pickle-based OSM data cache with in-memory LRU layer.

Provides caching for OSM street networks, features, and geocoding results.
Cache keys are rounded so nearby requests share cached data.

Two-tier strategy:
  1. In-memory LRU (fast, same-session hits skip disk I/O)
  2. Disk pickle (persistent across restarts)
"""

import logging
import math
import os
import pickle
from collections import OrderedDict
from pathlib import Path

_logger = logging.getLogger("mapgen")

_UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_UTILS_DIR)
_DEFAULT_CACHE = os.path.join(_PROJECT_DIR, "cache")
CACHE_DIR_PATH = os.environ.get("MAPGEN_CACHE_DIR", _DEFAULT_CACHE)
CACHE_DIR = Path(CACHE_DIR_PATH)
CACHE_DIR.mkdir(exist_ok=True)

# In-memory LRU cache — holds up to 32 entries (enough for 2-3 full renders)
_MAX_MEMORY_ENTRIES = 32
_memory_cache: OrderedDict[str, object] = OrderedDict()


class CacheError(Exception):
    """Raised when a cache operation fails."""


def _cache_path(key: str) -> str:
    safe = key.replace(os.sep, "_")
    return os.path.join(CACHE_DIR, f"{safe}.pkl")


def _memory_get(key: str):
    """Check in-memory LRU cache. Returns value or None."""
    if key in _memory_cache:
        _memory_cache.move_to_end(key)
        return _memory_cache[key]
    return None


def _memory_set(key: str, value) -> None:
    """Store in in-memory LRU cache, evicting oldest if full."""
    _memory_cache[key] = value
    _memory_cache.move_to_end(key)
    while len(_memory_cache) > _MAX_MEMORY_ENTRIES:
        _memory_cache.popitem(last=False)


def cache_get(key: str):
    """Retrieve a cached object by key, or None if not found.

    Checks in-memory LRU first, then disk pickle.
    """
    # Tier 1: in-memory
    mem = _memory_get(key)
    if mem is not None:
        return mem

    # Tier 2: disk
    try:
        path = _cache_path(key)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            value = pickle.load(f)
        # Promote to memory for next access
        _memory_set(key, value)
        return value
    except Exception as e:
        raise CacheError(f"Cache read failed: {e}") from e


def cache_set(key: str, value) -> None:
    """Store an object in both in-memory and disk cache."""
    # Tier 1: memory
    _memory_set(key, value)

    # Tier 2: disk
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        path = _cache_path(key)
        with open(path, "wb") as f:
            pickle.dump(value, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception as e:
        raise CacheError(f"Cache write failed: {e}") from e


def round_cache_key(lat: float, lon: float, dist: float) -> tuple[float, float, int]:
    """Round lat/lon/dist to create stable cache keys.

    Rounds coordinates to 3 decimal places (~111m) and distance to
    nearest 500m so that slight pan/zoom changes hit the same cache entry.
    """
    rlat = round(lat, 3)
    rlon = round(lon, 3)
    rdist = int(math.ceil(dist / 500) * 500)
    return rlat, rlon, rdist
