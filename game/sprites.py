"""Спрайты в стиле The Binding of Isaac: Repentance+ (рисуются кодом, внешние ассеты не нужны).

Все изображения строятся модулями game/art/*. Ходьба и анимации боссов — наборы кадров: SpriteBook.get(name)
сам выбирает кадр по времени, поэтому код врагов и боссов менять не пришлось. Игрок передаёт state="idle"/"walk".
"""
import pygame

from .art import humans as H, foes as F, bosses as B, world as W
from .art.canvas import OUT, Canvas, dark, light
from .art.bosses import SHINE_IRIS, IMP_IRIS

K = OUT


def silhouette(surf, color=(255, 255, 255)):
    return pygame.mask.from_surface(surf).to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))


def draw_iris(surf, cx, cy, ox, oy, color, kind="round"):
    """Радужка и зрачок глаз-боссов: тёмный контур, тень снизу, блик (кружки без сглаживания, как и сам спрайт)."""
    pygame.draw.circle(surf, OUT, (cx + ox, cy + oy), 11)
    pygame.draw.circle(surf, color, (cx + ox, cy + oy), 10)
    pygame.draw.circle(surf, dark(color, 0.45), (cx + ox, cy + oy), 10, 2)
    pygame.draw.circle(surf, color, (cx + ox - 1, cy + oy - 1), 8)
    if kind == "slit":
        pygame.draw.ellipse(surf, (25, 6, 6), (cx + int(ox * 1.5) - 2, cy + int(oy * 1.5) - 7, 4, 14))
    else:
        pygame.draw.circle(surf, (20, 10, 30), (cx + int(ox * 1.5), cy + int(oy * 1.5)), 5)
    hx, hy = cx + ox - 3, cy + oy - 4
    surf.fill((255, 255, 255), (hx, hy, 2, 2))


def _anim(fn, n=4, *args):
    return [fn(i, *args).outlined() for i in range(n)]


# имя -> (функция-фабрика кадров, мс на кадр). Статичные плитки возвращают один кадр.
def _registry():
    R = {}
    ms = {}

    def add(name, frames, t=130):
        R[name] = frames
        ms[name] = t

    add("player", [H.hero("rob", i).outlined() for i in range(4)], 110)
    add("bush", _anim(F.bush), 140)
    add("tree", _anim(F.face_tree), 150)
    add("bird", _anim(F.bird), 90)
    add("soldier", _anim(H.soldier), 160)
    add("lumberjack", _anim(B.lumberjack_boss), 120)
    add("dog", _anim(F.dog), 90)
    add("mailman", _anim(H.mailman), 120)
    add("sprinkler", _anim(F.sprinkler), 110)
    add("cart", _anim(F.cart), 120)
    add("neighbor", _anim(H.neighbor), 110)
    add("neighbor_boss", _anim(B.neighbor_boss), 120)
    for v, n in ((1, "shine"), (2, "shine2"), (3, "shine3")):
        add(n, [B.shine(i, v).outlined() for i in range(4)], 100)
    add("eye", _anim(F.eye_swarm), 150)
    add("fragment", _anim(F.fragment), 160)
    add("glitchling", _anim(F.glitchling), 70)
    add("chaos", _anim(B.chaos), 140)
    add("living_spruce", _anim(F.living_spruce), 150)
    add("landlord", _anim(H.landlord), 130)
    add("tank", _anim(B.tank), 140)
    add("cherub", _anim(F.cherub), 110)
    add("cloudling", _anim(F.cloudling), 160)
    add("halo", _anim(F.halo_ring), 120)
    add("dove", _anim(F.dove), 100)
    add("trumpeter", _anim(F.trumpeter), 130)
    add("stone_angel", _anim(F.stone_angel), 220)
    add("gate_keeper", _anim(B.gate_keeper), 220)
    add("hellhound", _anim(F.hellhound), 90)
    add("fire_imp", _anim(F.fire_imp), 100)
    add("golem", _anim(F.magma_golem), 160)
    add("ember", _anim(F.ember), 100)
    add("idol", _anim(F.idol), 150)
    for v, n in ((1, "imp"), (2, "imp2"), (3, "imp3")):
        add(n, [B.imp_boss(i, v).outlined() for i in range(4)], 100)
    add("imp_mini", _anim(F.imp_mini), 90)
    add("rat", _anim(F.rat), 90)
    add("cop", _anim(H.cop), 120)
    add("drone", _anim(F.drone), 60)
    add("car", _anim(F.car), 110)
    add("tvmon", _anim(F.tvmon), 140)
    add("mayor", _anim(B.mayor), 260)
    add("mayor_desk", _anim(B.mayor_desk), 160)
    add("mayor_surreal", _anim(B.mayor_surreal), 160)
    add("player_shine_form", [B.shine_form(i).outlined() for i in range(4)], 100)
    add("coin", [W.coin(i) for i in range(4)], 140)
    return R, ms


def _hero_frames(cid):
    """(кадр стойки, кадры ходьбы) героя; все — с контуром."""
    if cid == "soul":
        fr = _anim(H.soul)
        return fr[0], fr
    if cid == "angel":
        return H.angel(0, idle=True).outlined(), [H.angel(i).outlined() for i in range(4)]
    if cid == "glitch":
        base = [H.hero("glitch", i) for i in range(4)]
        walk = []
        for i, c in enumerate(base):
            g = Canvas(c.w + 4, c.h)
            ghost = Canvas(c.w, c.h)
            for y in range(c.h):
                for x in range(c.w):
                    q = c.p[y][x]
                    if q:
                        ghost.p[y][x] = (255, 70, 200, 255)
            g.blit(ghost, 3 + (i % 2), 0)
            g.blit(c, 0, 0)
            for y0, dx in (((4 + i * 3) % 14, 2 - i % 3), ((9 + i * 2) % 16, -1 + i % 2)):       # сбои строк
                for x in range(c.w - 1, -1, -1):
                    for yy in (y0, y0 + 1):
                        if 0 <= yy < c.h and 0 <= x + dx < g.w and c.p[yy][x]:
                            g.p[yy][x + dx] = c.p[yy][x]
            walk.append(g.outlined())
        return walk[0], walk
    try:
        walk = [H.hero(cid, i).outlined() for i in range(4)]
        idle = H.hero(cid, 0, idle=True).outlined()
    except KeyError:
        walk = [H.hero("rob", i).outlined() for i in range(4)]
        idle = H.hero("rob", 0, idle=True).outlined()
    return idle, walk


# --- совместимость: прежние публичные функции (их вызывают тесты и сторонний код) ---
def make_player_sprite(char_id, scale=1.0):
    """Кадр стойки героя. Масштаб Тома (1.5) теперь заложен в рисунок, параметр scale оставлен для совместимости."""
    return _hero_frames(char_id)[0].to_surface()


def make_shine(variant=1):
    return B.shine(0, variant).outlined().to_surface()


def make_imp_boss(variant=1):
    return B.imp_boss(0, variant).outlined().to_surface()


class SpriteBook:
    """Кэш всех спрайтов; создаётся после инициализации дисплея."""

    def __init__(self, item_defs, characters=None):
        self.surf = {}      # статичный/первый кадр каждого спрайта
        self.anim = {}      # имя -> [Surface...] — цикл ходьбы/анимации
        self.ms = {}        # мс на кадр
        self.idle = {}      # имя -> Surface стойки (у героев)
        self._flip = {}
        self._white = {}
        frames, ms = _registry()
        for name, fr in frames.items():
            self.anim[name] = [c.to_surface() for c in fr]
            self.surf[name] = self.anim[name][0]
            self.ms[name] = ms[name]
        for name, tile in (("rock", W.rock()), ("hedge", W.hedge()), ("barrier", W.barrier()), ("crate", W.crate()),
                           ("basalt", W.basalt()), ("cloud", W.cloud()), ("god", B.god_wings())):
            self.surf[name] = tile.to_surface()
        for cid in (characters or {"rob": {}}):
            idle, walk = _hero_frames(cid)
            key = "player_" + cid
            self.idle[key] = idle.to_surface()
            self.anim[key] = [c.to_surface() for c in walk]
            self.surf[key] = self.idle[key]
            self.ms[key] = 105
        for item in item_defs:
            self.surf["icon_" + item.id] = W.icon(item.icon, item.color).to_surface()
        self.surf["heart_full"] = W.heart("full").to_surface()
        self.surf["heart_half"] = W.heart("half").to_surface()
        self.surf["heart_empty"] = W.heart("empty").to_surface()
        self.surf["gem_heart"] = W.gem_heart().to_surface()
        self.tears = {}
        self.props = {}

    # --- выбор кадра ---
    def _frame(self, name, state=None, phase=0):
        frames = self.anim.get(name)
        if frames is None:
            return 0, self.surf[name]
        if state == "idle" and name in self.idle:
            return -1, self.idle[name]
        idx = (pygame.time.get_ticks() // self.ms.get(name, 120) + phase) % len(frames)
        return idx, frames[idx]

    def get(self, name, flip=False, state=None, phase=0):
        idx, surf = self._frame(name, state, phase)
        if not flip:
            return surf
        key = (name, idx)
        hit = self._flip.get(key)
        if hit is None:
            hit = self._flip[key] = pygame.transform.flip(surf, True, False)
        return hit

    def white(self, name, state=None, phase=0):
        idx, surf = self._frame(name, state, phase)
        key = (name, idx)
        if key not in self._white:
            self._white[key] = silhouette(surf)
        return self._white[key]

    def icon(self, item_id):
        return self.surf["icon_" + item_id]

    def prop(self, kind, used=False):
        key = (kind, bool(used))
        if key not in self.props:
            self.props[key] = W.prop(kind, used).to_surface()
        return self.props[key]

    def tear(self, radius, color, friendly):
        key = (int(radius), tuple(color), bool(friendly))
        if key not in self.tears:
            if len(self.tears) > 300:
                self.tears.clear()
            self.tears[key] = W.tear(radius, color, friendly).to_surface()
        return self.tears[key]
