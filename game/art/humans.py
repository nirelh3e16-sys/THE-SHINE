"""Человечки: герои и людские враги/боссы. Единый «ригг» в стиле Isaac: огромная голова, крошечное тело,
4 кадра ходьбы. Параметр k масштабирует фигуру в родном разрешении (Том, боссы), а не раздувает пиксели."""
import math

from .canvas import Canvas, ell_set, rect_set, poly_set, dark, light, mix, OUT

SKIN = (246, 214, 190)
BOB = (0, -1, 0, -1)               # покачивание головы и тела
LIFT_L = (0, 1, 0, 0)              # поднятая левая нога
LIFT_R = (0, 0, 0, 1)              # поднятая правая нога
ARM_L = (0, 1, 0, -1)
ARM_R = (0, -1, 0, 1)
BASE_W, BASE_H = 18, 22


def _r(v):
    return max(1, int(round(v)))


def _face(c, cx, cy, k, eyes, skin, mouth="line", blush=True, tears=False, look=(0, 0), brow=False):
    ex = 2.9 * k
    rx, ry = 2.1 * k, 2.6 * k
    if eyes in ("big", "angry", "red"):
        iris = {"big": (20, 10, 16), "angry": (210, 24, 30), "red": (230, 30, 36)}[eyes]
        white = (255, 238, 232) if eyes == "red" else (250, 246, 240)
        for sx in (-1, 1):
            c.eye(cx + sx * ex, cy + 0.5 * k, rx, ry if eyes != "angry" else ry * 0.9, look=look, iris=iris, white=white)
        if eyes == "angry" or brow:
            for sx in (-1, 1):
                x0, x1 = cx + sx * ex - 2.4 * k, cx + sx * ex + 2.4 * k
                if sx < 0:
                    c.L(x0, cy - 2.6 * k, x1, cy - 1.2 * k, OUT, _r(k * 0.9))
                else:
                    c.L(x0, cy - 1.2 * k, x1, cy - 2.6 * k, OUT, _r(k * 0.9))
    elif eyes == "glow":
        for sx in (-1, 1):
            c.E(cx + sx * ex, cy + 0.5 * k, rx * 0.95, ry * 0.9, (255, 70, 76), shade=False)
            c.px(cx + sx * ex - 0.5, cy - 0.5 * k, (255, 236, 210))
    elif eyes == "hollow":
        for sx in (-1, 1):
            c.E(cx + sx * ex, cy + 0.5 * k, rx * 0.95, ry * 1.05, (6, 2, 8), shade=False)
    elif eyes == "shades":
        c.R(cx - 6 * k, cy - 1 * k, 12 * k, 3 * k, (10, 8, 14), shade=False)
        c.R(cx - 4.5 * k, cy - 1 * k, _r(k), _r(k), (130, 140, 180), shade=False)
        c.R(cx + 1.5 * k, cy - 1 * k, _r(k), _r(k), (130, 140, 180), shade=False)
    if tears:
        for sx in (-1, 1):
            c.R(cx + sx * ex - 0.5, cy + 3.2 * k, 1, _r(k * 1.5), (150, 205, 255), shade=False)
    if blush:
        for sx in (-1, 1):
            c.R(cx + sx * 5 * k - 0.5, cy + 3 * k, _r(k), _r(k), mix(skin, (255, 90, 110), 0.55), shade=False)
    my = cy + 4.5 * k
    if mouth == "line":
        c.R(cx - 1 * k, my, 2 * k, _r(k * 0.8), dark(skin, 0.8), shade=False)
    elif mouth == "o":
        c.R(cx - 0.5 * k, my - 0.5 * k, _r(k), _r(k * 1.6), dark(skin, 0.85), shade=False)
    elif mouth == "grin":
        c.R(cx - 2.5 * k, my - 0.5 * k, 5 * k, _r(k * 1.4), (40, 10, 16), shade=False)
        for x in (-1.5, 0.5):
            c.R(cx + x * k, my - 0.5 * k, _r(k), _r(k * 0.9), (255, 255, 250), shade=False)
    elif mouth == "shout":
        c.R(cx - 2.5 * k, my - 0.5 * k, 5 * k, _r(k * 2.2), (60, 8, 18), shade=False)
        c.R(cx - 1.5 * k, my - 0.5 * k, _r(k), _r(k), (255, 255, 250), shade=False)
        c.R(cx + 0.5 * k, my - 0.5 * k, _r(k), _r(k), (255, 255, 250), shade=False)
    elif mouth == "frown":
        c.R(cx - 1.5 * k, my, 3 * k, _r(k * 0.8), dark(skin, 0.85), shade=False)
        c.R(cx - 2 * k, my + 0.8 * k, _r(k), _r(k * 0.8), dark(skin, 0.85), shade=False)
        c.R(cx + 1 * k, my + 0.8 * k, _r(k), _r(k * 0.8), dark(skin, 0.85), shade=False)


def human(f=0, *, k=1.0, skin=SKIN, hair=None, hair_style="short", shirt=(80, 140, 240), pants=(60, 56, 96),
          shoes=(60, 42, 40), eyes="big", mouth="line", blush=True, tears=False, belt=None, accents=(), look=(0, 0),
          shadow=False, idle=False, head_k=1.0, pre=None, post=None, brow=False, sleeves=None):
    """Один кадр человечка без контура. pre/post — функции(c, cx, bob, i, k) для деталей под и над телом."""
    W, H = int(round(BASE_W * k)), int(round(BASE_H * k))
    c = Canvas(W, H)
    i = 0 if idle else f % 4
    bob = BOB[i] * _r(k * 0.8) if BOB[i] else 0
    cx = W / 2.0
    if shadow:
        c.shadow(cx, H - 1.6 * k, 6.8 * k, max(1.6, 1.8 * k))
    if pre:
        pre(c, cx, bob, i, k)
    # ноги
    legh = 3 * k
    for sx, lift in ((-1, LIFT_L[i]), (1, LIFT_R[i])):
        lx = cx + sx * 2.5 * k - 1.5 * k
        lift = lift * _r(k * 0.8)
        c.R(lx, 17 * k - lift, 3 * k, legh, pants, shade=False)
        c.R(lx - 0.3 * k, 19 * k - lift, 3.4 * k, 2 * k, shoes, shade=False)
        c.R(lx, 19 * k - lift, _r(k), _r(k), light(shoes, 0.3), shade=False)
    # туловище
    top, bot = 13 * k + bob, 18 * k
    c.P([(cx - 3.6 * k, top), (cx + 3.6 * k, top), (cx + 4.2 * k, bot), (cx - 4.2 * k, bot)], shirt)
    if belt:
        c.R(cx - 4.2 * k, 17 * k, 8.4 * k, _r(k), belt, shade=False)
    # руки
    for sx, sw in ((-1, ARM_L[i]), (1, ARM_R[i])):
        sw = 0 if idle else sw * _r(k * 0.8)
        ax = cx + sx * 4.9 * k - 1 * k
        c.R(ax, 14 * k + bob + sw, 2 * k, 3 * k, sleeves or shirt, shade=False)
        c.R(ax, 16.5 * k + bob + sw, 2 * k, _r(k * 1.4), skin, shade=False)
    for acc in accents:
        acc(c, cx, bob, i, k)
    # голова
    hy = 7.4 * k + bob
    rx, ry = 7.0 * k * head_k, 6.4 * k * head_k
    S = ell_set(cx, hy, rx, ry)
    c.paint(S, skin)
    if hair_style and hair:
        if hair_style == "short":
            c.paint({p for p in S if p[1] < hy - 2.6 * k}, hair)
            for sx in (-1, 1):
                c.R(cx + sx * 6.6 * k - 0.5 * k, hy - 2 * k, _r(k), 4 * k, hair, shade=False)
        elif hair_style == "mop":
            c.paint({p for p in S if p[1] < hy - 1.6 * k}, hair)
            for x in (-5, -2, 1, 4):
                c.R(cx + x * k, hy - 2.4 * k, 2 * k, 2 * k, hair, shade=False)
            c.R(cx - 7 * k, hy - 2 * k, _r(k), 5 * k, hair, shade=False)
            c.R(cx + 6 * k, hy - 2 * k, _r(k), 5 * k, hair, shade=False)
        elif hair_style == "spiky":
            c.paint({p for p in S if p[1] < hy - 3 * k}, hair)
            for x in (-5.5, -2.5, 0.5, 3.5):
                c.P([(cx + x * k, hy - 3 * k), (cx + (x + 1.5) * k, hy - 7.6 * k), (cx + (x + 3) * k, hy - 3 * k)], hair, shade=False)
        elif hair_style == "gray":
            c.paint({p for p in S if p[1] < hy - 2.4 * k}, hair)
            for sx in (-1, 1):
                c.R(cx + sx * 6.6 * k - 0.5 * k, hy - 2 * k, _r(k), 5 * k, hair, shade=False)
        elif hair_style == "bald_ring":
            for sx in (-1, 1):
                c.R(cx + sx * 6.6 * k - 0.5 * k, hy - 1 * k, _r(k), 3 * k, hair, shade=False)
    _face(c, cx, hy, k, eyes, skin, mouth, blush, tears, look=look, brow=brow)
    if post:
        post(c, cx, hy, bob, i, k)
    return c


def finish(c, k=1.0):
    return c.outlined()


# ---------- герои ----------
def _plaid(c, cx, bob, i, k):
    for y in range(int(14 * k) + bob, int(18 * k)):
        for x in range(int(cx - 3.6 * k), int(cx + 4 * k)):
            if (x + y) % 3 == 0:
                c.px(x, y, (128, 30, 40))


def _lumberjack_post(c, cx, hy, bob, i, k):
    S = {p for p in ell_set(cx, hy, 7.0 * k, 6.4 * k) if p[1] >= hy + 1.6 * k}
    c.paint(S, (130, 78, 42))
    c.R(cx - 2 * k, hy + 3 * k, 4 * k, _r(k), light((130, 78, 42), 0.3), shade=False)
    c.R(cx - 1.5 * k, hy + 1.2 * k, 3 * k, _r(k), (40, 14, 18), shade=False)
    c.R(cx - 8 * k, hy - 3.4 * k, 16 * k, 2 * k, (150, 36, 40), shade=False)     # отворот шапки
    c.R(cx - 6 * k, hy - 6.8 * k, 12 * k, _r(k * 3.4), (196, 52, 52))
    # глаза поверх бороды
    for sx in (-1, 1):
        c.eye(cx + sx * 2.9 * k, hy + 0.5 * k, 2.1 * k, 2.4 * k)


def hero(char_id, f=0, idle=False):
    """Кадр героя без контура (масштаб Тома — 1.5, нативно)."""
    if char_id == "rob":
        return human(f, hair=(150, 96, 60), hair_style="mop", shirt=(80, 140, 240), pants=(58, 62, 110), tears=True, idle=idle)
    if char_id == "lumberjack":
        c = human(f, hair=None, shirt=(205, 55, 55), pants=(58, 62, 110), shoes=(70, 44, 30), accents=(_plaid,),
                  idle=idle, blush=False, mouth=None, eyes=None, post=_lumberjack_post)
        return c
    if char_id == "tom":
        return human(f, k=1.5, hair=(70, 46, 34), hair_style="short", shirt=(72, 150, 92), pants=(60, 52, 70),
                     shoes=(50, 36, 34), idle=idle, mouth="grin")

    if char_id == "bigshot":
        def tie(c, cx, bob, i, k):
            c.R(cx - 0.5, 14 + bob, 2, 4, (255, 215, 70), shade=False)
            c.R(cx - 0.5, 18, 2, 1, (255, 215, 70), shade=False)
        return human(f, hair=(32, 30, 44), hair_style="short", shirt=(44, 46, 70), pants=(34, 34, 50), shoes=(20, 18, 24),
                     eyes="shades", accents=(tie,), idle=idle, blush=False, mouth="line")
    if char_id == "glitch":
        return human(f, skin=(255, 140, 232), hair=(255, 240, 90), hair_style="spiky", shirt=(60, 255, 220), pants=(60, 80, 200),
                     shoes=(255, 70, 200), idle=idle, mouth="grin")
    if char_id == "devil":
        def horns(c, cx, hy, bob, i, k):
            for sx in (-1, 1):
                c.P([(cx + sx * 3.6, hy - 4.2), (cx + sx * 4.4, hy - 9.4), (cx + sx * 7.6, hy - 8.4), (cx + sx * 6.8, hy - 3.4)], (255, 232, 180))

        def tail(c, cx, bob, i, k):
            sway = (0, 1, 2, 1)[i]
            c.L(cx - 4, 18, cx - 7, 17 - sway, (190, 34, 44), 1)
            c.L(cx - 7, 17 - sway, cx - 8, 15 - sway, (190, 34, 44), 1)
            c.P([(cx - 9, 15 - sway), (cx - 7, 15 - sway), (cx - 8, 13 - sway)], (255, 90, 80), shade=False)
        return human(f, skin=(216, 62, 56), hair=(30, 18, 22), hair_style="short", shirt=(124, 22, 32), pants=(60, 14, 30),
                     shoes=(30, 14, 18), belt=(255, 190, 50), idle=idle, mouth="grin", eyes="glow", blush=False,
                     pre=tail, post=horns)
    raise KeyError(char_id)


# ---------- людские враги ----------
def _cap(col, badge=None):
    def post(c, cx, hy, bob, i, k):
        c.paint({p for p in ell_set(cx, hy, 7.2 * k, 6.6 * k) if p[1] < hy - 2.2 * k}, col)
        c.R(cx - 1 * k, hy - 3.4 * k, 9 * k, _r(k * 1.4), dark(col, 0.45), shade=False)         # козырёк
        if badge:
            c.R(cx - 1 * k, hy - 5.2 * k, 2 * k, 2 * k, badge, shade=False)
    return post


def mailman(f):
    def bag(c, cx, bob, i, k):
        c.R(cx - 8 * k, 15 * k, 4 * k, 4 * k, (176, 52, 60))
        c.L(cx - 5.2 * k, 14 * k, cx + 3 * k, 18.5 * k, (236, 226, 190), 1)
        c.R(cx + 5 * k, 15 * k + ARM_R[i], 4, 3, (250, 246, 232), shade=False)
        c.px(cx + 6, 16 + ARM_R[i], (200, 60, 60))
    return human(f, hair=None, hair_style=None, shirt=(72, 104, 196), pants=(58, 60, 92), shoes=(40, 36, 52), accents=(bag,),
                 post=lambda c, cx, hy, bob, i, k: _cap((60, 92, 186))(c, cx, hy, bob, i, k), brow=True, eyes="big", mouth="frown")


def neighbor(f):
    return human(f, hair=(132, 92, 60), hair_style="short", shirt=(232, 152, 72), pants=(92, 92, 132), shoes=(60, 44, 40),
                 eyes="angry", mouth="shout", blush=False)


def cop(f):
    def gun(c, cx, bob, i, k):
        c.R(cx + 5, 15 + bob + ARM_R[i], 5, 2, (70, 72, 86), shade=False)
        c.R(cx + 5, 16 + bob + ARM_R[i], 2, 2, (50, 52, 64), shade=False)
    return human(f, skin=(150, 226, 120), hair=None, hair_style=None, shirt=(52, 72, 134), pants=(40, 42, 74), shoes=(24, 24, 36),
                 eyes="red", mouth="grin", blush=False, accents=(gun,),
                 post=lambda c, cx, hy, bob, i, k: _cap((36, 46, 104), (255, 215, 70))(c, cx, hy, bob, i, k))


def soldier(f):
    c = Canvas(9, 9)
    bob = BOB[f % 4]
    c.E(4.5, 3.4 + bob, 3.6, 3.2, (96, 150, 78))
    c.R(2, 3 + bob, 5, 2, (232, 190, 160), shade=False)
    c.px(3, 3 + bob, OUT)
    c.px(6, 3 + bob, OUT)
    c.R(2, 5 + bob, 5, 3, (70, 120, 70))
    c.R(2, 8, 2, 1, (40, 30, 30), shade=False)
    c.R(5, 8, 2, 1, (40, 30, 30), shade=False)
    return c


def landlord(f):
    """Домовладелец (мини-босс): злой мужчина в халате, k=1.45."""
    def robe(c, cx, bob, i, k):
        c.R(cx - 4.4 * k, 17 * k, 8.8 * k, _r(k * 1.2), (110, 28, 44), shade=False)
        c.P([(cx - 1.4 * k, 13 * k + bob), (cx + 1.4 * k, 13 * k + bob), (cx, 17 * k)], (238, 228, 210), shade=False)
    return human(f, k=1.45, skin=SKIN, hair=(208, 208, 214), hair_style="gray", shirt=(156, 52, 64), pants=(236, 190, 160),
                 shoes=(96, 74, 62), eyes="angry", mouth="shout", blush=False, accents=(robe,), sleeves=(156, 52, 64))


def angel(f, idle=False):
    """Герой-Ангел: белые одежды, нимб и крылья, взмахи при ходьбе."""
    i = 0 if idle else f % 4
    c = Canvas(34, 26)
    ox = 8
    flap = (0, 2, 3, 1)[i]
    for sx in (-1, 1):
        cx0 = ox + 9 + sx * 3
        pts = [(cx0, 11), (cx0 + sx * 8, 3 + flap), (cx0 + sx * 8.5, 8 + flap), (cx0 + sx * 7, 13 + flap // 2), (cx0 + sx * 2, 16)]
        c.P(pts, (250, 250, 255))
        for t in (0.35, 0.65):
            c.L(cx0 + sx * 2, 12, cx0 + sx * (3 + 5.5 * t), 7 + flap * t + 3, (200, 210, 235), 1)
    body = human(f, hair=(255, 224, 120), hair_style="mop", shirt=(250, 250, 255), pants=(236, 238, 250), shoes=(255, 240, 200),
                 idle=idle, mouth="line")
    c.blit(body, ox, 4)
    cxh = ox + 9
    c.flat(ell_set(cxh, 3.0 + BOB[i], 5, 1.7), (255, 216, 90))
    c.flat(ell_set(cxh, 3.0 + BOB[i], 3, 0.6), None) if False else None
    for x in range(cxh - 3, cxh + 3):
        c.px(x, 3 + BOB[i], (255, 244, 170)) if x in (cxh - 3, cxh + 2) else None
    return c


def soul(f):
    """Душа: призрак без рук и ног, чёрные пустые глаза; рваный низ колышется."""
    i = f % 4
    c = Canvas(14, 22)
    float_y = (0, 1, 1, 0)[i]
    white, shade = (248, 250, 255), (206, 216, 242)
    c.E(7, 7 + float_y, 6, 6.2, white)
    c.R(1, 8 + float_y, 12, 8, white, shade=False)
    for k_, x in enumerate((1, 4, 7, 10)):
        h = 3 + ((k_ + i) % 2) * 2
        c.P([(x, 15 + float_y), (x + 3, 15 + float_y), (x + 1.5, 15 + float_y + h)], white, shade=False)
    c.R(10, 8 + float_y, 3, 7, shade, shade=False)
    for sx in (-1, 1):
        c.E(7 + sx * 2.6, 7 + float_y, 1.6, 2.4, (4, 2, 8), shade=False)
    c.R(5, 12 + float_y, 4, 1 + (i % 2), (4, 2, 8), shade=False)
    return c
