"""Пиксель-арт спрайты, нарисованные кодом (внешние ассеты не нужны)."""
import math
import pygame

K = (34, 24, 48)
PAL = {
    "k": K, "w": (255, 250, 240), "r": (230, 60, 70), "o": (255, 150, 50), "y": (255, 225, 80),
    "g": (120, 215, 100), "G": (52, 150, 76), "b": (80, 140, 240), "p": (220, 120, 200),
    "n": (150, 95, 60), "N": (104, 64, 44), "s": (255, 205, 170), "d": (120, 120, 140),
    "l": (190, 230, 255), "c": (130, 240, 90),
}

PLAYER = [
    "...kkkk...", "..knnnnk..", ".kssssssk.", ".kskssksk.", ".kssssssk.", "..kbbbbk..",
    ".kbbbbbbk.", "ksbbbbbbsk", ".kbbbbbbk.", "..kbkkbk..", "..ksk.ksk.", "..kkk.kkk.",
]
BUSH = [
    "...kkkkkk...", "..kGGGGGGk..", ".kGgGGgGGGGk", "kGGgGGGGgGGk", "kGwkGGGGwkGk", "kGgGGGGGGgGk",
    "kGGGkkkkGGGk", ".kGgGGGGgGk.", "..kkGGGGkk..", "....kkkk....",
]
TREE = [
    "....kkkkkk....", "..kkGGGGGGkk..", ".kGGgGGGGgGGk.", "kGGGGGGGGGGGGk", "kGgGGGGGGGGgGk",
    ".kGGGGGGGGGGk.", "..kkGGGGGGkk..", "....kNNNNk....", "...kNwkNNkwNk.", "...kNNNNNNNNk.",
    "...kNNkkkkNNk.", "...kNNNNNNNNk.", "....kNNNNNNk..", "...kkkkkkkkkk.",
]
BIRD = [
    "............", "k....kk....k", "kk..kyyk..kk", "kyykkwkkyykk", "kyyyyyyyyyyk", ".kyyyoyyyyk.",
    "..kkyyyykk..", "....kookk...", "....kkk.....",
]
ROCK = [
    "................", "......kkkk......", "....kkddddkk....", "...kdddlldddk...", "..kdddlddddddk..",
    "..kddddddddddk..", ".kdddddddddNdk..", ".kddddddddddNdk.", ".kdddddddddddNk.", ".kddddddddddNNk.",
    "..kddddddddNNk..", "..kkdddddNNNkk..", "....kkkkkkkk....", "................", "................", "................",
]
SOLDIER = [
    "..kkk..", ".kGGGk.", ".ksssk.", "..kGk..", ".kGGGk.", "kGGGGGk", ".kk.kk.",
]


def from_rows(rows, palette=PAL):
    w = len(rows[0])
    surf = pygame.Surface((w, len(rows)), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        if len(row) != w:
            raise ValueError(f"строки спрайта разной длины (строка {y})")
        for x, ch in enumerate(row):
            color = palette.get(ch)
            if color:
                surf.set_at((x, y), color)
    return surf


def outlined(surf, color=K):
    """Добавляет 1px контур вокруг непрозрачных пикселей."""
    mask = pygame.mask.from_surface(surf)
    sil = mask.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))
    out = pygame.Surface((surf.get_width() + 2, surf.get_height() + 2), pygame.SRCALPHA)
    for ox, oy in ((0, 1), (2, 1), (1, 0), (1, 2)):
        out.blit(sil, (ox, oy))
    out.blit(surf, (1, 1))
    return out


def silhouette(surf, color=(255, 255, 255)):
    return pygame.mask.from_surface(surf).to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))


def make_lumberjack():
    s = pygame.Surface((40, 44), pygame.SRCALPHA)
    pygame.draw.rect(s, (60, 70, 130), (12, 34, 6, 10))
    pygame.draw.rect(s, (60, 70, 130), (22, 34, 6, 10))
    pygame.draw.rect(s, (200, 50, 50), (8, 16, 24, 20))
    for i in range(0, 24, 6):
        pygame.draw.rect(s, (120, 30, 40), (8 + i, 16, 2, 20))
    for j in range(0, 20, 6):
        pygame.draw.rect(s, (120, 30, 40), (8, 16 + j, 24, 2))
    pygame.draw.rect(s, (255, 205, 170), (13, 6, 14, 12))
    pygame.draw.rect(s, (130, 80, 45), (12, 13, 16, 9))
    pygame.draw.rect(s, (200, 50, 50), (11, 2, 18, 6))
    pygame.draw.rect(s, (255, 255, 255), (15, 9, 3, 3))
    pygame.draw.rect(s, (255, 255, 255), (22, 9, 3, 3))
    pygame.draw.rect(s, (230, 20, 20), (16, 10, 1, 2))
    pygame.draw.rect(s, (230, 20, 20), (23, 10, 1, 2))
    pygame.draw.rect(s, (200, 50, 50), (2, 18, 6, 14))
    pygame.draw.rect(s, (200, 50, 50), (32, 18, 6, 14))
    pygame.draw.circle(s, (190, 195, 210), (36, 26), 8)
    pygame.draw.circle(s, (110, 115, 135), (36, 26), 3)
    for a in range(0, 360, 45):
        x = 36 + math.cos(math.radians(a)) * 9
        y = 26 + math.sin(math.radians(a)) * 9
        pygame.draw.circle(s, (230, 235, 245), (int(x), int(y)), 1)
    return outlined(s)


def _surf(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def make_dog():
    s, d = _surf(16, 12), pygame.draw
    d.ellipse(s, (150, 110, 70), (2, 3, 10, 6))
    d.rect(s, (150, 110, 70), (10, 2, 5, 5))
    d.rect(s, (100, 70, 45), (14, 4, 2, 2))
    d.rect(s, (100, 70, 45), (10, 1, 2, 2))
    d.rect(s, (150, 110, 70), (3, 8, 2, 3))
    d.rect(s, (150, 110, 70), (9, 8, 2, 3))
    d.line(s, (150, 110, 70), (2, 4), (0, 2), 1)
    s.set_at((12, 3), (130, 240, 90))
    s.set_at((6, 5), (130, 240, 90))
    return outlined(s)


def make_mailman():
    s, d = _surf(12, 16), pygame.draw
    d.rect(s, (70, 100, 190), (3, 6, 6, 6))
    d.rect(s, (60, 60, 90), (3, 12, 2, 3))
    d.rect(s, (60, 60, 90), (7, 12, 2, 3))
    d.rect(s, (255, 205, 170), (3, 2, 6, 4))
    d.rect(s, (70, 100, 190), (2, 0, 8, 3))
    d.rect(s, (230, 60, 70), (1, 7, 2, 5))
    d.rect(s, (245, 240, 220), (8, 8, 4, 4))
    s.set_at((4, 4), K)
    s.set_at((7, 4), K)
    return outlined(s)


def make_sprinkler():
    s, d = _surf(12, 12), pygame.draw
    d.rect(s, (110, 110, 130), (3, 8, 6, 3))
    d.circle(s, (80, 160, 235), (6, 6), 4)
    d.rect(s, (200, 230, 255), (6, 1, 2, 4))
    d.rect(s, (200, 230, 255), (1, 6, 4, 2))
    s.set_at((6, 6), (255, 255, 255))
    return outlined(s)


def make_cart():
    s, d = _surf(16, 14), pygame.draw
    d.rect(s, (190, 195, 210), (2, 2, 12, 7), 1)
    for x in range(4, 14, 3):
        d.line(s, (190, 195, 210), (x, 2), (x, 8))
    d.line(s, (190, 195, 210), (0, 1), (2, 2))
    d.circle(s, (60, 60, 70), (4, 11), 2)
    d.circle(s, (60, 60, 70), (12, 11), 2)
    d.rect(s, (230, 60, 70), (4, 4, 3, 3))
    return outlined(s)


def make_neighbor():
    s, d = _surf(12, 16), pygame.draw
    d.rect(s, (230, 150, 70), (3, 6, 6, 6))
    d.rect(s, (90, 90, 130), (3, 12, 2, 3))
    d.rect(s, (90, 90, 130), (7, 12, 2, 3))
    d.rect(s, (255, 205, 170), (3, 1, 6, 5))
    d.rect(s, (130, 90, 60), (3, 0, 6, 2))
    d.rect(s, (230, 20, 20), (4, 3, 1, 1))
    d.rect(s, (230, 20, 20), (7, 3, 1, 1))
    d.rect(s, (230, 150, 70), (1, 7, 2, 4))
    d.rect(s, (230, 150, 70), (9, 7, 2, 4))
    return outlined(s)


def make_neighbor_boss():
    s, d = _surf(44, 44), pygame.draw
    d.rect(s, (80, 80, 120), (13, 33, 7, 10))
    d.rect(s, (80, 80, 120), (23, 33, 7, 10))
    d.rect(s, (235, 150, 70), (9, 15, 26, 20))
    d.rect(s, (200, 110, 40), (9, 25, 26, 3))
    d.rect(s, (255, 205, 170), (14, 3, 16, 14))
    d.rect(s, (140, 95, 60), (13, 1, 18, 5))
    d.rect(s, (255, 255, 255), (16, 8, 5, 4))
    d.rect(s, (255, 255, 255), (24, 8, 5, 4))
    d.rect(s, (230, 20, 20), (18, 9, 2, 2))
    d.rect(s, (230, 20, 20), (26, 9, 2, 2))
    d.rect(s, K, (18, 14, 8, 2))
    d.rect(s, (235, 150, 70), (3, 17, 6, 14))
    d.rect(s, (235, 150, 70), (35, 17, 6, 14))
    d.rect(s, (210, 50, 50), (0, 30, 44, 10))      # газонокосилка перед ним
    d.rect(s, (250, 220, 70), (4, 32, 14, 3))
    d.circle(s, (50, 50, 60), (7, 41), 3)
    d.circle(s, (50, 50, 60), (37, 41), 3)
    d.line(s, (150, 150, 160), (22, 30), (22, 22), 2)
    return outlined(s)


def make_rat():
    s, d = _surf(14, 8), pygame.draw
    d.ellipse(s, (120, 120, 130), (2, 2, 9, 5))
    d.polygon(s, (120, 120, 130), [(10, 2), (14, 4), (10, 6)])
    d.line(s, (200, 150, 160), (2, 4), (0, 6), 1)
    d.rect(s, (230, 170, 180), (7, 0, 2, 2))
    s.set_at((11, 3), (130, 240, 90))
    d.rect(s, (90, 90, 100), (3, 6, 2, 2))
    d.rect(s, (90, 90, 100), (8, 6, 2, 2))
    return outlined(s)


def make_cop():
    s, d = _surf(12, 16), pygame.draw
    d.rect(s, (50, 70, 130), (3, 6, 6, 6))
    d.rect(s, (40, 40, 70), (3, 12, 2, 3))
    d.rect(s, (40, 40, 70), (7, 12, 2, 3))
    d.rect(s, (150, 230, 120), (3, 2, 6, 4))      # мутировавшая зелёная кожа
    d.rect(s, (30, 40, 90), (2, 0, 8, 3))
    d.rect(s, (255, 215, 70), (5, 0, 2, 2))
    d.rect(s, (230, 20, 20), (4, 3, 1, 1))
    d.rect(s, (230, 20, 20), (7, 3, 1, 1))
    d.rect(s, (60, 60, 70), (9, 7, 3, 2))
    return outlined(s)


def make_drone():
    s, d = _surf(16, 10), pygame.draw
    d.ellipse(s, (90, 100, 90), (4, 3, 8, 5))
    d.line(s, (200, 200, 210), (0, 1), (6, 3), 1)
    d.line(s, (200, 200, 210), (16, 1), (10, 3), 1)
    d.rect(s, (255, 70, 70), (7, 5, 2, 2))
    d.rect(s, (60, 70, 60), (6, 8, 4, 2))
    return outlined(s)


def make_car():
    s, d = _surf(24, 14), pygame.draw
    d.rect(s, (245, 200, 50), (1, 4, 22, 7), border_radius=2)
    d.rect(s, (245, 200, 50), (6, 1, 12, 5), border_radius=2)
    d.rect(s, (150, 210, 245), (8, 2, 8, 3))
    d.rect(s, (255, 255, 255), (19, 5, 4, 3))
    d.rect(s, (230, 20, 20), (20, 6, 2, 1))
    for x in range(14, 22, 2):                    # зубы
        d.rect(s, (255, 255, 255), (x, 9, 1, 2))
    d.circle(s, (40, 40, 50), (6, 11), 3)
    d.circle(s, (40, 40, 50), (18, 11), 3)
    return outlined(s)


def make_tvmon():
    s, d = _surf(16, 16), pygame.draw
    d.rect(s, (90, 90, 110), (1, 2, 14, 11))
    for i, col in enumerate(((255, 80, 80), (255, 220, 70), (90, 220, 120), (90, 160, 255))):
        d.rect(s, col, (3 + i * 3, 4, 3, 7))
    d.rect(s, (255, 255, 255), (4, 6, 8, 2))
    d.line(s, (200, 200, 210), (5, 2), (3, 0))
    d.line(s, (200, 200, 210), (10, 2), (12, 0))
    d.rect(s, (60, 60, 70), (4, 13, 3, 2))
    d.rect(s, (60, 60, 70), (9, 13, 3, 2))
    return outlined(s)


def make_mayor():
    s, d = _surf(46, 44), pygame.draw
    d.rect(s, (60, 60, 90), (14, 12, 18, 18))                  # костюм
    d.polygon(s, (230, 60, 70), [(22, 14), (25, 14), (26, 26), (23, 28)])
    d.rect(s, (255, 205, 170), (16, 1, 14, 12))
    d.rect(s, (150, 150, 160), (15, 0, 16, 4))
    d.rect(s, K, (19, 6, 2, 2))
    d.rect(s, K, (26, 6, 2, 2))
    d.rect(s, K, (20, 10, 6, 1))
    d.rect(s, (140, 90, 55), (2, 28, 42, 14))                  # стол
    d.rect(s, (110, 70, 40), (2, 28, 42, 3))
    d.rect(s, (245, 245, 235), (8, 25, 10, 5))                 # документ
    d.line(s, (40, 40, 160), (9, 27), (16, 27))
    return outlined(s)


def make_mayor_desk():
    s, d = _surf(52, 44), pygame.draw
    d.rect(s, (130, 85, 50), (2, 8, 48, 26), border_radius=3)
    d.rect(s, (100, 65, 38), (2, 8, 48, 4))
    d.rect(s, (40, 10, 20), (8, 18, 36, 12))                  # пасть
    for x in range(9, 43, 5):
        d.polygon(s, (255, 255, 240), [(x, 18), (x + 4, 18), (x + 2, 23)])
        d.polygon(s, (255, 255, 240), [(x, 30), (x + 4, 30), (x + 2, 25)])
    d.circle(s, (255, 255, 255), (15, 12), 4)
    d.circle(s, (255, 255, 255), (37, 12), 4)
    d.circle(s, (230, 20, 20), (15, 12), 2)
    d.circle(s, (230, 20, 20), (37, 12), 2)
    for x in (6, 16, 34, 44):
        d.rect(s, (100, 65, 38), (x, 34, 4, 9))
    d.polygon(s, (230, 60, 70), [(24, 0), (28, 0), (30, 9), (22, 9)])   # галстук торчит сверху
    return outlined(s)


def make_mayor_surreal():
    s, d = _surf(48, 48), pygame.draw
    d.ellipse(s, (240, 200, 215), (6, 4, 36, 40))
    d.ellipse(s, (150, 60, 190), (10, 8, 28, 32), 3)
    for i, (ex, ey) in enumerate(((16, 14), (30, 14), (23, 22), (14, 30), (32, 30), (23, 38))):
        d.circle(s, (255, 255, 255), (ex, ey), 4)
        d.circle(s, (120, 30, 170), (ex, ey), 2)
    d.polygon(s, (230, 60, 70), [(22, 0), (26, 0), (30, 12), (18, 12)])
    d.arc(s, K, (14, 24, 20, 14), 3.4, 6.0, 2)
    d.line(s, (255, 205, 170), (6, 24), (0, 14), 3)
    d.line(s, (255, 205, 170), (42, 24), (47, 14), 3)
    return outlined(s)


def make_eye():
    s, d = _surf(12, 12), pygame.draw
    d.circle(s, (255, 255, 255), (6, 6), 5)
    d.circle(s, (210, 20, 60), (6, 6), 3)
    d.circle(s, K, (6, 6), 1)
    d.line(s, (255, 120, 220), (1, 1), (3, 3))
    d.line(s, (255, 120, 220), (11, 1), (9, 3))
    return outlined(s)


def make_fragment():
    s, d = _surf(18, 20), pygame.draw
    d.polygon(s, (150, 150, 165), [(2, 4), (14, 1), (17, 8), (15, 19), (1, 17)])
    for x in (4, 9, 13):
        for y in (5, 10, 15):
            d.rect(s, (255, 235, 120) if (x + y) % 2 else (90, 200, 255), (x, y, 3, 3))
    d.circle(s, (60, 170, 80), (14, 3), 3)                      # кусок дерева на обломке
    d.rect(s, (230, 20, 60), (7, 7, 2, 2))
    return outlined(s)


def make_glitchling():
    s, d = _surf(14, 16), pygame.draw
    d.rect(s, (60, 255, 220), (3, 2, 8, 12))
    d.rect(s, (255, 70, 210), (5, 4, 8, 12))
    d.rect(s, (255, 255, 255), (5, 5, 2, 2))
    d.rect(s, (255, 255, 255), (9, 5, 2, 2))
    d.rect(s, K, (6, 9, 5, 1))
    d.rect(s, (255, 240, 90), (0, 8, 5, 1))
    d.rect(s, (255, 240, 90), (10, 12, 4, 1))
    return outlined(s)


def make_chaos():
    s, d = _surf(64, 64), pygame.draw
    d.polygon(s, (110, 110, 135), [(10, 40), (14, 8), (34, 4), (40, 30), (28, 46)])        # кусок здания
    for x in range(15, 34, 7):
        for y in range(10, 38, 8):
            d.rect(s, (255, 235, 120) if (x + y) % 3 else (90, 200, 255), (x, y, 4, 5))
    d.circle(s, (50, 160, 80), (44, 20), 14)                                                # крона дерева
    d.circle(s, (80, 200, 100), (40, 16), 8)
    d.rect(s, (110, 70, 45), (41, 28, 6, 22))
    d.ellipse(s, (240, 200, 215), (22, 30, 30, 28))                                          # лицо
    d.polygon(s, (230, 70, 190), [(4, 54), (20, 44), (24, 60), (8, 62)])
    d.polygon(s, (60, 230, 200), [(46, 50), (62, 40), (60, 60), (50, 62)])
    d.rect(s, (255, 235, 90), (30, 50, 16, 4))
    d.line(s, (255, 70, 200), (0, 30), (20, 34), 3)
    d.line(s, (60, 255, 210), (44, 60), (63, 46), 3)
    return outlined(s)


def _feather(surf, root, angle_deg, length, width, fill, edge):
    """Одно перо крыла: вытянутый ромб от корня к кончику."""
    ang = math.radians(angle_deg)
    d = pygame.Vector2(math.cos(ang), math.sin(ang))
    n = pygame.Vector2(-d.y, d.x)
    r = pygame.Vector2(root)
    pts = [r + n * (width * 0.3), r + d * (length * 0.55) + n * width, r + d * length, r + d * (length * 0.55) - n * width, r - n * (width * 0.3)]
    pygame.draw.polygon(surf, fill, pts)
    pygame.draw.polygon(surf, edge, pts, 1)


# цвета радужки по фазам: рисуется динамически в Shine.draw (зрачок следит за игроком)
SHINE_IRIS = {1: (80, 150, 255), 2: (235, 150, 40), 3: (195, 60, 225)}


def make_shine(variant=1):
    """THE SHINE — летающий глаз с крыльями и нимбом (без радужки: её рисует босс).
    variant 1 — золотой, 2 — тёмное золото (судья), 3 — искажённый фиолетовый."""
    w, h = 104, 84
    s = _surf(w, h)
    fill = {1: (255, 244, 205), 2: (232, 200, 120), 3: (196, 150, 205)}[variant]
    edge = {1: (205, 155, 60), 2: (150, 100, 40), 3: (90, 40, 115)}[variant]
    cx, cy = w // 2, 46
    for side in (-1, 1):                                   # три яруса перьев с каждой стороны
        base = 0 if side > 0 else 180
        for tier, (ang, length, width) in enumerate(((-62, 40, 7), (-34, 46, 8), (-8, 48, 8), (20, 42, 7), (46, 32, 6))):
            a = base + side * ang if side > 0 else 180 - ang
            _feather(s, (cx + side * 12, cy), a, length, width, fill, edge)
    pygame.draw.circle(s, (255, 255, 255), (cx, cy), 18)                      # глаз
    pygame.draw.circle(s, edge, (cx, cy), 18, 2)
    if variant == 3:                                                          # воспалённые жилки и трещины
        for ang in (20, 80, 150, 210, 275, 330):
            v = pygame.Vector2(math.cos(math.radians(ang)), math.sin(math.radians(ang)))
            pygame.draw.line(s, (220, 40, 70), (cx + v.x * 18, cy + v.y * 18), (cx + v.x * 11, cy + v.y * 11), 1)
        pygame.draw.line(s, (255, 70, 70), (cx - 30, cy - 18), (cx - 20, cy - 6), 1)
        pygame.draw.line(s, (255, 70, 70), (cx + 34, cy + 10), (cx + 24, cy + 18), 1)
    halo = (255, 220, 100) if variant < 3 else (160, 70, 200)
    pygame.draw.ellipse(s, halo, (cx - 22, 6, 44, 13), 3)                    # нимб
    pygame.draw.ellipse(s, (255, 255, 235) if variant < 3 else (220, 170, 240), (cx - 18, 9, 36, 7), 1)
    return outlined(s)


def make_barrier():
    s, d = _surf(16, 16), pygame.draw
    d.rect(s, (170, 170, 180), (0, 2, 16, 14))
    for x in range(-8, 24, 8):
        d.polygon(s, (240, 130, 40), [(x, 2), (x + 4, 2), (x + 12, 16), (x + 8, 16)])
    d.rect(s, K, (0, 2, 16, 14), 1)
    return s


def make_hedge():
    s, d = _surf(16, 16), pygame.draw
    d.rect(s, (40, 130, 60), (0, 1, 16, 15), border_radius=4)
    d.rect(s, (70, 170, 80), (2, 3, 6, 5), border_radius=2)
    d.rect(s, (70, 170, 80), (9, 8, 5, 5), border_radius=2)
    d.rect(s, K, (0, 1, 16, 15), 1, border_radius=4)
    return s


def make_crate():
    s, d = _surf(16, 16), pygame.draw
    d.rect(s, (170, 120, 70), (0, 0, 16, 16))
    d.rect(s, (130, 85, 50), (0, 0, 16, 16), 2)
    d.line(s, (130, 85, 50), (0, 0), (15, 15))
    d.line(s, (130, 85, 50), (15, 0), (0, 15))
    d.rect(s, K, (0, 0, 16, 16), 1)
    return s


def _icon_draw(kind, color):
    s = pygame.Surface((12, 12), pygame.SRCALPHA)
    d = pygame.draw
    c = color
    if kind == "burger":
        d.rect(s, (230, 170, 80), (1, 2, 10, 3)); d.rect(s, c, (1, 5, 10, 2))
        d.rect(s, (120, 70, 40), (1, 7, 10, 2)); d.rect(s, (230, 170, 80), (1, 9, 10, 2))
    elif kind == "broom":
        d.line(s, (150, 100, 60), (2, 1), (8, 8), 2); d.polygon(s, c, [(6, 7), (11, 8), (9, 11), (5, 10)])
    elif kind == "tv":
        d.rect(s, (90, 90, 110), (1, 2, 10, 8)); d.rect(s, c, (2, 3, 6, 6)); d.line(s, (200, 200, 200), (4, 2), (2, 0))
    elif kind == "bomb":
        d.circle(s, c, (5, 7), 5); d.rect(s, (250, 250, 250), (5, 0, 2, 3)); d.circle(s, (255, 230, 90), (6, 0), 1)
    elif kind == "feather":
        d.ellipse(s, c, (3, 0, 6, 11)); d.line(s, (200, 180, 120), (6, 1), (4, 11))
    elif kind == "mask":
        d.ellipse(s, c, (1, 0, 10, 12)); d.rect(s, K, (3, 4, 2, 2)); d.rect(s, K, (7, 4, 2, 2)); d.line(s, K, (6, 0), (4, 11))
    elif kind == "revolver":
        d.rect(s, c, (1, 3, 9, 3)); d.rect(s, c, (1, 6, 3, 5)); d.circle(s, (100, 70, 50), (6, 5), 2)
    elif kind == "soldier":
        d.rect(s, c, (3, 4, 6, 6)); d.rect(s, (255, 205, 170), (4, 1, 4, 3)); d.rect(s, (60, 60, 60), (9, 3, 2, 6))
    elif kind == "compass":
        d.circle(s, c, (6, 6), 5, 2); d.line(s, (230, 60, 70), (6, 6), (9, 2), 2); d.line(s, (250, 250, 250), (6, 6), (3, 10), 1)
    elif kind == "clock":
        d.circle(s, (240, 240, 250), (6, 6), 5); d.circle(s, c, (6, 6), 5, 1)
        d.line(s, K, (6, 6), (6, 2)); d.line(s, K, (6, 6), (9, 7))
    elif kind == "photo":
        d.rect(s, c, (1, 1, 10, 10)); d.rect(s, (200, 200, 210), (2, 2, 8, 6)); d.rect(s, K, (1, 1, 10, 10), 1)
    elif kind == "halo":
        d.ellipse(s, c, (0, 3, 12, 6), 2); d.ellipse(s, (160, 100, 220), (1, 4, 10, 4), 1)
    elif kind == "kettle":
        d.ellipse(s, c, (1, 3, 9, 8)); d.rect(s, c, (8, 4, 3, 2)); d.arc(s, K, (2, 0, 7, 6), 0, 3.14, 1)
    elif kind == "gnome":
        d.polygon(s, c, [(6, 0), (9, 5), (3, 5)]); d.rect(s, (255, 205, 170), (4, 5, 4, 3)); d.rect(s, (245, 245, 245), (3, 7, 6, 4))
    elif kind == "mail":
        d.rect(s, c, (1, 3, 10, 7)); d.line(s, (150, 140, 120), (1, 3), (6, 7)); d.line(s, (150, 140, 120), (11, 3), (6, 7))
    elif kind == "monitor":
        d.rect(s, c, (2, 1, 8, 10)); d.circle(s, (255, 80, 80), (6, 4), 1); d.rect(s, K, (4, 6, 4, 3), 1)
    else:
        d.rect(s, c, (2, 2, 8, 8))
    return outlined(s)


class SpriteBook:
    """Кэш всех спрайтов; создаётся после инициализации дисплея."""

    def __init__(self, item_defs):
        self.surf = {
            "player": outlined(from_rows(PLAYER)), "bush": outlined(from_rows(BUSH)),
            "tree": outlined(from_rows(TREE)), "bird": outlined(from_rows(BIRD)),
            "rock": from_rows(ROCK), "soldier": outlined(from_rows(SOLDIER)),
            "lumberjack": make_lumberjack(), "dog": make_dog(), "mailman": make_mailman(),
            "sprinkler": make_sprinkler(), "cart": make_cart(), "neighbor": make_neighbor(),
            "neighbor_boss": make_neighbor_boss(), "hedge": make_hedge(), "crate": make_crate(),
            "shine": make_shine(1), "shine2": make_shine(2), "shine3": make_shine(3), "eye": make_eye(), "fragment": make_fragment(), "glitchling": make_glitchling(), "chaos": make_chaos(),
            "rat": make_rat(), "cop": make_cop(), "drone": make_drone(), "car": make_car(), "tvmon": make_tvmon(),
            "mayor": make_mayor(), "mayor_desk": make_mayor_desk(), "mayor_surreal": make_mayor_surreal(), "barrier": make_barrier(),
        }
        for item in item_defs:
            self.surf["icon_" + item.id] = _icon_draw(item.icon, item.color)
        self.surf["heart_full"] = self._heart((230, 50, 70))
        self.surf["heart_half"] = self._heart((230, 50, 70), half=True)
        self.surf["heart_empty"] = self._heart((70, 50, 80))
        self.surf["coin"] = self._coin()
        self.surf["gem_heart"] = pygame.transform.scale(self._heart((255, 90, 110)), (9, 9))
        self._white = {}

    def _heart(self, color, half=False):
        s = pygame.Surface((9, 8), pygame.SRCALPHA)
        pts = [(1, 1), (2, 0), (3, 0), (4, 1), (5, 0), (6, 0), (7, 1), (8, 2), (7, 4), (4, 7), (1, 4), (0, 2)]
        pygame.draw.polygon(s, color, pts)
        pygame.draw.polygon(s, K, pts, 1)
        if half:
            empty = pygame.Surface((9, 8), pygame.SRCALPHA)
            pygame.draw.polygon(empty, (70, 50, 80), pts)
            pygame.draw.polygon(empty, K, pts, 1)
            empty.blit(s, (0, 0), pygame.Rect(0, 0, 4, 8))
            return empty
        return s

    def _coin(self):
        s = pygame.Surface((7, 7), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 215, 70), (3, 3), 3)
        pygame.draw.circle(s, K, (3, 3), 3, 1)
        s.set_at((2, 2), (255, 255, 220))
        return s

    def get(self, name, flip=False):
        surf = self.surf[name]
        return pygame.transform.flip(surf, True, False) if flip else surf

    def white(self, name):
        if name not in self._white:
            self._white[name] = silhouette(self.surf[name])
        return self._white[name]

    def icon(self, item_id):
        return self.surf["icon_" + item_id]
