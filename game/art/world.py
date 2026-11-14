"""Мир: плитки препятствий, полы и стены зон, двери, иконки предметов, сердца, монеты, снаряды — в стиле Rebirth."""
import math
import random

from .canvas import Canvas, ell_set, ring_set, rect_set, poly_set, line_set, dark, light, mix, OUT

T = 16


def _tile_border(c, col=OUT):
    for i in range(T):
        for x, y in ((i, 0), (i, T - 1), (0, i), (T - 1, i)):
            c.px(x, y, col)
    for x, y in ((0, 0), (T - 1, 0), (0, T - 1), (T - 1, T - 1)):
        c.p[y][x] = None


# ---------- препятствия (плитки 16x16) ----------
def rock():
    c = Canvas(T, T)
    c.P([(2, 14), (1, 8), (4, 3), (9, 1.5), (13, 4), (15, 9), (14, 14)], (156, 156, 168))
    c.P([(3, 9), (5, 5), (9, 3.5), (8, 7)], (206, 206, 216), shade=False)
    c.R(4, 13, 10, 1, (96, 94, 110), shade=False)
    c.L(10, 6, 12, 11, (104, 102, 120), 1)
    c.L(5, 10, 7, 12, (112, 110, 126), 1)
    return c.outlined().to_crop() if False else _crop16(c.outlined())


def _crop16(c):
    out = Canvas(T, T)
    for y in range(T):
        for x in range(T):
            out.p[y][x] = c.p[y][x]
    return out


def hedge():
    c = Canvas(T, T)
    c.R(0, 1, T, 15, (46, 140, 66))
    for x, y, r in ((3, 4, 3), (9, 3, 3.2), (13, 7, 3), (5, 10, 3.4), (11, 12, 3.2), (2, 13, 2.6)):
        c.E(x, y, r, r, (70, 176, 84))
    for x, y in ((3, 3), (9, 2), (12, 6), (5, 9), (10, 11)):
        c.px(x, y, (150, 226, 120))
    c.R(0, 14, T, 2, (30, 98, 50), shade=False)
    _tile_border(c)
    return c


def barrier():
    c = Canvas(T, T)
    c.R(0, 2, T, 14, (232, 232, 238), shade=False)
    for x in range(-8, 24, 8):
        c.P([(x, 2), (x + 4, 2), (x + 12, 16), (x + 8, 16)], (240, 130, 40), shade=False)
    c.R(0, 2, T, 2, (255, 255, 255), shade=False)
    c.R(0, 13, T, 3, (150, 150, 164), shade=False)
    for x in range(T):
        for y in range(2, 16):
            q = c.p[y][x]
            if q and y > 12:
                c.p[y][x] = dark(q[:3], 0.25) + (255,)
    _tile_border(c)
    return c


def crate():
    c = Canvas(T, T)
    c.R(0, 0, T, T, (178, 126, 74))
    c.R(1, 1, 14, 14, (160, 110, 64), shade=False)
    for y in (4, 8, 12):
        c.R(2, y, 12, 1, (126, 84, 48), shade=False)
    c.L(1, 1, 14, 14, (122, 80, 46), 1)
    c.L(14, 1, 1, 14, (122, 80, 46), 1)
    for x, y in ((1, 1), (14, 1), (1, 14), (14, 14)):
        c.px(x, y, (232, 208, 140))
    c.R(0, 0, T, 1, (214, 160, 96), shade=False)
    _tile_border(c)
    return c


def basalt():
    c = Canvas(T, T)
    c.R(0, 1, T, 15, (52, 44, 56))
    c.R(2, 2, 7, 5, (76, 66, 80), shade=False)
    c.R(9, 8, 5, 5, (66, 58, 72), shade=False)
    c.L(3, 9, 7, 12, (255, 110, 30), 1)
    c.L(7, 12, 12, 10, (255, 176, 44), 1)
    c.L(11, 3, 13, 6, (255, 110, 30), 1)
    c.R(0, 14, T, 2, (30, 24, 34), shade=False)
    _tile_border(c)
    return c


def cloud():
    c = Canvas(T, T)
    c.R(1, 2, 14, 13, (244, 248, 255), shade=False)
    for cx, cy, r in ((4, 4, 4), (11, 3, 4), (3, 11, 4), (12, 11, 4), (8, 8, 5)):
        c.E(cx, cy, r, r, (255, 255, 255), shade=False)
    c.R(2, 12, 12, 3, (204, 222, 246), shade=False)
    c.E(8, 13, 6, 2, (196, 214, 240), shade=False)
    out = c.outlined((140, 176, 224))
    return _crop16(out)


# ---------- полы ----------
def floor_tile(kind, base, seed):
    """Плитка пола 16x16: base — цвет из пары зоны, seed — вариант (0..3)."""
    rng = random.Random(seed * 7919 + sum(map(ord, kind)) % 1000)
    c = Canvas(T, T)
    c.flat(rect_set(0, 0, T, T), base)
    d1, l1 = dark(base, 0.16), light(base, 0.14)
    if kind in ("forest", "suburbs"):
        for _ in range(7):
            x, y = rng.randrange(1, 14), rng.randrange(2, 15)
            col = d1 if rng.random() < 0.5 else l1
            c.px(x, y, col)
            c.px(x, y - 1, col)
            if rng.random() < 0.5:
                c.px(x + 1, y - 2, col)
        if rng.random() < 0.35:
            fx, fy = rng.randrange(2, 13), rng.randrange(2, 13)
            c.px(fx, fy, (255, 244, 170))
            c.px(fx + 1, fy, (250, 130, 150) if rng.random() < 0.5 else (255, 255, 255))
    elif kind == "city":
        for _ in range(16):
            c.px(rng.randrange(T), rng.randrange(T), d1 if rng.random() < 0.6 else l1)
        c.R(0, 0, T, 1, dark(base, 0.12), shade=False)
        c.R(0, 0, 1, T, dark(base, 0.12), shade=False)
        if rng.random() < 0.3:
            x = rng.randrange(2, 12)
            c.L(x, 3, x + 3, 12, dark(base, 0.3), 1)
    elif kind == "center":
        for _ in range(10):
            c.px(rng.randrange(T), rng.randrange(T), rng.choice(((255, 96, 214), (84, 255, 214), d1, l1)))
        y = rng.randrange(2, 14)
        c.R(rng.randrange(0, 6), y, rng.randrange(4, 10), 1, rng.choice(((255, 96, 214), (84, 255, 214))), shade=False)
    elif kind == "shine":
        c.R(0, 0, T, 1, l1, shade=False)
        c.R(0, 0, 1, T, l1, shade=False)
        c.R(0, T - 1, T, 1, d1, shade=False)
        c.R(T - 1, 0, 1, T, d1, shade=False)
        if rng.random() < 0.7:
            x = rng.randrange(3, 10)
            c.L(x, 3, x + 4, 9, d1, 1)
            c.L(x + 4, 9, x + 3, 13, d1, 1)
        for _ in range(4):
            c.px(rng.randrange(2, 14), rng.randrange(2, 14), l1)
    elif kind == "hell":
        for _ in range(10):
            c.px(rng.randrange(T), rng.randrange(T), d1 if rng.random() < 0.6 else l1)
        if rng.random() < 0.4:
            x, y = rng.randrange(2, 8), rng.randrange(2, 10)
            c.L(x, y, x + 3, y + 2, (90, 36, 24), 1)
            c.L(x + 3, y + 2, x + 6, y + 1, (150, 54, 22), 1)
        c.R(0, 0, T, 1, dark(base, 0.25), shade=False)
        c.R(0, 0, 1, T, dark(base, 0.25), shade=False)
    elif kind == "heaven":
        for _ in range(3):
            x, y = rng.randrange(1, 10), rng.randrange(2, 14)
            c.R(x, y, rng.randrange(3, 6), 1, dark(base, 0.1), shade=False)
        for _ in range(4):
            c.px(rng.randrange(T), rng.randrange(T), (255, 255, 255))
    elif kind in ("house", "wood"):
        c.R(0, 0, T, 1, dark(base, 0.3), shade=False)
        c.R(0, 8, T, 1, dark(base, 0.3), shade=False)
        for y0 in (0, 8):
            off = rng.randrange(3, 12)
            c.R(off, y0 + 1, 1, 7, dark(base, 0.25), shade=False)
            for _ in range(3):
                c.px(rng.randrange(1, 15), y0 + rng.randrange(2, 7), d1)
    else:
        for _ in range(8):
            c.px(rng.randrange(T), rng.randrange(T), d1)
    return c


def wall_tile(kind, base, seed=0):
    """Плитка стены 16x16."""
    rng = random.Random(seed + 17)
    c = Canvas(T, T)
    d, l = dark(base, 0.3), light(base, 0.18)
    c.flat(rect_set(0, 0, T, T), base)
    if kind == "trees":
        for x, y, r in ((3, 3, 5), (11, 4, 5), (7, 10, 5.5), (14, 12, 4), (1, 13, 4)):
            c.E(x, y, r, r, dark(base, 0.2 + rng.random() * 0.2))
        for _ in range(8):
            c.px(rng.randrange(T), rng.randrange(T), light(base, 0.1))
        for _ in range(7):
            c.px(rng.randrange(T), rng.randrange(T), dark(base, 0.6))
    elif kind == "fence":
        for x in (0, 8):
            c.R(x, 0, 7, T, mix(base, (160, 110, 70), 0.18))
            c.R(x + 7, 0, 1, T, d, shade=False)
            c.R(x, 0, 1, T, l, shade=False)
        c.px(3, 3, d)
        c.px(11, 12, d)
        c.R(0, 5, T, 1, d, shade=False)
        c.R(0, 11, T, 1, d, shade=False)
    elif kind in ("wallpaper",):
        c.R(0, 0, T, T, base)
        for x in (0, 8):
            c.R(x, 0, 4, T, light(base, 0.1), shade=False)
        for y in (3, 11):
            for x in (2, 10):
                c.px(x, y, d)
                c.px(x + 1, y + 1, d)
        c.R(0, 14, T, 2, dark(base, 0.45), shade=False)
    elif kind == "acid":
        for _ in range(7):
            y = rng.randrange(T)
            c.R(rng.randrange(0, 6), y, rng.randrange(5, 16), 1, rng.choice(((255, 70, 200), (70, 255, 210), l, d)), shade=False)
    elif kind == "lava":
        for y in (0, 8):
            for x in range(0, T, 8):
                c.R(x + (4 if y else 0), y, 7, 7, mix(base, (96, 80, 100), 0.35 + rng.random() * 0.2))
        c.R(0, 7, T, 1, (255, 110, 30), shade=False)
        c.R(3, 15, 6, 1, (255, 160, 40), shade=False)
    else:
        for _ in range(10):
            c.px(rng.randrange(T), rng.randrange(T), rng.choice((d, l)))
    return c


# ---------- двери ----------
def door(w, h, orient, locked, base, sky=False, kind="fence"):
    """Дверной проём: тёмный проём в раме. orient 'h' (двери сверху/снизу, широкие) или 'v'."""
    c = Canvas(w, h)
    frame = (255, 214, 96) if sky else dark(base, 0.15)
    inner = (255, 252, 240) if sky else (20, 12, 18)
    c.flat(rect_set(0, 0, w, h), inner)
    c.flat({(x, y) for x in range(w) for y in range(h) if x in (0, w - 1) or y in (0, h - 1)}, frame)
    c.flat({(x, y) for x in range(1, w - 1) for y in range(1, h - 1) if x in (1, w - 2) or y in (1, h - 2)}, light(frame, 0.2) if sky else dark(base, 0.5))
    if locked:
        if sky:
            for x in range(3, w - 3, 3):
                c.R(x, 2, 1, h - 4, (255, 236, 150), shade=False)
        else:
            plank = (112, 72, 42)
            if orient == "h":
                for y in range(2, h - 2, 4):
                    c.R(1, y, w - 2, 3, plank)
                    c.px(3, y + 1, (214, 190, 140))
                    c.px(w - 4, y + 1, (214, 190, 140))
            else:
                for x in range(2, w - 2, 4):
                    c.R(x, 1, 3, h - 2, plank)
                    c.px(x + 1, 3, (214, 190, 140))
                    c.px(x + 1, h - 4, (214, 190, 140))
    return c


# ---------- иконки предметов (12x12 -> 14x14) ----------
def icon(kind, color):
    c = Canvas(12, 12)
    col = tuple(color)
    A = lambda *a, **k: c.R(*a, **k)
    if kind == "burger":
        c.E(6, 3.2, 5, 2.4, (234, 176, 84)); A(1, 5, 10, 2, col, shade=False); A(1, 7, 10, 1, (130, 74, 42), shade=False); A(1, 8, 10, 2, (234, 176, 84))
        c.px(3, 2, (255, 240, 190)); c.px(7, 2, (255, 240, 190))
    elif kind == "broom":
        c.L(2, 1, 8, 8, (166, 112, 66), 2); c.P([(6, 7), (11, 8), (9, 11.5), (5, 10)], col)
    elif kind == "tv":
        A(1, 2, 10, 8, (96, 96, 118)); A(2, 3, 6, 6, col, shade=False); A(9, 4, 1, 2, (230, 60, 70), shade=False); c.L(4, 2, 2, 0, (210, 210, 220), 1); c.L(7, 2, 9, 0, (210, 210, 220), 1)
    elif kind == "bomb":
        c.E(5.5, 7, 5, 5, col); c.L(7, 2, 9, 0, (230, 200, 120), 1); A(5, 1, 3, 2, (96, 96, 108), shade=False); c.px(10, 0, (255, 232, 90)); c.px(3, 5, (255, 255, 255))
    elif kind == "feather":
        c.P([(6, 0), (10, 4), (7, 11), (4, 7), (3, 3)], col); c.L(6, 1, 4, 11, (214, 196, 140), 1)
    elif kind == "mask":
        c.E(6, 6, 5, 5.8, col); A(3, 4, 2, 2, OUT, shade=False); A(7, 4, 2, 2, OUT, shade=False); c.L(6, 0, 4, 11, OUT, 1)
    elif kind == "revolver":
        A(1, 3, 9, 3, col); A(1, 6, 3, 5, col); c.E(6, 5, 2, 2, (116, 80, 56), shade=False); c.px(2, 4, (236, 240, 250))
    elif kind == "soldier":
        A(3, 4, 6, 6, col); A(4, 1, 4, 3, (255, 208, 176), shade=False); A(3, 0, 6, 2, (80, 126, 70), shade=False); A(9, 3, 2, 7, (70, 70, 74), shade=False)
    elif kind == "compass":
        c.E(6, 6, 5, 5, (236, 232, 214)); c.flat(ring_set(6, 6, 3.5, 3.5, 5.2, 5.2), col); c.L(6, 6, 9, 2, (230, 60, 70), 1); c.L(6, 6, 3, 10, (250, 250, 250), 1)
    elif kind == "clock":
        c.E(6, 6, 5, 5, (244, 244, 252)); c.flat(ring_set(6, 6, 4, 4, 5.4, 5.4), col); c.L(6, 6, 6, 2, OUT, 1); c.L(6, 6, 9, 7, OUT, 1)
    elif kind == "photo":
        A(1, 1, 10, 10, col, shade=False); A(2, 2, 8, 6, (206, 206, 220), shade=False); c.px(4, 4, (255, 220, 120)); c.L(2, 7, 5, 5, (110, 150, 110), 1); c.L(5, 5, 9, 7, (110, 150, 110), 1)
    elif kind == "halo":
        c.flat(ring_set(6, 6, 3.5, 1.8, 6, 3.4), col); c.flat(ring_set(6, 6, 3.4, 1.4, 4.4, 2.4), (255, 246, 190))
    elif kind == "grenade":
        c.E(6, 7, 4.2, 4.6, col); A(5, 1, 3, 3, (84, 84, 70), shade=False); c.L(8, 2, 10, 1, (232, 232, 100), 1); c.L(3, 6, 9, 8, OUT, 1)
    elif kind == "medkit":
        A(1, 3, 10, 8, col); A(5, 4, 2, 6, (226, 40, 52), shade=False); A(3, 6, 6, 2, (226, 40, 52), shade=False); A(4, 1, 4, 2, (214, 214, 220), shade=False)
    elif kind == "anchor":
        c.L(6, 2, 6, 10, col, 2); c.L(3, 5, 9, 5, col, 1); c.flat(ring_set(6, 8, 3.4, 3, 5, 4.4), col); c.E(6, 2, 1.4, 1.4, col, shade=False)
    elif kind == "wings":
        c.P([(6, 6), (0, 1), (1, 9), (5, 9)], col); c.P([(6, 6), (12, 1), (11, 9), (7, 9)], col); c.L(5, 10, 7, 10, (255, 216, 92), 1)
    elif kind == "bat":
        c.L(2, 10, 9, 3, col, 3); c.E(9, 3, 2, 2, col, shade=False); c.L(2, 10, 4, 8, (130, 86, 44), 3)
    elif kind == "smg":
        A(1, 4, 10, 3, col); A(3, 7, 2, 4, col); A(7, 7, 2, 3, (70, 70, 80), shade=False); A(10, 3, 2, 2, (70, 70, 80), shade=False)
    elif kind == "phone":
        A(3, 1, 6, 10, col); A(4, 2, 4, 6, (156, 214, 248), shade=False); c.L(4, 2, 7, 7, (255, 96, 96), 1); c.L(7, 2, 4, 7, (255, 96, 96), 1)
    elif kind == "impmini":
        c.E(6, 7, 4.4, 4, col); c.P([(3, 4), (2, 0), (5, 3)], (255, 232, 130), shade=False); c.P([(9, 4), (10, 0), (7, 3)], (255, 232, 130), shade=False); A(4, 6, 2, 2, (255, 255, 210), shade=False); A(7, 6, 2, 2, (255, 255, 210), shade=False)
    elif kind == "axe":
        c.L(2, 10, 8, 3, (160, 108, 62), 2); c.P([(6, 0.5), (11, 3), (10, 8), (7, 5)], col)
    elif kind == "shotgun":
        A(3, 3, 9, 2, (120, 120, 132), shade=False); A(3, 6, 9, 2, (120, 120, 132), shade=False); c.P([(0, 5), (4, 4), (4, 9), (1, 11)], col)
    elif kind == "kettle":
        c.E(5, 7, 4.6, 4, col); A(8, 4, 3, 2, col, shade=False); c.flat(ring_set(5, 3.4, 2.4, 1.6, 3.6, 3), OUT); c.px(4, 6, (255, 255, 255))
    elif kind == "gnome":
        c.P([(6, 0), (9.5, 5), (2.5, 5)], col); A(4, 5, 4, 3, (255, 208, 176), shade=False); A(3, 7, 6, 4, (246, 246, 246))
    elif kind == "mail":
        A(1, 3, 10, 7, col); c.L(1, 3, 6, 7, (150, 140, 120), 1); c.L(11, 3, 6, 7, (150, 140, 120), 1)
    elif kind == "monitor":
        A(2, 1, 8, 10, col); c.E(6, 4, 1.4, 1.4, (255, 90, 90), shade=False); A(4, 6, 4, 3, OUT, shade=False)
    elif kind == "soulgeyser":
        c.L(6, 11, 6, 0, col, 3); c.L(6, 11, 6, 0, (255, 255, 255), 1)
        for x, y in ((3, 8), (9, 5), (3, 2), (10, 9)):
            c.E(x, y, 1.2, 1.2, col, shade=False)
    elif kind == "scream":
        c.E(6, 5, 5, 5, col); A(3, 3, 2, 3, (34, 22, 54), shade=False); A(7, 3, 2, 3, (34, 22, 54), shade=False); c.E(6, 9, 2, 2.4, (34, 22, 54), shade=False)
    elif kind == "thorn":
        A(4, 3, 4, 8, col); c.E(6, 3, 2, 2, col, shade=False); A(3, 10, 6, 2, (116, 74, 46), shade=False)
        for a_, b_ in (((3, 4), (1, 3)), ((8, 4), (10, 3)), ((3, 7), (0, 7)), ((8, 7), (11, 7)), ((6, 1), (6, 0))):
            c.L(a_[0], a_[1], b_[0], b_[1], (255, 250, 190), 1)
    elif kind == "remote":
        A(3, 0, 6, 12, col); c.E(6, 3, 1.4, 1.4, (230, 60, 70), shade=False)
        for y in (6, 9):
            c.px(4, y, (232, 232, 240)); c.px(7, y, (232, 232, 240))
    elif kind == "vest":
        c.P([(1, 1), (4, 0), (6, 3), (8, 0), (11, 1), (11, 11), (1, 11)], col); c.L(6, 3, 6, 11, (194, 204, 218), 1); A(2, 6, 3, 2, (194, 204, 218), shade=False); A(7, 6, 3, 2, (194, 204, 218), shade=False)
    else:
        A(2, 2, 8, 8, col)
    return c.outlined()


# ---------- сердца, монеты ----------
_HEART = ("..kk.kk..",
          ".kRwRRRk.",
          "kRwRRRRRk",
          "kRRRRRRDk",
          ".kRRRRDk.",
          "..kRRDk..",
          "...kDk...",
          "....k....")


def heart(kind="full", gem=False):
    pal = {"k": OUT + (255,), "R": (232, 52, 72, 255), "w": (255, 232, 236, 255), "D": (150, 24, 52, 255)}
    pal_e = {"k": OUT + (255,), "R": (66, 46, 78, 255), "w": (96, 72, 108, 255), "D": (48, 32, 58, 255)}
    c = Canvas(9, 8)
    for y, row in enumerate(_HEART):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            use = pal
            if kind == "empty" or (kind == "half" and x > 4 and ch != "k"):
                use = pal_e
            c.p[y][x] = use[ch]
    return c


def gem_heart():
    c = heart("full")
    out = Canvas(11, 10)
    out.blit(c, 1, 1)
    for x, y in ((0, 2), (10, 3), (5, 0)):
        out.px(x, y, (255, 255, 235))
    return out


def coin(f=0):
    """Монета (7x7 с контуром), вращается: 4 кадра."""
    c = Canvas(5, 5)
    w = (2.4, 1.6, 0.8, 1.6)[f % 4]
    c.E(2.5, 2.5, w, 2.4, (255, 214, 70), shade=False)
    if w > 1.5:
        c.px(1, 1, (255, 250, 200))
        c.px(3, 3, (214, 150, 30))
    else:
        c.R(2, 0, 1, 5, (214, 150, 30), shade=False)
    return c.outlined()


def tear(r, color, friendly=True):
    """Снаряд: капля-слеза с бликом и тёмным контуром."""
    r = max(2, int(r))
    n = r * 2 + 3
    c = Canvas(n, n)
    m = n / 2.0
    c.E(m, m, r, r, color)
    c.px(m - r * 0.45, m - r * 0.5, (255, 255, 255))
    if r >= 3:
        c.px(m - r * 0.45 + 1, m - r * 0.5, (255, 255, 255))
    ring = ring_set(m, m, r - 1, r - 1, r, r)
    for x, y in ring:
        if y >= m:
            c.px(x, y, dark(color, 0.45))
    return c.outlined((40, 10, 30) if not friendly else (18, 22, 52))


def stump():
    """Пень (плитка 16x16): годовые кольца сверху."""
    c = Canvas(T, T)
    c.R(0, 0, T, T, (132, 86, 54))
    c.E(8, 7, 7, 6, (186, 138, 90), shade=False)
    c.flat(ring_set(8, 7, 3.2, 2.6, 4.2, 3.4), (146, 100, 62))
    c.flat(ring_set(8, 7, 0.4, 0.4, 1.6, 1.4), (146, 100, 62))
    c.R(0, 12, T, 4, (96, 62, 40), shade=False)
    c.L(3, 13, 3, 15, (70, 44, 30), 1)
    c.L(8, 13, 8, 15, (70, 44, 30), 1)
    c.L(13, 13, 13, 15, (70, 44, 30), 1)
    _tile_border(c)
    return c


# ---------- реквизит комнат ----------
def prop(kind, used=False):
    from . import humans
    if kind == "pedestal":
        c = Canvas(18, 13)
        c.R(0, 0, 18, 4, (176, 176, 196))
        c.R(2, 4, 14, 6, (128, 128, 150))
        c.R(1, 5, 2, 5, (156, 156, 176), shade=False)
        c.R(0, 10, 18, 3, (150, 150, 170))
        return c.outlined()
    if kind == "card":
        c = Canvas(14, 18)
        c.R(0, 0, 14, 18, (255, 216, 92))
        c.R(1, 1, 12, 16, (255, 236, 150), shade=False)
        for y, row in enumerate((".ppp.", "p...p", "....p", "..pp.", "..p..", ".....", "..p..")):
            for x, ch in enumerate(row):
                if ch == "p":
                    c.px(4 + x, 4 + y * 1.5 if False else 5 + y, (96, 40, 140))
        return c.outlined()
    if kind == "npc":
        c = humans.human(0, hair=(120, 80, 50), hair_style="short", shirt=(110, 110, 130) if used else (204, 142, 92),
                         pants=(84, 70, 64), shoes=(50, 40, 40), idle=True, mouth="line", blush=not used)
        return c.outlined()
    if kind == "altar":
        c = Canvas(22, 15)
        c.R(1, 0, 20, 5, (150, 150, 172))
        c.R(3, 5, 16, 8, (112, 112, 134))
        c.R(0, 12, 22, 3, (132, 132, 152))
        for x in (6, 10, 14):
            c.px(x, 8, (190, 120, 255) if not used else (80, 80, 96))
        return c.outlined()
    if kind == "bed":
        c = Canvas(30, 18)
        c.R(0, 2, 30, 14, (146, 98, 60))
        c.R(1, 3, 28, 11, (120, 170, 220))
        c.R(1, 3, 10, 11, (255, 250, 240))
        c.R(11, 3, 1, 11, (96, 140, 190), shade=False)
        c.R(0, 14, 3, 4, (110, 70, 44), shade=False)
        c.R(27, 14, 3, 4, (110, 70, 44), shade=False)
        return c.outlined()
    if kind == "house":
        c = Canvas(54, 42)
        c.R(5, 18, 44, 24, (232, 214, 180))
        c.R(5, 18, 44, 3, (206, 186, 150), shade=False)
        c.P([(0, 20), (27, 0), (54, 20)], (194, 72, 62))
        for y in (6, 11, 16):
            c.L(27 - (y) * 1.3, y + 1, 27 + (y) * 1.3, y + 1, (150, 48, 46), 1)
        c.R(22, 28, 10, 14, (118, 76, 48))
        c.px(30, 35, (255, 220, 110))
        for x in (9, 36):
            c.R(x, 25, 9, 9, (130, 196, 244))
            c.R(x + 4, 25, 1, 9, (232, 214, 180), shade=False)
            c.R(x, 29, 9, 1, (232, 214, 180), shade=False)
        c.R(38, 4, 5, 9, (150, 110, 90))
        return c.outlined()
    if kind == "exit":
        c = Canvas(18, 16)
        c.R(0, 0, 18, 16, (120, 78, 48))
        c.R(2, 2, 14, 12, (255, 238, 160), shade=False)
        c.R(2, 2, 14, 12, (36, 24, 30), shade=False)
        c.R(3, 3, 12, 10, (255, 236, 150), shade=False)
        return c.outlined()
    if kind == "gates":
        c = Canvas(40, 44)
        c.flat(ell_set(20, 20, 19, 19) | rect_set(1, 20, 38, 24), (255, 246, 206))
        c.flat(ring_set(20, 20, 17, 17, 19, 19), (255, 214, 90))
        c.flat(rect_set(1, 20, 2, 24) | rect_set(37, 20, 2, 24), (255, 214, 90))
        c.flat(ell_set(20, 20, 12, 12) | rect_set(8, 20, 24, 24), (255, 255, 255))
        for y in range(8, 42, 5):
            c.px(20, y, (255, 240, 190))
        return c.outlined()
    raise KeyError(kind)
