"""Обычные враги и существа: животные, предметы-мутанты, небесные и адские обитатели. Каждая функция — кадр f (0..3)."""
import math

from .canvas import Canvas, ell_set, rect_set, poly_set, dark, light, mix, OUT

EYE_W = (250, 246, 240)
BOB4 = (0, -1, 0, -1)


def quad(f, *, body, belly=None, ear=None, eye=(130, 240, 90), snout=None, tail=None, W=22, H=14, fangs=True, hell=False):
    """Четвероногий (смотрит вправо): собаки, адская гончая."""
    c = Canvas(W, H)
    i = f % 4
    bob = (0, -1, 0, -1)[i]
    lift = ((1, 0, 0, 1), (0, 0, 0, 0), (0, 1, 1, 0), (0, 0, 0, 0))[i]
    for k_, x in enumerate((4, 7, 12, 15)):
        c.R(x, 9 - lift[k_], 2, 4 + lift[k_] * 0, dark(body, 0.25) if k_ in (1, 3) else body, shade=False)
        c.R(x, 12 - lift[k_], 3, 1, dark(body, 0.5), shade=False)
    c.L(4, 6 + bob, 1, 3 + (i % 2) * 2, tail or body, 2)                      # хвост виляет
    c.E(9, 7 + bob, 6.4, 3.8, body)
    if belly:
        c.R(5, 9 + bob, 8, 1, belly, shade=False)
    c.E(15.5, 5 + bob, 4.2, 3.6, body)
    c.E(19, 6.6 + bob, 2.6, 1.8, snout or light(body, 0.25), shade=False)
    c.R(21, 6 + bob, 1, 1, OUT, shade=False)
    c.P([(13, 2.5 + bob), (15, 0 + bob), (16.5, 3 + bob)], ear or dark(body, 0.4), shade=False)
    c.eye(16.5, 4.6 + bob, 1.8, 2.0, iris=eye, white=(250, 246, 220))
    if fangs:
        c.px(19, 8 + bob, (255, 255, 250))
        c.px(21, 8 + bob, (255, 255, 250))
    return c


def dog(f):
    c = quad(f, body=(158, 114, 72), belly=(214, 180, 130), ear=(98, 66, 44), eye=(120, 240, 80))
    c.R(7, 3 + BOB4[f % 4], 3, 2, (120, 220, 90), shade=False)      # зелёный мутировавший нарост
    c.px(8, 2 + BOB4[f % 4], (200, 255, 150))
    c.px(20, 9 + BOB4[f % 4], (120, 240, 90))                          # слюна
    return c


def hellhound(f):
    i = f % 4
    c = quad(f, body=(66, 34, 34), belly=(110, 50, 40), ear=(255, 120, 40), eye=(255, 224, 80), snout=(96, 52, 46), hell=True)
    bob = (0, -1, 0, -1)[i]
    for k_, x in enumerate((6, 9, 12)):                                   # огненная грива вдоль спины
        h = 3 + ((k_ + i) % 3)
        c.P([(x, 4 + bob), (x + 1.5, 4 - h + bob), (x + 3, 4 + bob)], (255, 130, 40), shade=False)
        c.P([(x + 0.8, 4 + bob), (x + 1.5, 4 - h + 2 + bob), (x + 2.3, 4 + bob)], (255, 220, 90), shade=False)
    return c


def rat(f):
    i = f % 4
    c = Canvas(18, 11)
    bob = (0, -1, 0, -1)[i]
    for k_, x in enumerate((5, 10)):
        l = ((1, 0, 0, 1), (0, 1, 1, 0))[k_][i]
        c.R(x, 7 - l, 2, 3, (92, 92, 104), shade=False)
    wag = (0, 1, 2, 1)[i]
    c.L(3, 6 + bob, 0, 8 - wag, (232, 160, 176), 1)
    c.L(0, 8 - wag, 0, 5 - wag, (232, 160, 176), 1)
    c.E(8, 5.5 + bob, 5.4, 3.4, (126, 126, 140))
    c.P([(11, 3 + bob), (17, 5.5 + bob), (11, 8 + bob)], (150, 150, 164))
    c.E(10, 2.2 + bob, 1.8, 1.8, (240, 170, 184), shade=False)
    c.eye(12, 4 + bob, 1.4, 1.6, iris=(120, 255, 70), white=(230, 255, 210))
    c.px(16, 5 + bob, (240, 150, 170))
    c.px(14, 7 + bob, (255, 255, 250))
    return c


def bird(f):
    """Ворона (жёлтая птица): взмахи крыльев."""
    i = f % 4
    c = Canvas(20, 16)
    wing = (-4, -1, 3, 0)[i]
    body_y = 8 + (0, 1, 1, 0)[i]
    for sx in (-1, 1):
        x0 = 10 + sx * 3
        c.P([(x0, body_y - 1), (x0 + sx * 8, body_y - 2 + wing), (x0 + sx * 7, body_y + 1 + wing), (x0 + sx * 3, body_y + 3)], (246, 214, 84))
        c.L(x0 + sx * 1, body_y, x0 + sx * 6, body_y - 1 + wing, (214, 160, 50), 1)
    c.E(10, body_y, 5.4, 4.6, (252, 226, 96))
    c.E(10, body_y + 2, 3.4, 1.8, (255, 246, 190), shade=False)
    c.P([(8, body_y - 4), (10, body_y - 7), (12, body_y - 4)], (230, 180, 50), shade=False)            # хохолок
    c.P([(9, body_y + 0.5), (11, body_y + 0.5), (10, body_y + 3)], (255, 150, 50), shade=False)         # клюв
    for sx in (-1, 1):
        c.eye(10 + sx * 2.6, body_y - 1.4, 1.6, 1.9, iris=(150, 20, 30))
    c.R(7, body_y + 4, 1, 2, (230, 130, 50), shade=False)
    c.R(12, body_y + 4, 1, 2, (230, 130, 50), shade=False)
    return c


def bush(f):
    """Куст-прыгун: приседает и вытягивается."""
    i = f % 4
    sq = (0, 2, 0, -1)[i]
    w, h = 8 + sq * 0.5, 6 - sq * 0.5
    c = Canvas(20, 16)
    base_y = 14
    G, G2 = (60, 156, 82), (96, 206, 108)
    c.R(6, base_y - 1, 3, 2, (96, 62, 44), shade=False)
    c.R(11, base_y - 1, 3, 2, (96, 62, 44), shade=False)
    cy = base_y - h - 1 + (0 if sq >= 0 else 1)
    c.E(10, cy, w + 1, h, G)
    for dx, dy, r in ((-6, -1, 3.2), (6, -1, 3.2), (-3, -4, 3.4), (3, -4, 3.4), (0, -5, 3)):
        c.E(10 + dx * (1 + sq * 0.04), cy + dy, r, r, G)
    for x, y in ((6, -3), (12, -4), (9, 1), (14, 0), (4, 1)):
        c.px(5 + x * 0.9, cy + y, G2)
    for sx in (-1, 1):
        c.eye(10 + sx * 3, cy + 0.5, 2.0, 2.4, iris=(30, 12, 18))
    c.R(7, cy + 4, 6, 1, (30, 12, 18), shade=False)
    for x in (8, 10, 12):
        c.px(x, cy + 4, (255, 255, 250))
    return c


def face_tree(f):
    """Дерево с лицом: идёт на корнях, ветви качаются."""
    i = f % 4
    c = Canvas(22, 26)
    sway = (0, 1, 0, -1)[i]
    G, G2 = (52, 142, 74), (92, 190, 100)
    lift = ((1, 0), (0, 1), (0, 0), (1, 0))[i] if False else ((0, 0), (1, 0), (0, 0), (0, 1))[i]
    c.R(7, 22 - lift[0], 3, 4, (96, 62, 44), shade=False)
    c.R(12, 22 - lift[1], 3, 4, (96, 62, 44), shade=False)
    c.R(8, 12, 7, 11, (130, 84, 54))
    c.R(9, 12, 2, 10, (166, 112, 72), shade=False)
    for dx, dy, rx, ry in ((0, 0, 10, 7), (-5, 3, 6, 5), (5, 3, 6, 5), (0, -4, 7, 5)):
        c.E(11 + dx + sway * (1 if dy < 1 else 0), 8 + dy, rx, ry, G)
    for x, y in ((6, 4), (12, 3), (16, 7), (8, 9)):
        c.R(x + sway, y, 2, 2, G2, shade=False)
    for sx in (-1, 1):
        c.eye(11 + sx * 2.6, 15, 1.9, 2.3, iris=(30, 12, 18))
    c.R(8, 19, 6, 2, (40, 14, 18), shade=False)
    for x in (9, 11, 13):
        c.px(x, 19, (255, 255, 250))
    for sx, y in ((-1, 14), (1, 15)):                                    # ветки-руки
        c.L(11 + sx * 4, y, 11 + sx * 9, y - 2 + sway * sx, (130, 84, 54), 1)
    return c


def sprinkler(f):
    i = f % 4
    c = Canvas(16, 16)
    c.R(4, 11, 8, 4, (116, 116, 138))
    c.R(3, 14, 10, 1, (80, 80, 100), shade=False)
    c.R(6, 9, 4, 3, (150, 150, 170))
    c.E(8, 7, 5, 4.4, (84, 164, 238))
    arms = ((1, 0), (0.7, 0.7), (0, 1), (-0.7, 0.7))[i]
    for s_ in (-1, 1):
        ex, ey = 8 + arms[0] * 7 * s_, 6 - abs(arms[1]) * 3 + (arms[1] * 2 * s_)
        c.L(8, 6, ex, ey, (216, 240, 255), 1)
        c.px(ex + s_, ey - 1, (255, 255, 255))
    c.eye(8, 7, 2.2, 2.4, iris=(20, 40, 120))
    return c


def cart(f):
    i = f % 4
    c = Canvas(20, 18)
    bob = (0, -1, 0, -1)[i]
    c.R(3, 3 + bob, 14, 8, (160, 166, 184), shade=False)
    c.R(4, 4 + bob, 12, 6, (50, 54, 70), shade=False)
    for x in range(5, 16, 3):
        c.L(x, 4 + bob, x, 9 + bob, (190, 196, 212), 1)
    c.L(3, 3 + bob, 0, 1 + bob, (190, 196, 212), 1)
    c.R(6, 5 + bob, 4, 4, (230, 60, 70))
    c.eye(13, 6 + bob, 1.6, 2.0, iris=(200, 20, 30))
    for x in (5, 14):
        c.E(x, 14, 2.4, 2.4, (54, 54, 66), shade=False)
        a = i * math.pi / 2
        c.px(x + math.cos(a) * 1.4, 14 + math.sin(a) * 1.4, (190, 190, 206))
    return c


def drone(f):
    i = f % 4
    c = Canvas(22, 14)
    bob = (0, 1, 0, 1)[i]
    c.E(11, 7 + bob, 5.4, 3.6, (96, 108, 98))
    c.R(9, 10 + bob, 4, 2, (64, 72, 66), shade=False)
    for sx in (-1, 1):
        x = 11 + sx * 7
        c.L(11 + sx * 4, 5 + bob, x, 3 + bob, (170, 176, 190), 1)
        span = (6, 3, 5, 2)[i]
        c.L(x - span, 2 + bob, x + span, 2 + bob, (226, 230, 240), 1)
    c.E(11, 7 + bob, 2.4, 2.2, (255, 74, 74), shade=False)
    c.px(10, 6 + bob, (255, 220, 200))
    return c


def car(f):
    i = f % 4
    c = Canvas(30, 18)
    bob = (0, -1, 0, -1)[i]
    c.R(2, 6 + bob, 26, 8, (250, 204, 56), strength=1.0)
    c.R(8, 2 + bob, 14, 6, (250, 204, 56))
    c.R(10, 3 + bob, 5, 4, (150, 214, 248), shade=False)
    c.R(16, 3 + bob, 5, 4, (150, 214, 248), shade=False)
    c.R(25, 7 + bob, 4, 3, (255, 255, 240), shade=False)
    c.R(2, 8 + bob, 2, 2, (230, 40, 40), shade=False)
    jaw = (0, 2, 0, 2)[i]
    c.R(15, 11 + bob, 13, 2 + jaw // 2, (40, 8, 14), shade=False)
    for x in range(16, 28, 2):
        c.px(x, 11 + bob, (255, 255, 250))
        c.px(x, 12 + bob + jaw // 2, (255, 255, 250))
    for x in (8, 22):
        c.E(x, 14, 3.4, 3.4, (40, 40, 52), shade=False)
        a = i * math.pi / 2
        c.px(x + math.cos(a) * 1.6, 14 + math.sin(a) * 1.6, (180, 180, 196))
        c.px(x - math.cos(a) * 1.6, 14 - math.sin(a) * 1.6, (180, 180, 196))
    for sx in (24,):
        c.eye(sx, 5 + bob, 1.6, 1.8, iris=(220, 24, 30))
    return c


def tvmon(f):
    i = f % 4
    c = Canvas(20, 22)
    bob = (0, -1, 0, -1)[i]
    c.R(2, 4 + bob, 16, 13, (92, 92, 116))
    c.R(3, 5 + bob, 11, 10, (24, 26, 40), shade=False)
    cols = ((255, 80, 80), (255, 220, 70), (90, 220, 120), (90, 160, 255))
    for k_ in range(4):
        c.R(3 + k_ * 2.7 + (1 if i % 2 else 0) * 0, 5 + bob, 3, 7, cols[(k_ + i) % 4], shade=False)
    c.R(3, 12 + bob, 11, 3, (24, 26, 40), shade=False)
    for x in range(3, 14, 2):
        c.px(x + (i % 2), 13 + bob, (200, 200, 210))
    c.R(15, 6 + bob, 2, 3, (60, 60, 76), shade=False)
    c.px(15, 11 + bob, (230, 60, 70))
    c.L(7, 4 + bob, 4 - (i % 2) * 2, 0, (214, 214, 224), 1)
    c.L(11, 4 + bob, 14 + (i % 2) * 2, 0, (214, 214, 224), 1)
    lift = ((0, 1), (1, 0))[i % 2]
    c.R(5, 17 + bob - lift[0], 3, 4, (60, 60, 76), shade=False)
    c.R(12, 17 + bob - lift[1], 3, 4, (60, 60, 76), shade=False)
    return c


def eye_swarm(f):
    """Летающий глаз: мигает и косится, крохотные жилки."""
    i = f % 4
    c = Canvas(15, 15)
    bob = (0, -1, 0, 1)[i]
    c.E(7.5, 7.5 + bob, 6.4, 6.4, (252, 248, 244))
    look = ((0, 0), (1, 0), (0, 1), (-1, 0))[i]
    c.E(7.5 + look[0], 8 + bob + look[1], 3.6, 3.6, (214, 24, 66), shade=False)
    c.E(7.5 + look[0], 8 + bob + look[1], 1.6, 1.6, (20, 8, 16), shade=False)
    c.px(6 + look[0], 6.5 + bob + look[1], (255, 255, 255))
    for x, y, ex, ey in ((1, 2, 3, 4), (13, 2, 11, 4), (1, 10, 3, 9), (13, 11, 11, 9)):
        c.L(x, y + bob, ex, ey + bob, (255, 120, 190), 1)
    if i == 3:                                                           # моргание
        c.R(1, 5 + bob, 13, 3, (200, 140, 150), shade=False)
    return c


def fragment(f):
    i = f % 4
    c = Canvas(22, 24)
    j = ((0, 0), (1, 0), (0, 1), (-1, 0))[i]
    ox, oy = 1 + j[0], 1 + j[1]
    c.P([(ox + 2, oy + 5), (ox + 15, oy + 1), (ox + 19, oy + 9), (ox + 17, oy + 21), (ox + 1, oy + 19)], (156, 156, 174))
    for k_, (x, y) in enumerate(((4, 6), (9, 5), (14, 7), (4, 11), (9, 11), (14, 12), (5, 16), (10, 16), (14, 17))):
        lit = (k_ + i) % 3
        col = (255, 236, 126) if lit else (96, 204, 255)
        c.R(ox + x, oy + y, 3, 3, col, shade=False)
    c.E(ox + 16, oy + 4, 3.2, 3.2, (56, 160, 84))
    c.eye(ox + 10, oy + 14, 2.0, 2.2, iris=(230, 20, 60))
    return c


def glitchling(f):
    i = f % 4
    c = Canvas(20, 20)
    jx = ((0, 2), (2, -1), (-1, 1), (1, 0))[i]
    c.R(3 + jx[0], 2, 9, 14, (60, 255, 220))
    c.R(7 + jx[1], 4, 9, 14, (255, 72, 212))
    for sx in (-1, 1):
        c.eye(8 + sx * 3 + jx[0], 8, 1.7, 2.0, iris=(10, 10, 20))
    c.R(7, 12, 6, 1, (20, 10, 28), shade=False)
    for k_ in range(3):
        y = 3 + ((k_ * 5 + i * 3) % 14)
        c.R(0 + (k_ * i) % 3, y, 6 + k_ * 2, 1, (255, 240, 90), shade=False)
    return c


def ember(f):
    i = f % 4
    c = Canvas(18, 22)
    sway = (0, 1, 0, -1)[i]
    tall = (0, 1, 2, 1)[i]
    c.P([(9 + sway, 1 - tall * 0.5), (15, 11), (13, 18), (5, 18), (3, 11)], (255, 112, 34))
    c.P([(9 + sway * 0.5, 5), (13, 11), (11, 17), (7, 17), (5, 11)], (255, 196, 60), shade=False)
    for sx in (-1, 1):
        c.eye(9 + sx * 2.5, 12, 1.6, 2.0, iris=(60, 10, 8), white=(255, 250, 220))
    c.R(7, 16, 4, 1, (120, 30, 14), shade=False)
    c.px(2, 6 - tall, (255, 190, 80))
    c.px(15, 5 + tall, (255, 150, 50))
    return c


def fire_imp(f):
    i = f % 4
    c = Canvas(22, 20)
    flap = (0, 2, 3, 1)[i]
    for sx in (-1, 1):
        c.P([(11 + sx * 3, 9), (11 + sx * 10, 4 + flap), (11 + sx * 10, 10 + flap), (11 + sx * 4, 13)], (255, 150, 40))
    c.E(11, 11, 4.4, 4.4, (214, 56, 46))
    c.E(11, 6, 5, 4.4, (232, 72, 56))
    c.P([(6, 5), (5, 0), (8.5, 3.5)], (255, 232, 130), shade=False)
    c.P([(16, 5), (17, 0), (13.5, 3.5)], (255, 232, 130), shade=False)
    for sx in (-1, 1):
        c.eye(11 + sx * 2.4, 6, 1.6, 1.8, iris=(230, 20, 20), white=(255, 250, 200))
    c.R(9, 9, 4, 1, (60, 8, 10), shade=False)
    c.L(11, 14, 15, 17 + (i % 2), (214, 56, 46), 1)
    c.px(16, 17 + (i % 2), (255, 190, 60))
    c.R(8, 15, 2, 3, (160, 40, 40), shade=False)
    c.R(12, 15, 2, 3, (160, 40, 40), shade=False)
    return c


def magma_golem(f):
    i = f % 4
    c = Canvas(28, 28)
    stomp = (0, 1, 0, -1)[i]
    lift = ((0, 1), (0, 0), (1, 0), (0, 0))[i]
    R, R2, LAVA = (64, 54, 66), (92, 78, 96), (255, 120, 30)
    c.R(6, 22 - lift[0], 6, 5, R)
    c.R(16, 22 - lift[1], 6, 5, R)
    c.R(5, 8 + stomp, 18, 15, R)
    c.R(8, 2 + stomp, 12, 8, R2)
    c.R(0, 9 + stomp - (i % 2), 6, 11, R)
    c.R(22, 9 + stomp + (i % 2), 6, 11, R)
    for pts in (((7, 12), (12, 17), (18, 14)), ((9, 21), (15, 19), (21, 20)), ((3, 12), (4, 17), (2, 19))):
        for a, b in zip(pts, pts[1:]):
            c.L(a[0], a[1] + stomp, b[0], b[1] + stomp, LAVA if (i + a[0]) % 3 else (255, 200, 70), 1)
    for sx in (-1, 1):
        c.R(14 + sx * 3 - 1, 5 + stomp, 2, 2, (255, 224, 90), shade=False)
    return c


def idol(f):
    i = f % 4
    c = Canvas(18, 24)
    c.R(4, 3, 10, 17, (80, 70, 82))
    c.R(2, 18, 14, 5, (56, 48, 58))
    glow = ((255, 130, 30), (255, 190, 60), (255, 130, 30), (255, 90, 20))[i]
    c.R(6, 8, 2, 3, glow, shade=False)
    c.R(10, 8, 2, 3, glow, shade=False)
    c.R(6, 14, 6, 2, glow, shade=False)
    c.P([(9, 0 - (i % 2)), (12, 4), (6, 4)], glow, shade=False)
    c.L(4, 6, 6, 5, light((80, 70, 82), 0.3), 1)
    return c


def imp_mini(f):
    i = f % 4
    c = Canvas(18, 16)
    flap = (0, 2, 3, 1)[i]
    for sx in (-1, 1):
        c.P([(9 + sx * 2, 8), (9 + sx * 8, 3 + flap), (9 + sx * 8, 9 + flap), (9 + sx * 3, 11)], (156, 32, 34))
    c.E(9, 8, 4.8, 4.4, (224, 62, 52))
    c.P([(4, 5), (3, 0), (7, 3)], (255, 232, 130), shade=False)
    c.P([(14, 5), (15, 0), (11, 3)], (255, 232, 130), shade=False)
    for sx in (-1, 1):
        c.eye(9 + sx * 2.4, 8, 1.5, 1.8, iris=(220, 20, 20), white=(255, 250, 210))
    return c


def cherub(f):
    i = f % 4
    c = Canvas(20, 18)
    flap = (0, 2, 3, 1)[i]
    bob = (0, 1, 1, 0)[i]
    for sx in (-1, 1):
        c.P([(10 + sx * 3, 8 + bob), (10 + sx * 9, 3 + flap + bob), (10 + sx * 9.5, 9 + flap + bob), (10 + sx * 4, 11 + bob)], (250, 250, 255))
        c.L(10 + sx * 4, 8 + bob, 10 + sx * 8, 6 + flap + bob, (190, 204, 232), 1)
    c.R(7, 11 + bob, 6, 4, (255, 214, 184))
    c.E(10, 8 + bob, 5, 4.8, (255, 220, 192))
    for sx in (-1, 1):
        c.eye(10 + sx * 2.2, 8.5 + bob, 1.4, 1.8)
    c.R(9, 11 + bob, 2, 1, (214, 90, 100), shade=False)
    c.flat(ell_set(10, 2.2 + bob, 3.6, 1.2), (255, 220, 90))
    c.flat(ell_set(10, 2.2 + bob, 1.8, 0.4), None) if False else None
    return c


def cloudling(f):
    i = f % 4
    c = Canvas(20, 16)
    pf = (0, 1, 0, -1)[i]
    cloud, shade_ = (222, 228, 242), (168, 178, 208)
    c.E(10, 8, 8.4, 4.2, shade_)
    c.E(6 + pf, 6, 4.4, 4, cloud)
    c.E(13 - pf, 5.6, 4.6, 4, cloud)
    c.E(10, 7, 8, 4, cloud)
    for sx in (-1, 1):
        c.L(10 + sx * 2, 6, 10 + sx * 4, 7, OUT, 1)
        c.px(10 + sx * 3, 8, OUT)
    bolt = (0, 1, 0, 1)[i]
    c.P([(9, 11), (7, 14 + bolt), (9, 14 + bolt), (8, 16 + bolt)], (255, 232, 80), shade=False)
    return c


def halo_ring(f):
    i = f % 4
    c = Canvas(18, 18)
    c.E(9, 9, 8, 8, (255, 214, 82))
    c.E(9, 9, 4.4, 4.4, None) if False else None
    for x, y in ell_set(9, 9, 4.6, 4.6):
        c.p[y][x] = None
    c.E(9, 9, 2, 2, (255, 252, 240), shade=False)
    c.px(9, 9, OUT)
    a = i * math.pi / 2
    for k_ in range(4):
        aa = a + k_ * math.pi / 2
        c.px(9 + math.cos(aa) * 7.5, 9 + math.sin(aa) * 7.5, (255, 248, 180))
    return c


def dove(f):
    i = f % 4
    c = Canvas(20, 14)
    wing = (-3, 0, 3, 0)[i]
    c.P([(5, 5), (8, 0 - wing * 0.3 + (wing < 0) * 0), (12, 5)], (226, 232, 248))
    c.P([(4, 6), (0, 9 + wing), (6, 8)], (250, 250, 255))
    c.E(9, 7, 5.6, 3.6, (252, 252, 255))
    c.E(15, 5, 3, 2.8, (252, 252, 255))
    c.P([(17.5, 4.5), (20, 5.6), (17.5, 6.6)], (255, 172, 60), shade=False)
    c.eye(15.3, 4.4, 1.2, 1.4)
    c.P([(4, 6), (7, 3 + wing), (10, 6)], (238, 242, 255), shade=False)
    return c


def trumpeter(f):
    i = f % 4
    c = Canvas(22, 24)
    flap = (0, 2, 3, 1)[i]
    bob = (0, 1, 1, 0)[i]
    for sx in (-1, 1):
        c.P([(11 + sx * 3, 8 + bob), (11 + sx * 9, 3 + flap + bob), (11 + sx * 9.5, 11 + flap + bob), (11 + sx * 4, 13 + bob)], (222, 236, 255))
    c.P([(7, 10 + bob), (15, 10 + bob), (17, 22 + bob), (5, 22 + bob)], (252, 252, 255))
    c.E(11, 6 + bob, 4.2, 4.2, (255, 218, 188))
    for sx in (-1, 1):
        c.eye(11 + sx * 1.8, 6.5 + bob, 1.2, 1.6)
    c.flat(ell_set(11, 1.4 + bob, 3.6, 1.2), (255, 220, 90))
    c.L(10, 12 + bob, 18, 8 + bob, (255, 206, 72), 2)
    c.P([(16, 5 + bob), (21, 7 + bob), (21, 12 + bob), (16, 10 + bob)], (255, 206, 72))
    return c


def stone_angel(f):
    i = f % 4
    c = Canvas(22, 26)
    sway = (0, 0, 1, 0)[i]
    st, dk = (176, 178, 192), (124, 126, 144)
    for sx in (-1, 1):
        c.P([(11 + sx * 2, 8), (11 + sx * 10, 3 - sway), (11 + sx * 10, 17), (11 + sx * 3, 19)], dk)
    c.P([(6, 10), (16, 10), (18, 24), (4, 24)], st)
    c.R(7, 2 + sway, 8, 8, (210, 212, 226))
    for sx in (-1, 1):
        c.R(11 + sx * 2 - 0.5, 5 + sway, 2, 2, (96, 196, 255) if (i % 2) else (150, 226, 255), shade=False)
    c.L(8, 13, 7, 22, dk, 1)
    c.L(14, 13, 15, 22, dk, 1)
    return c


def living_spruce(f):
    """Живая ель (мини-босс леса): идёт, иглы качаются."""
    i = f % 4
    c = Canvas(44, 52)
    sway = (0, 1, 0, -1)[i]
    lift = ((0, 1), (1, 0), (0, 1), (1, 0))[i]
    c.R(15, 40 - lift[0], 6, 10, (104, 64, 44), shade=False)
    c.R(24, 40 - lift[1], 6, 10, (104, 64, 44), shade=False)
    c.R(13, 48 - lift[0], 8, 3, (70, 44, 32), shade=False)
    c.R(23, 48 - lift[1], 8, 3, (70, 44, 32), shade=False)
    for pts, col in (([(22 + sway, 1), (9, 19), (35, 19)], (62, 160, 86)),
                     ([(22 + sway, 9), (5, 30), (39, 30)], (50, 142, 74)),
                     ([(22, 18), (2, 43), (42, 43)], (40, 122, 64))):
        c.P(pts, col)
        c.L(pts[0][0], pts[0][1], pts[1][0], pts[1][1], (130, 222, 110), 1)
    for sx in (-1, 1):
        c.eye(22 + sx * 7, 29, 3.2, 3.6, iris=(230, 30, 40), white=(255, 252, 244))
        c.L(22 + sx * 11, 24 - (0 if sx > 0 else 0), 22 + sx * 3.6, 26.4, OUT, 2)
    c.R(15, 35, 15, 5, (34, 10, 16), shade=False)
    for x in range(16, 29, 3):
        c.R(x, 35, 2, 2, (255, 252, 244), shade=False)
        c.R(x + 1, 38, 2, 2, (255, 252, 244), shade=False)
    for x, y, dx, dy in ((9, 16, -5, -2), (35, 16, 5, -2), (5, 28, -6, -1), (39, 28, 6, -1), (3, 40, -5, 1), (41, 40, 5, 1), (22, 1, 0, -4)):
        c.L(x, y, x + dx, y + dy + sway * (1 if dx > 0 else -1), (238, 238, 164), 1)
    return c
