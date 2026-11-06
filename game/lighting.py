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


class Lighting:
    def __init__(self):
        self._cut = {}      # (радиус, сила) -> градиент прозрачности для «пробивания» тьмы
        self._add = {}      # (радиус, цвет, сила) -> цветное свечение (складывается с кадром)
        self._shadow_layer = None
        self._dark = None
        self._shafts = None

    # --- заготовки градиентов (кэшируются) ---
    def _quant(self, radius):
        return max(4, int(radius) // 4 * 4)

    def _cut_gradient(self, radius, intensity):
        key = (self._quant(radius), int(max(0.0, min(1.0, intensity)) * 10))
        surf = self._cut.get(key)
        if surf is None:
            if len(self._cut) > 400:
                self._cut.clear()
            r, k = key[0], key[1] / 10
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            for step in range(r, 0, -2):
                alpha = int(255 * k * (1 - step / r) ** 1.3)
                pygame.draw.circle(surf, (0, 0, 0, alpha), (r, r), step)
            self._cut[key] = surf
        return surf

    def _add_gradient(self, radius, color, intensity):
        key = (self._quant(radius), color, int(max(0.0, min(1.0, intensity)) * 10))
        surf = self._add.get(key)
        if surf is None:
            if len(self._add) > 400:
                self._add.clear()
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
        layer.fill((0, 0, 0, 0))
        color = (*SHADOW_RGB, 255)
        for x, y, w, h in actors:
            x, y = x + off.x, y + off.y
            half = w * 0.45
            pygame.draw.ellipse(layer, color, (x - w * 0.5, y - w * 0.18, w, w * 0.36))      # пятно под ногами
            ext = (dx * h * length, dy * h * length * 0.55)                                   # проекция роста
            pts = [(x - half, y), (x + half, y), (x + half * 0.55 + ext[0], y + ext[1]), (x - half * 0.55 + ext[0], y + ext[1])]
            pygame.draw.polygon(layer, color, pts)
        layer.set_alpha(int(min(1.0, strength * SHADOW_ALPHA[gfx["shadow_strength"]]) * 120))
        surf.blit(layer, (0, 0))

    # --- свет ---
    def apply(self, surf, state, lights, gfx):
        """lights: список (x, y, радиус, цвет, сила 0..1) в экранных координатах."""
        if state.tint != (255, 255, 255):
            surf.fill(state.tint, special_flags=pygame.BLEND_RGB_MULT)       # тон рассвета/заката/ночи
        use_lights = gfx["lights"]
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
        if gfx["sun_glare"] and state.has_sun:
            self._sun_glare(surf, state)

    def _sun_glare(self, surf, state):
        """Тёплое сияние со стороны солнца, блики на линзе и световые лучи."""
        power = min(1.0, state.elevation * 1.6)
        sx = GAME_W / 2 + state.sun_dx * 300
        sy = 20 + 80 * (1 - state.elevation)
        color = (255, 205, 130)
        q = self._quant(220)
        surf.blit(self._add_gradient(220, color, 0.55 * power), (int(sx) - q, int(sy) - q), special_flags=pygame.BLEND_RGB_ADD)
        if power < 0.3:
            return
        cx, cy = GAME_W / 2, GAME_H / 2
        for k, (r, col) in zip((0.55, 0.85, 1.15, 1.45), ((14, (255, 225, 170)), (8, (150, 200, 255)), (18, (255, 170, 120)), (10, (200, 255, 200)))):
            fx, fy = sx + (cx - sx) * k, sy + (cy - sy) * k
            qq = self._quant(r)
            surf.blit(self._add_gradient(r, col, 0.35 * power), (int(fx) - qq, int(fy) - qq), special_flags=pygame.BLEND_RGB_ADD)
        if self._shafts is None:
            self._shafts = pygame.Surface((GAME_W, GAME_H))
        shafts = self._shafts
        shafts.fill((0, 0, 0))
        for i, spread in enumerate((-0.5, -0.2, 0.1, 0.4)):
            ang = math.atan2(cy - sy, cx - sx) + spread
            end = (sx + math.cos(ang) * 700, sy + math.sin(ang) * 700)
            c = int(26 * power)
            pygame.draw.line(shafts, (c, int(c * 0.8), int(c * 0.5)), (sx, sy), end, 26 - i * 3)
        surf.blit(shafts, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
