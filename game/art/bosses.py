"""Боссы и мини-боссы с анимацией: крылатые глаза взмахивают крыльями (глаз остаётся на месте — радужку рисует босс)."""
import math

from .canvas import Canvas, ell_set, ring_set, rect_set, poly_set, line_set, dark, light, mix, OUT
from . import humans

SHINE_IRIS = {1: (80, 150, 255), 2: (235, 150, 40), 3: (195, 60, 225)}
IMP_IRIS = {1: (255, 150, 35), 2: (255, 95, 25), 3: (255, 50, 35)}
FLAP = (0, 10, 20, 10)               # угол взмаха пера по кадрам (градусы)


def feather(c, root, ang_deg, length, width, fill, edge, hi=None, tip=None):
    """Одно перо: вытянутый ромб, светлая жилка и тёмный нижний край."""
    a = math.radians(ang_deg)
    d = (math.cos(a), math.sin(a))
    n = (-d[1], d[0])
    r = root
    pts = [(r[0] + n[0] * width * 0.3, r[1] + n[1] * width * 0.3),
           (r[0] + d[0] * length * 0.55 + n[0] * width, r[1] + d[1] * length * 0.55 + n[1] * width),
           (r[0] + d[0] * length, r[1] + d[1] * length),
           (r[0] + d[0] * length * 0.55 - n[0] * width, r[1] + d[1] * length * 0.55 - n[1] * width),
           (r[0] - n[0] * width * 0.3, r[1] - n[1] * width * 0.3)]
    c.flat(poly_set(pts), fill)
    if hi:
        c.L(r[0] + d[0] * 3 + n[0] * width * 0.3, r[1] + d[1] * 3 + n[1] * width * 0.3,
            r[0] + d[0] * length * 0.7 + n[0] * width * 0.3, r[1] + d[1] * length * 0.7 + n[1] * width * 0.3, hi)
    for p0, p1 in ((pts[2], pts[3]), (pts[3], pts[4])):
        c.L(p0[0], p0[1], p1[0], p1[1], edge)
    c.L(pts[1][0], pts[1][1], pts[2][0], pts[2][1], tip or edge)


WING_SET = ((-62, 40, 7), (-34, 46, 8), (-8, 48, 8), (20, 42, 7), (46, 32, 6))


def flyer(f, variant=1, kind="shine", S=1.0, with_iris=False):
    """Крылатый глаз: kind 'shine' (золото, нимб) или 'imp' (базальт и лава, рога)."""
    w, h = int(104 * S), int(84 * S)
    c = Canvas(w, h)
    cx, cy = w // 2, int(46 * S)
    flap = FLAP[f % 4]
    if kind == "shine":
        fill = {1: (255, 244, 205), 2: (232, 200, 120), 3: (196, 150, 205)}[variant]
        edge = {1: (205, 155, 60), 2: (150, 100, 40), 3: (90, 40, 115)}[variant]
        hi = light(fill, 0.6)
    else:
        fill = {1: (84, 72, 90), 2: (78, 66, 86), 3: (70, 58, 82)}[variant]
        edge = (30, 18, 30)
        hi = {1: (255, 120, 30), 2: (255, 150, 40), 3: (255, 190, 60)}[variant]
    for side in (-1, 1):
        for ang, length, width in WING_SET:
            base = 0 if side > 0 else 180
            a_ = (base + ang + flap * (1 if ang < 0 else 0.6)) if side > 0 else (180 - ang - flap * (1 if ang < 0 else 0.6))
            feather(c, (cx + side * 12 * S, cy), a_, length * S, width * S, fill, edge, hi)
    if kind == "shine":
        c.E(cx, cy, 18.5 * S, 18.5 * S, (255, 255, 255))
        c.flat(ring_set(cx, cy, 17 * S, 17 * S, 18.5 * S, 18.5 * S), edge)
        if variant == 3:
            for ang in (20, 80, 150, 210, 275, 330):
                v = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
                c.L(cx + v[0] * 17 * S, cy + v[1] * 17 * S, cx + v[0] * 11 * S, cy + v[1] * 11 * S, (220, 40, 70))
            c.L(cx - 30 * S, cy - 18 * S, cx - 20 * S, cy - 6 * S, (255, 70, 70))
            c.L(cx + 34 * S, cy + 10 * S, cx + 24 * S, cy + 18 * S, (255, 70, 70))
        halo = (255, 216, 92) if variant < 3 else (166, 74, 206)
        hy = int(11 * S) + (0, -1, 0, 1)[f % 4]
        c.flat(ring_set(cx, hy, 18 * S, 3.4 * S, 22 * S, 6.5 * S), halo)
        c.flat(ring_set(cx, hy - 1, 16 * S, 1.6 * S, 18 * S, 3 * S), light(halo, 0.65))
    else:
        lava = hi
        c.E(cx, cy, 19.5 * S, 19.5 * S, fill)
        c.flat(ring_set(cx, cy, 17.5 * S, 17.5 * S, 19.5 * S, 19.5 * S), lava)
        c.E(cx, cy, 15 * S, 15 * S, (255, 236, 190), shade=False)
        for ang in range(0, 360, 45):
            v = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
            c.L(cx + v[0] * 15 * S, cy + v[1] * 15 * S, cx + v[0] * 20 * S, cy + v[1] * 20 * S, lava)
        if variant >= 2:
            for sx in (-1, 1):
                for a_, b_ in (((26, -8), (32, -2)), ((32, -2), (30, 8))):
                    c.L(cx + sx * a_[0] * S, cy + a_[1] * S, cx + sx * b_[0] * S, cy + b_[1] * S, lava)
        for side in (-1, 1):
            hh = (0, 1, 0, -1)[f % 4]
            pts = [(cx + side * 8 * S, 22 * S), (cx + side * 12 * S, 11 * S), (cx + side * 20 * S, (4 + hh) * S), (cx + side * 27 * S, (6 + hh) * S),
                   (cx + side * 21 * S, 12 * S), (cx + side * 16 * S, 19 * S), (cx + side * 12 * S, 25 * S)]
            c.flat(poly_set(pts), (34, 24, 38))
            c.L(cx + side * 10 * S, 20 * S, cx + side * 19 * S, (8 + hh) * S, lava)
            c.px(cx + side * 26 * S, (6 + hh) * S, (255, 236, 150))
    if with_iris:
        c.E(cx + 1, cy + 4 * S, 10 * S, 10 * S, SHINE_IRIS[3])
        c.E(cx + 1, cy + 4 * S, 5 * S, 5 * S, (20, 10, 30), shade=False)
        c.px(cx - 1, cy + 2 * S, (255, 255, 255))
        for a_, b_ in (((cx - 40 * S, cy - 30 * S), (cx - 28 * S, cy - 10 * S)), ((cx + 38 * S, cy - 24 * S), (cx + 26 * S, cy - 8 * S)), ((cx - 8 * S, cy - 2 * S), (cx + 6 * S, cy + 12 * S))):
            c.L(a_[0], a_[1], b_[0], b_[1], (255, 60, 80), 2)
    return c


def shine(f, variant=1):
    return flyer(f, variant, "shine")


def imp_boss(f, variant=1):
    return flyer(f, variant, "imp")


def shine_form(f):
    return flyer(f, 3, "shine", S=0.46, with_iris=True)


def god_wings():
    """Бог: радиальная симметрия, ряды перьев вокруг одного глаза. Радужку рисует босс; слой вращает игра."""
    n = 150
    c = Canvas(n, n)
    m = n // 2
    gold, white, pale = (232, 190, 90), (255, 252, 238), (214, 232, 255)
    for count, length, width, fill, edge, offset in ((24, 72, 7, pale, (150, 182, 228), 0.0),
                                                      (24, 58, 8, white, gold, 7.5),
                                                      (12, 40, 8, (255, 246, 205), gold, 0.0)):
        for i in range(count):
            ang = math.radians(offset + i * 360 / count)
            feather(c, (m + math.cos(ang) * 8, m + math.sin(ang) * 8), math.degrees(ang), length, width, fill, edge, light(fill, 0.5))
    ring = lambda r0, r1: ring_set(m, m, r0, r0, r1, r1)
    c.flat(ring(29.5, 32), gold)
    c.flat(ring(23, 24.5), gold)
    for i in range(36):
        a = math.radians(i * 10)
        r0, r1 = (24, 31) if i % 3 == 0 else (24, 27)
        c.L(m + math.cos(a) * r0, m + math.sin(a) * r0, m + math.cos(a) * r1, m + math.sin(a) * r1, (255, 220, 120))
    c.E(m, m, 17.5, 17.5, (255, 255, 255))
    c.flat(ring(16, 18), gold)
    return c.outlined()


def draw_iris(surf_draw_fn=None):
    return None


# ---------- наземные боссы ----------
def _saw(c, x, y, f, r=7):
    c.E(x, y, r, r, (196, 202, 218))
    c.E(x, y, 2.4, 2.4, (112, 118, 138), shade=False)
    for k_ in range(8):
        a = math.radians(k_ * 45 + f * 15)
        c.px(x + math.cos(a) * (r + 1), y + math.sin(a) * (r + 1), (236, 240, 250))
        c.px(x + math.cos(a) * (r - 1.5), y + math.sin(a) * (r - 1.5), (130, 136, 156))


def lumberjack_boss(f):
    body = humans.human(f, k=2.05, hair=None, shirt=(205, 55, 55), pants=(58, 62, 110), shoes=(70, 44, 30), accents=(humans._plaid,),
                        blush=False, mouth=None, eyes=None, post=humans._lumberjack_post)
    c = Canvas(body.w + 14, body.h)
    c.blit(body, 0, 0)
    bob = humans.BOB[f % 4]
    _saw(c, body.w + 3, 27 + bob, f, 8)
    c.L(body.w - 4, 25 + bob, body.w + 1, 27 + bob, (150, 100, 60), 2)
    return c


def neighbor_boss(f):
    i = f % 4
    c = Canvas(44, 44)
    bob = (0, -1, 0, -1)[i]
    c.R(15, 34, 7, 8, (84, 84, 124), shade=False)
    c.R(24, 34, 7, 8, (84, 84, 124), shade=False)
    c.R(9, 16 + bob, 26, 18, (236, 152, 72))
    c.R(9, 26 + bob, 26, 3, (200, 112, 40), shade=False)
    c.E(22, 10 + bob, 9, 8.4, (255, 208, 176))
    c.R(12, 2 + bob, 20, 5, (140, 96, 62))
    for sx in (-1, 1):
        c.eye(22 + sx * 4.6, 10 + bob, 3.2, 3.6, iris=(230, 20, 20))
        c.L(22 + sx * 8, 5 + bob + (0 if sx > 0 else 0), 22 + sx * 2, 7.5 + bob, OUT, 2)
    c.R(16, 15 + bob, 12, 3, (40, 8, 12), shade=False)
    for x in range(17, 28, 3):
        c.R(x, 15 + bob, 2, 1, (255, 255, 250), shade=False)
    for sx, sw in ((-1, -1 if i % 2 else 1), (1, 1 if i % 2 else -1)):
        c.R(21 + sx * 15, 17 + bob + sw, 6, 14, (236, 152, 72))
        c.R(21 + sx * 15, 29 + bob + sw, 6, 4, (255, 208, 176), shade=False)
    c.R(0, 32, 44, 10, (214, 52, 52))                                    # газонокосилка
    c.R(4, 34, 16, 3, (250, 222, 72), shade=False)
    c.L(22, 32, 22, 22, (160, 160, 170), 2)
    c.R(18, 20 + bob, 8, 2, (60, 60, 70), shade=False)
    for x in (8, 36):
        c.E(x, 40, 3.8, 3.8, (50, 50, 62), shade=False)
        a = i * math.pi / 2
        c.px(x + math.cos(a) * 2, 40 + math.sin(a) * 2, (200, 200, 214))
        c.px(x - math.cos(a) * 2, 40 - math.sin(a) * 2, (200, 200, 214))
    return c


def mayor(f):
    i = f % 4
    c = Canvas(46, 42)
    bob = (0, 0, -1, -1)[i]
    c.R(14, 12 + bob, 18, 18, (60, 62, 94))
    c.P([(22, 14 + bob), (25, 14 + bob), (26, 26 + bob), (23, 28 + bob)], (230, 60, 70), shade=False)
    c.E(23, 7 + bob, 8, 7, (255, 210, 176))
    c.R(15, 0 + bob, 16, 4, (156, 156, 168))
    for sx in (-1, 1):
        c.eye(23 + sx * 3.4, 7 + bob, 2.2, 2.6)
    c.R(20, 11 + bob, 6, 1, OUT, shade=False)
    c.R(2, 28, 42, 12, (146, 92, 56))
    c.R(2, 28, 42, 3, (176, 118, 72), shade=False)
    c.R(8, 25 - (i % 2), 11, 5, (246, 246, 236), shade=False)
    c.L(9, 27, 17, 27, (50, 50, 170), 1)
    for sx in (-1, 1):
        c.R(23 + sx * 12 - 2, 17 + bob, 4, 10, (60, 62, 94), shade=False)
        c.R(23 + sx * 12 - 2, 26 + bob + (i % 2) * (1 if sx > 0 else 0), 4, 3, (255, 210, 176), shade=False)
    return c


def mayor_desk(f):
    i = f % 4
    c = Canvas(54, 44)
    jaw = (0, 3, 5, 3)[i]
    lift = ((0, 1), (1, 0), (0, 1), (1, 0))[i]
    for k_, x in enumerate((6, 16, 34, 44)):
        c.R(x, 32 - lift[k_ % 2], 4, 10 + lift[k_ % 2], (112, 70, 40), shade=False)
    c.R(2, 8, 50, 14, (140, 90, 52))
    c.R(2, 8, 50, 4, (178, 122, 76), shade=False)
    c.R(4, 20, 46, 12 + jaw // 2, (140, 90, 52))
    c.R(8, 18, 38, 4 + jaw, (46, 10, 22), shade=False)
    for x in range(9, 45, 5):
        c.P([(x, 18), (x + 4, 18), (x + 2, 23)], (255, 255, 240), shade=False)
        c.P([(x, 22 + jaw), (x + 4, 22 + jaw), (x + 2, 18 + jaw)], (255, 255, 240), shade=False)
    for x in (15, 37):
        c.eye(x, 11, 4, 4.4, iris=(230, 24, 30))
    c.P([(24, 0), (28, 0), (31, 9), (21, 9)], (230, 60, 70), shade=False)
    return c


def mayor_surreal(f):
    i = f % 4
    c = Canvas(50, 50)
    pulse = (0, 1, 0, -1)[i]
    c.E(25, 25, 18 + pulse * 0.6, 21 + pulse * 0.6, (244, 204, 220))
    ring = ring_set(25, 25, 12, 14.5, 14.5, 17)
    c.flat(ring, (156, 62, 196))
    for k_, (ex, ey) in enumerate(((17, 14), (33, 14), (25, 23), (15, 31), (35, 31), (25, 39))):
        look = ((1, 0), (0, 1), (-1, 0), (0, -1))[(i + k_) % 4]
        c.eye(ex, ey, 4, 4.4, look=look, iris=(122, 30, 172), white=(252, 244, 250))
    c.P([(22, 0), (28, 0), (32, 13), (18, 13)], (230, 60, 70), shade=False)
    wave = (0, -2, -4, -2)[i]
    c.L(7, 25, 1, 15 + wave, (255, 210, 176), 3)
    c.L(43, 25, 49, 15 - wave, (255, 210, 176), 3)
    return c


def chaos(f):
    """Хаос: обломок здания, крона дерева и лицо в одном; куски дрожат и вращаются."""
    i = f % 4
    j = ((0, 0), (1, 1), (0, 2), (-1, 1))[i]
    c = Canvas(70, 68)
    c.P([(10 + j[0], 42), (14, 9 + j[1]), (36, 4), (42, 32), (28, 48)], (118, 118, 144))
    for x in range(15, 35, 7):
        for y in range(11, 39, 8):
            c.R(x + j[0], y + j[1] * (1 if x > 20 else 0), 4, 5, (255, 236, 122) if (x + y + i) % 3 else (96, 204, 255), shade=False)
    c.E(46, 20 + j[1], 14, 14, (50, 160, 80))
    c.E(42, 16 + j[1], 8, 8, (84, 202, 102), shade=False)
    c.R(43, 28, 6, 22, (112, 72, 46))
    c.E(37, 44, 17, 17, (244, 204, 220))
    c.P([(4, 58), (20 + j[0] * 2, 48), (24, 64), (8, 66)], (232, 72, 192))
    c.P([(48, 54), (66, 44 - j[1]), (63, 64), (52, 66)], (62, 232, 204))
    for sx in (-1, 1):
        c.eye(37 + sx * 6, 41, 3.4, 4.0, look=(j[0], 0), iris=(200, 20, 80))
    c.R(29, 53, 16, 4 + (i % 2), (255, 236, 92), shade=False)
    c.L(0, 32, 20, 36 + j[1], (255, 72, 202), 3)
    c.L(46, 62, 66, 48 - j[1], (62, 255, 212), 3)
    return c


def tank(f):
    i = f % 4
    c = Canvas(40, 28)
    for y0 in (1, 19):
        c.R(1, y0, 38, 8, (48, 50, 56))
        for x in range(3 + (i % 2) * 2, 37, 5):
            c.L(x, y0 + 1, x, y0 + 6, (96, 98, 110), 1)
    c.R(3, 6, 34, 15, (92, 114, 78))
    c.R(3, 16, 34, 5, (66, 86, 58), shade=False)
    c.E(20, 13.5, 9, 8.6, (116, 140, 98))
    c.E(18, 11.5, 2.4, 2.4, (160, 182, 140), shade=False)
    c.P([(33, 11), (34, 13), (37, 13), (34, 15), (35, 18), (33, 15), (30, 18), (31, 15), (28, 13), (31, 13)], (240, 208, 72), shade=False) if i % 2 else None
    return c


def gate_keeper(f):
    """Хранитель врат: каменный ангел с весами; чаши весов качаются."""
    i = f % 4
    c = Canvas(46, 54)
    sw = (0, 1, 0, -1)[i]
    breath = (0, 0, 1, 0)[i]
    st, lt, dk, gold = (172, 174, 188), (212, 214, 226), (122, 124, 140), (236, 194, 92)
    for side in (-1, 1):
        c.P([(23 + side * 6, 15), (23 + side * 20, 6 - breath), (23 + side * 20, 38), (23 + side * 9, 42)], dk)
        for y in (17, 25):
            c.L(23 + side * 9, y, 23 + side * 17, y - 4 + breath, st, 1)
    c.P([(13, 21), (33, 21), (36, 52), (10, 52)], st)
    c.L(17, 25, 15, 51, dk, 1)
    c.L(29, 25, 31, 51, dk, 1)
    c.R(16, 8 - breath, 14, 14, lt)
    for sx in (-1, 1):
        c.R(23 + sx * 3 - 1, 13 - breath, 2, 3, (96, 196, 255), shade=False)
    c.flat(ring_set(23, 5, 5.5, 1.4, 8, 3), gold)
    c.R(6, 24, 6, 3, st)
    c.L(9, 25, 9, 6, gold, 1)
    c.L(2, 8 + sw, 16, 8 - sw, gold, 1)
    for px_, d_ in ((2, sw), (16, -sw)):
        c.L(px_, 8 + d_, px_, 15 + d_, gold, 1)
        c.flat({p for p in ell_set(px_, 15 + d_, 3.6, 2.6) if p[1] >= 15 + d_}, gold)
    return c
