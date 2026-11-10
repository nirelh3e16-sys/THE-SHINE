"""Тени, свет и блики солнца — простые 2D-эффекты на Pygame (без настоящих шейдеров и GPU-кода).

Кадр рисуется как обычно; затем:
1. draw_shadows — тени от солнца под мобами, игроком, NPC и боссами (до отрисовки самих спрайтов);
2. apply — цветовой тон времени суток, затемнение с «дырами» от источников света, цветное свечение
   и блики/лучи солнца (после отрисовки мира, до HUD).
"""
import math

import pygame

from .daycycle import shadow_params
from .graphics_settings import SHADOW_ALPHA
from .settings import GAME_W, GAME_H

SHADOW_RGB = (8, 6, 20)
WHITE = (255, 255, 255)
CACHE_LIMIT = 400
LOW_QUALITY_LIGHTS = 5      # на низком качестве рисуем только самые сильные источники света


def _trim(cache, limit=CACHE_LIMIT):
    """Выбрасывает самые старые записи по одной (раньше кэш сбрасывался целиком, и игра на кадр «замирала»)."""
    while len(cache) > limit:
        cache.pop(next(iter(cache)))


def _fast_alpha(surf):
    """Переводит поверхность в формат экрана: так blit с прозрачностью заметно быстрее. Без окна (тесты) — как есть."""
    try:
        if pygame.display.get_surface() is not None:
            return surf.convert_alpha()
    except (pygame.error, AttributeError):
        pass
    return surf


class Lighting:
    def __init__(self):
        self._cut = {}      # (радиус, сила) -> градиент прозрачности для «пробивания» тьмы
        self._add = {}      # (радиус, цвет, сила) -> цветное свечение (складывается с кадром)
        self._shadow_layer = None
        self._dark = None
        self._shafts = None
        self._shafts_key = None
        self.quality = 2    # 2 — всё, 1 — без лучей и бликов, 0 — ещё и упрощённые тени и меньше света (ставит Game)

    # --- заготовки градиентов (кэшируются) ---
    def _quant(self, radius):
        return max(4, int(radius) // 4 * 4)

    def _cut_gradient(self, radius, intensity):
        key = (self._quant(radius), int(max(0.0, min(1.0, intensity)) * 10))
        surf = self._cut.get(key)
        if surf is None:
            _trim(self._cut, CACHE_LIMIT - 1)
            r, k = key[0], key[1] / 10
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            for step in range(r, 0, -2):
                alpha = int(255 * k * (1 - step / r) ** 1.3)
                pygame.draw.circle(surf, (0, 0, 0, alpha), (r, r), step)
            surf = self._cut[key] = _fast_alpha(surf)
        return surf

    def _add_gradient(self, radius, color, intensity):
        key = (self._quant(radius), color, int(max(0.0, min(1.0, intensity)) * 10))
        surf = self._add.get(key)
        if surf is None:
            _trim(self._add, CACHE_LIMIT - 1)
            r, k = key[0], key[2] / 10
            surf = pygame.Surface((r * 2, r * 2))
            surf.fill((0, 0, 0))
            for step in range(r, 0, -2):
                f = k * (1 - step / r) ** 1.8
                pygame.draw.circle(surf, (int(color[0] * f), int(color[1] * f), int(color[2] * f)), (r, r), step)
            self._add[key] = surf
        return surf

    # --- тени ---
    def draw_shadows(self, surf, off, actors, state, gfx):
        """actors: список (x, y_ног, ширина, высота) в координатах мира."""
        dx, dy, length, strength = shadow_params(state)
        if strength <= 0 or not actors:
            return
        if self._shadow_layer is None:
            self._shadow_layer = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
        layer = self._shadow_layer
        color = (*SHADOW_RGB, 255)
        simple = self.quality <= 0      # на низком качестве — только пятно под ногами, без проекции
        shapes, lo_x, lo_y, hi_x, hi_y = [], GAME_W, GAME_H, 0, 0
        for x, y, w, h in actors:
            x, y = x + off.x, y + off.y
            half = w * 0.45
            ext = (dx * h * length, dy * h * length * 0.55)                                   # проекция роста
            shapes.append((x, y, w, half, ext))
            lo_x, hi_x = min(lo_x, x - w * 0.5, x + ext[0] - half), max(hi_x, x + w * 0.5, x + ext[0] + half)
            lo_y, hi_y = min(lo_y, y - w * 0.18, y + ext[1]), max(hi_y, y + w * 0.18, y + ext[1])   # тень может падать и вверх
        # чистим и переносим на экран только прямоугольник, где реально есть тени (а не весь кадр)
        area = pygame.Rect(int(lo_x) - 2, int(lo_y) - 2, int(hi_x - lo_x) + 5, int(hi_y - lo_y) + 5).clip(layer.get_rect())
        if area.width <= 0 or area.height <= 0:
            return
        layer.fill((0, 0, 0, 0), area)
        for x, y, w, half, ext in shapes:
            pygame.draw.ellipse(layer, color, (x - w * 0.5, y - w * 0.18, w, w * 0.36))      # пятно под ногами
            if not simple:
                pts = [(x - half, y), (x + half, y), (x + half * 0.55 + ext[0], y + ext[1]), (x - half * 0.55 + ext[0], y + ext[1])]
                pygame.draw.polygon(layer, color, pts)
        layer.set_alpha(int(min(1.0, strength * SHADOW_ALPHA[gfx["shadow_strength"]]) * 120))
        surf.blit(layer, area.topleft, area)

    # --- свет ---
    def apply(self, surf, state, lights, gfx):
        """lights: список (x, y, радиус, цвет, сила 0..1) в экранных координатах."""
        if state.tint != (255, 255, 255):
            surf.fill(state.tint, special_flags=pygame.BLEND_RGB_MULT)       # тон рассвета/заката/ночи
        use_lights = gfx["lights"]
        if use_lights and self.quality <= 0 and len(lights) > LOW_QUALITY_LIGHTS:
            lights = sorted(lights, key=lambda l: -l[2] * l[4])[:LOW_QUALITY_LIGHTS]
        if state.darkness > 0.01:
            if self._dark is None:
                self._dark = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
            dark = self._dark
            dark.fill((*state.dark_rgb, int(255 * state.darkness)))
            if use_lights:
                for x, y, r, color, power in lights:
                    if -r < x < GAME_W + r and -r < y < GAME_H + r:
                        dark.blit(self._cut_gradient(r, power), (int(x) - self._quant(r), int(y) - self._quant(r)),
                                  special_flags=pygame.BLEND_RGBA_SUB)
            surf.blit(dark, (0, 0))
        if use_lights:
            for x, y, r, color, power in lights:
                if -r < x < GAME_W + r and -r < y < GAME_H + r:
                    q = self._quant(r)
                    surf.blit(self._add_gradient(r, color, power * 0.55), (int(x) - q, int(y) - q), special_flags=pygame.BLEND_RGB_ADD)
        if gfx["sun_glare"] and state.has_sun and self.quality >= 1:
            self._sun_glare(surf, state)

    def _sun_glare(self, surf, state):
        """Тёплое сияние со стороны солнца, блики на линзе и световые лучи."""
        power = min(1.0, state.elevation * 1.6)
        sx = GAME_W / 2 + state.sun_dx * 300
        sy = 20 + 80 * (1 - state.elevation)
        color = (255, 205, 130)
        q = self._quant(220)
        surf.blit(self._add_gradient(220, color, 0.55 * power), (int(sx) - q, int(sy) - q), special_flags=pygame.BLEND_RGB_ADD)
        if power < 0.3 or self.quality < 2:     # блики и лучи — самое дорогое, поэтому первыми отключаются
            return
        cx, cy = GAME_W / 2, GAME_H / 2
        for k, (r, col) in zip((0.55, 0.85, 1.15, 1.45), ((14, (255, 225, 170)), (8, (150, 200, 255)), (18, (255, 170, 120)), (10, (200, 255, 200)))):
            fx, fy = sx + (cx - sx) * k, sy + (cy - sy) * k
            qq = self._quant(r)
            surf.blit(self._add_gradient(r, col, 0.35 * power), (int(fx) - qq, int(fy) - qq), special_flags=pygame.BLEND_RGB_ADD)
        # лучи двигаются медленно (солнце идёт по небу минутами), поэтому рисуем их заново только когда сдвиг заметен
        key = (int(sx) // 4, int(sy) // 4, int(power * 16))
        if self._shafts is None:
            self._shafts = pygame.Surface((GAME_W, GAME_H))
        if key != self._shafts_key:
            self._shafts_key = key
            shafts = self._shafts
            shafts.fill((0, 0, 0))
            for i, spread in enumerate((-0.5, -0.2, 0.1, 0.4)):
                ang = math.atan2(cy - sy, cx - sx) + spread
                end = (sx + math.cos(ang) * 700, sy + math.sin(ang) * 700)
                c = int(26 * power)
                pygame.draw.line(shafts, (c, int(c * 0.8), int(c * 0.5)), (sx, sy), end, 26 - i * 3)
        surf.blit(self._shafts, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
