"""Плитки пола, стен и дверей в стиле Rebirth: строятся один раз и кэшируются как pygame.Surface."""
from ..art import world as W

_cache = {}


def _get(key, make):
    surf = _cache.get(key)
    if surf is None:
        surf = _cache[key] = make().to_surface()
    return surf


def floor(kind, color, variant):
    color = tuple(color)
    return _get(("f", kind, color, variant % 4), lambda: W.floor_tile(kind, color, variant % 4))


def wall(kind, color):
    color = tuple(color)
    return _get(("w", kind, color), lambda: W.wall_tile(kind, color))


def door(w, h, orient, locked, base, sky=False):
    base = tuple(base)
    return _get(("d", w, h, orient, locked, base, sky), lambda: W.door(w, h, orient, locked, base, sky))


def stump():
    return _get(("s",), W.stump)
