"""Иконки 30 артефактов версии 1.1.0 (12x12 -> 14x14 с контуром).

Не зависит от pygame: рисуется тем же мини-растеризатором, что и остальные иконки (см. canvas.py).
Вызывается из world.icon(): имя иконки (поле "icon" в items.json) -> функция рисования.
"""
from .canvas import Canvas, OUT, ring_set

GOLD = (255, 214, 90)
WOOD = (150, 104, 60)
STEEL = (206, 214, 228)
WHITE = (250, 250, 250)
LEAF = (96, 190, 84)


def _new():
    c = Canvas(12, 12)
    return c, c.R


# ---------- библейские ----------
def seals(col):
    c, A = _new()
    A(1, 2, 10, 8, (232, 214, 170))
    c.L(1, 4, 10, 4, (190, 168, 120), 1)
    c.E(6, 7, 2.8, 2.8, col)
    c.px(6, 6, (255, 255, 255))
    for x in (2, 4, 8, 9):
        c.px(x, 9, (150, 60, 50))
    return c


def apple(col):
    c, A = _new()
    c.E(6, 7, 4.8, 4.4, col)
    c.L(6, 3, 6, 1, (110, 70, 40), 1)
    c.P([(7, 2), (10, 0.5), (10, 3.5)], LEAF, shade=False)
    c.px(4, 5, (255, 255, 255))
    c.px(3, 6, (255, 190, 190))
    return c


def thorncrown(col):
    c, A = _new()
    c.flat(ring_set(6, 8, 4.6, 2.0, 5.6, 3.0), (140, 100, 58))
    for a, b, d, e in ((1, 7, 0, 3), (3, 6, 2, 2), (6, 5, 6, 0), (9, 6, 10, 2), (11, 7, 11, 3)):
        c.L(a, b, d, e, col, 1)
    c.px(4, 9, (230, 50, 60))
    c.px(8, 10, (230, 50, 60))
    return c


def tablets(col):
    c, A = _new()
    A(1, 3, 5, 8, col)
    A(6, 3, 5, 8, col)
    c.E(3.5, 3.2, 2.5, 1.6, col)
    c.E(8.5, 3.2, 2.5, 1.6, col)
    for x, y in ((3, 5), (3, 7), (3, 9), (8, 5), (8, 7), (8, 9)):
        c.px(x, y, (96, 88, 74))
        c.px(x + 1, y, (96, 88, 74))
    return c


def flamesword(col):
    c, A = _new()
    c.L(2, 10, 9, 3, STEEL, 2)
    c.L(2, 7, 5, 10, WOOD, 1)
    c.L(1, 11, 2, 10, WOOD, 1)
    c.P([(8, 0), (11, 2), (11, 5), (9, 4), (8, 2.5)], col, shade=False)
    c.P([(9, 1.5), (10.5, 3), (9.5, 4)], GOLD, shade=False)
    return c


def revbook(col):
    c, A = _new()
    A(2, 1, 8, 10, col)
    A(2, 1, 2, 10, (96, 60, 140), shade=False)
    A(6, 3, 1, 6, GOLD, shade=False)
    A(5, 5, 3, 1, GOLD, shade=False)
    for x in (5, 7):
        c.px(x, 2, (255, 255, 255))
    return c


def silver(col):
    c, A = _new()
    c.E(4, 8, 3.6, 3.2, col)
    c.E(8, 5, 3.6, 3.2, col)
    c.px(8, 5, (110, 114, 130))
    c.px(4, 8, (110, 114, 130))
    c.px(7, 3, (255, 255, 255))
    c.px(3, 6, (255, 255, 255))
    return c


def grail(col):
    c, A = _new()
    c.P([(1, 1), (11, 1), (9.5, 5), (6, 7), (2.5, 5)], col)
    c.P([(2, 2), (10, 2), (9, 4), (3, 4)], (200, 30, 54), shade=False)
    A(5, 7, 2, 3, col)
    A(3, 10, 6, 2, col)
    c.px(3, 3, (255, 150, 160))
    return c


def seraphwings(col):
    c, A = _new()
    c.P([(5, 6), (0, 2), (0, 6), (3, 10), (5, 9)], col)
    c.P([(7, 6), (12, 2), (12, 6), (9, 10), (7, 9)], col)
    c.L(1, 3, 4, 8, (210, 200, 160), 1)
    c.L(11, 3, 8, 8, (210, 200, 160), 1)
    c.flat(ring_set(6, 2.5, 2.2, 1.0, 3.2, 1.7), GOLD)
    return c


def scales(col):
    c, A = _new()
    c.L(6, 2, 6, 10, col, 1)
    c.L(1, 3, 11, 3, col, 1)
    c.P([(0, 4), (4, 4), (2, 7)], col)
    c.P([(8, 4), (12, 4), (10, 7)], col)
    A(4, 10, 4, 1, col)
    c.px(6, 1, GOLD)
    return c


# ---------- древнерусские ----------
def perunaxe(col):
    c, A = _new()
    c.L(3, 11, 8, 3, WOOD, 2)
    c.P([(6, 1), (11, 3), (10, 8), (7, 5)], col)
    c.L(9, 1, 8, 3, GOLD, 1)
    c.L(8, 3, 10, 3, GOLD, 1)
    c.L(10, 3, 9, 6, GOLD, 1)
    return c


def mortar(col):
    c, A = _new()
    c.P([(2, 4), (10, 4), (9, 10), (3, 10)], col)
    A(1, 3, 10, 2, (240, 236, 216))
    c.L(9, 0, 6, 5, WOOD, 2)
    c.px(5, 7, OUT)
    c.px(7, 7, OUT)
    c.px(6, 9, OUT)
    return c


def leshyhorn(col):
    c, A = _new()
    c.L(2, 10, 3, 6, col, 3)
    c.L(3, 6, 7, 2, col, 2)
    c.L(7, 2, 10, 1, col, 1)
    c.E(2, 10, 1.8, 1.4, LEAF)
    c.px(4, 11, LEAF)
    return c


def koscheineedle(col):
    c, A = _new()
    c.E(5, 7, 3.2, 3.8, (238, 232, 216))
    c.L(1, 11, 11, 1, col, 1)
    c.L(10, 0, 11, 1, (255, 255, 255), 1)
    c.px(4, 6, (170, 150, 120))
    c.px(5, 8, (170, 150, 120))
    return c


def fang(col):
    c, A = _new()
    c.P([(2, 1), (10, 1), (8.5, 5), (6, 11), (3.5, 5)], col)
    c.px(4, 3, (255, 255, 255))
    c.px(6, 11, (130, 230, 90))
    c.px(5, 8, (130, 230, 90))
    return c


def moranacrown(col):
    c, A = _new()
    A(1, 7, 10, 3, col)
    c.P([(1, 7), (2, 2), (4, 7)], col)
    c.P([(4, 7), (6, 0), (8, 7)], col)
    c.P([(8, 7), (10, 2), (11, 7)], col)
    for x, y in ((2, 1), (6, 0), (10, 1)):
        c.px(x, y, WHITE)
    c.px(3, 8, WHITE)
    c.px(8, 9, WHITE)
    return c


def firefeather(col):
    c, A = _new()
    c.P([(6, 0), (10, 4), (7, 11), (4, 7), (3, 3)], col)
    c.L(6, 1, 4, 11, (255, 226, 130), 1)
    c.px(6, 0, (255, 80, 40))
    c.px(5, 1, (255, 80, 40))
    c.px(7, 4, (255, 226, 130))
    return c


def charm(col):
    c, A = _new()
    c.L(3, 0, 6, 3, (150, 110, 70), 1)
    c.L(9, 0, 6, 3, (150, 110, 70), 1)
    c.E(6, 7, 4.0, 4.0, col)
    c.L(6, 5, 6, 9, (90, 60, 40), 1)
    c.L(4, 6, 8, 6, (90, 60, 40), 1)
    return c


def velesstaff(col):
    c, A = _new()
    c.L(6, 6, 6, 11, WOOD, 2)
    A(4, 3, 4, 3, col)
    c.L(2, 0, 4, 3, col, 1)
    c.L(10, 0, 8, 3, col, 1)
    c.px(5, 4, OUT)
    c.px(7, 4, OUT)
    return c


def wreath(col):
    c, A = _new()
    c.flat(ring_set(6, 6, 3.0, 3.0, 5.4, 5.4), col)
    for x, y, f in ((6, 1, (255, 170, 200)), (1, 6, (255, 240, 150)), (10, 6, (255, 170, 200)),
                    (6, 10, (255, 240, 150)), (3, 2, (170, 210, 255)), (9, 2, (170, 210, 255))):
        c.px(x, y, f)
    return c


# ---------- греческие ----------
def torchfire(col):
    c, A = _new()
    c.L(4, 11, 6, 6, WOOD, 2)
    c.P([(6, 0), (9.5, 4), (8.5, 7), (4.5, 7), (3, 4)], col)
    c.P([(6, 3), (8, 5.5), (7, 7), (5, 7), (4.5, 5)], (255, 226, 110), shade=False)
    return c


def pandorabox(col):
    c, A = _new()
    A(1, 6, 10, 5, (150, 100, 70))
    A(1, 4, 10, 3, col)
    A(5, 6, 2, 2, GOLD, shade=False)
    for x in (3, 6, 9):
        c.L(x, 0, x, 2, (255, 240, 150), 1)
    return c


def icaruswings(col):
    c, A = _new()
    c.P([(5, 7), (0, 3), (0, 8), (4, 11), (5, 10)], col)
    c.P([(7, 7), (12, 3), (12, 8), (8, 11), (7, 10)], col)
    c.px(0, 8, (255, 90, 50))
    c.px(12 - 1, 8, (255, 90, 50))
    c.px(4, 11, (255, 90, 50))
    c.E(6, 2.4, 1.8, 1.8, (255, 244, 130), shade=False)
    return c


def medusa(col):
    c, A = _new()
    c.E(6, 7, 3.6, 3.8, col)
    for a, b, d, e in ((2, 3, 3, 5), (10, 3, 9, 5), (6, 0, 6, 3), (1, 7, 2, 7), (11, 7, 10, 7), (4, 1, 4, 4), (8, 1, 8, 4)):
        c.L(a, b, d, e, (80, 190, 80), 1)
    c.px(5, 7, (255, 236, 110))
    c.px(7, 7, (255, 236, 110))
    return c


def helm(col):
    c, A = _new()
    c.P([(2, 11), (2, 5), (4, 2), (8, 2), (10, 5), (10, 11), (8, 11), (8, 8), (4, 8), (4, 11)], col)
    A(5, 0, 2, 3, (150, 40, 60), shade=False)
    A(4, 6, 4, 1, OUT, shade=False)
    return c


def greaves(col):
    c, A = _new()
    c.P([(3, 0), (9, 0), (9.5, 11), (3.5, 11)], col)
    c.L(3, 3, 9, 3, GOLD, 1)
    c.L(3, 7, 9, 7, GOLD, 1)
    c.px(6, 1, (255, 255, 255))
    return c


def sandals(col):
    c, A = _new()
    A(1, 8, 8, 2, WOOD)
    A(2, 5, 5, 3, col)
    c.L(4, 5, 4, 3, WOOD, 1)
    c.P([(8, 8), (11, 3), (11, 8)], WHITE)
    c.L(9, 6, 11, 4, (200, 200, 210), 1)
    return c


def thread(col):
    c, A = _new()
    c.E(5, 5, 4.0, 4.0, col)
    c.L(2, 3, 8, 3, (200, 60, 70), 1)
    c.L(1, 5, 9, 5, (200, 60, 70), 1)
    c.L(2, 7, 8, 7, (200, 60, 70), 1)
    c.L(8, 8, 11, 11, col, 1)
    c.px(11, 10, col)
    return c


def charoncoin(col):
    c, A = _new()
    c.E(6, 6, 5.0, 5.0, col)
    c.flat(ring_set(6, 6, 3.6, 3.6, 4.6, 4.6), (120, 150, 164))
    A(5, 5, 2, 2, OUT, shade=False)
    c.px(3, 3, (255, 255, 255))
    return c


def zeusbolt(col):
    c, A = _new()
    c.P([(8, 0), (2, 6.5), (5.5, 6.5), (4, 12), (10, 4.5), (6.5, 4.5)], col)
    c.L(7, 1, 4, 5, (255, 255, 255), 1)
    return c


ICONS = {fn.__name__: fn for fn in (
    seals, apple, thorncrown, tablets, flamesword, revbook, silver, grail, seraphwings, scales,
    perunaxe, mortar, leshyhorn, koscheineedle, fang, moranacrown, firefeather, charm, velesstaff, wreath,
    torchfire, pandorabox, icaruswings, medusa, helm, greaves, sandals, thread, charoncoin, zeusbolt)}


def draw(kind, color):
    """Иконка артефакта (14x14 с контуром) или None, если такого вида нет."""
    fn = ICONS.get(kind)
    return fn(tuple(color)).outlined() if fn else None
