"""Окно, масштабирование без искажений, эффекты (частицы, тряска, вспышки)."""
import math
import random

import pygame

from .settings import GAME_W, GAME_H


class Display:
    def __init__(self, scale=2, fullscreen=False, gpu=True):
        self.surface = pygame.Surface((GAME_W, GAME_H))
        self.fullscreen = fullscreen
        self.gpu = gpu   # SCALED: вывод через SDL renderer (Direct3D/OpenGL) — на нём работает оверлей Steam
        self.scale = max(1, int(scale))
        self._create_window()
        self._offset = (0, 0)
        self._fx = self._fy = 1.0
        self.fill_mode = "blur"   # "blur" — размытое продолжение кадра по краям, "stretch" — растянуть
        self._ambient = None        # кэш размытого фона вокруг кадра (обновляется раз в AMBIENT_EVERY кадров)
        self._ambient_age = 0
        self._scaled = None         # буфер для масштабирования кадра: не выделяем новую поверхность каждый кадр

    @staticmethod
    def _desktop_size():
        try:
            return pygame.display.get_desktop_sizes()[0]
        except (AttributeError, IndexError, pygame.error):
            info = pygame.display.Info()
            return info.current_w, info.current_h

    def _canvas_size(self):
        """Размер холста в полноэкранном GPU-режиме: под пропорции монитора, чтобы не было полос."""
        dw, dh = self._desktop_size()
        aspect = dw / max(1, dh)
        return max(GAME_W, math.ceil(GAME_H * aspect)), max(GAME_H, math.ceil(GAME_W / aspect))

    def _create_window(self):
        if self.gpu:
            try:
                if self.fullscreen:
                    pygame.display.set_mode(self._canvas_size(), pygame.SCALED | pygame.FULLSCREEN)
                else:
                    pygame.display.set_mode((GAME_W, GAME_H), pygame.SCALED | pygame.RESIZABLE)
                pygame.display.set_caption("THE SHINE — FreeDom Studio")
                return
            except pygame.error:
                self.gpu = False  # запасной программный вывод
        if self.fullscreen:
            pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            pygame.display.set_mode((GAME_W * self.scale, GAME_H * self.scale), pygame.RESIZABLE)
        pygame.display.set_caption("THE SHINE — FreeDom Studio")

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self._create_window()

    def present(self):
        win = pygame.display.get_surface()
        ww, wh = win.get_size()
        if self.fill_mode == "stretch":
            self._offset = (0, 0)
            self._fx, self._fy = ww / GAME_W, wh / GAME_H
            win.blit(self._scale_to((ww, wh)), (0, 0))
            pygame.display.flip()
            return
        factor = min(ww / GAME_W, wh / GAME_H)
        if factor >= 1:
            factor = float(int(factor))
        size = (max(1, int(GAME_W * factor)), max(1, int(GAME_H * factor)))
        self._offset = ((ww - size[0]) // 2, (wh - size[1]) // 2)
        self._fx = self._fy = factor
        if size[0] < ww or size[1] < wh:
            self._draw_ambient(win, (ww, wh), pygame.Rect(self._offset, size))
        if size == self.surface.get_size():
            win.blit(self.surface, self._offset)      # масштаб 1:1 — копируем без лишнего масштабирования
        else:
            win.blit(self._scale_to(size), self._offset)
        pygame.display.flip()

    def _scale_to(self, size):
        """Масштабирует кадр в переиспользуемый буфер (раньше каждый кадр создавалась новая поверхность окна)."""
        if self._scaled is None or self._scaled.get_size() != size:
            self._scaled = pygame.Surface(size, 0, self.surface)   # тот же формат пикселей, что у кадра (требует pygame)
        pygame.transform.scale(self.surface, size, self._scaled)
        return self._scaled

    AMBIENT_EVERY = 8   # размытый фон по краям пересчитывается раз в 8 кадров: он размытый, разницы глаз не заметит

    def _draw_ambient(self, win, win_size, game_rect):
        """Вместо чёрных полос — размытое затемнённое продолжение кадра. Считается редко, рисуется только на полосах."""
        self._ambient_age += 1
        if self._ambient is None or self._ambient.get_size() != win_size or self._ambient_age >= self.AMBIENT_EVERY:
            self._ambient_age = 0
            if self._ambient is None or self._ambient.get_size() != win_size:
                self._ambient = pygame.Surface(win_size, 0, self.surface)
            tiny = pygame.transform.smoothscale(self.surface, (32, 18))
            pygame.transform.smoothscale(tiny, win_size, self._ambient)
            self._ambient.fill((135, 135, 135), special_flags=pygame.BLEND_RGB_MULT)   # затемнение без alpha-слоя
            self._ambient.fill((5, 2, 9), special_flags=pygame.BLEND_RGB_ADD)
        ww, wh = win_size
        strips = (pygame.Rect(0, 0, game_rect.left, wh), pygame.Rect(game_rect.right, 0, ww - game_rect.right, wh),
                  pygame.Rect(game_rect.left, 0, game_rect.width, game_rect.top),
                  pygame.Rect(game_rect.left, game_rect.bottom, game_rect.width, wh - game_rect.bottom))
        for r in strips:                       # только полосы вокруг картинки, а не всё окно целиком
            if r.width > 0 and r.height > 0:
                win.blit(self._ambient, r.topleft, r)

    def to_game(self, pos):
        x = (pos[0] - self._offset[0]) / self._fx
        y = (pos[1] - self._offset[1]) / self._fy
        return pygame.Vector2(x, y)


class Effects:
    """Частицы, тряска экрана, вспышка. Количество частиц ограничено."""

    def __init__(self, max_particles=300, shake_enabled=True):
        self.particles = []  # [x, y, vx, vy, life, maxlife, color, size]
        self.max_particles = max_particles
        self.shake_enabled = shake_enabled
        self.shake_t = 0.0
        self.shake_amp = 0.0
        self.flash_t = 0.0
        self.flash_color = (255, 255, 255)
        self.flash_dur = 0.3
        self._flash_overlay = None
        self.rng = random.Random()

    def burst(self, pos, color, n=8, speed=90, life=0.4, size=2):
        for _ in range(n):
            if len(self.particles) >= self.max_particles:
                return
            a = self.rng.uniform(0, math.tau)
            s = self.rng.uniform(0.3, 1.0) * speed
            self.particles.append([pos[0], pos[1], math.cos(a) * s, math.sin(a) * s,
                                   life * self.rng.uniform(0.6, 1.0), life, color, size])

    def shake(self, amp, dur):
        if self.shake_enabled:
            self.shake_amp = max(self.shake_amp, amp)
            self.shake_t = max(self.shake_t, dur)

    def flash(self, color=(255, 255, 255), dur=0.3):
        self.flash_color, self.flash_t, self.flash_dur = color, dur, dur

    def update(self, dt):
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[2] *= 0.94
            p[3] *= 0.94
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        self.shake_t = max(0.0, self.shake_t - dt)
        if self.shake_t == 0:
            self.shake_amp = 0.0
        self.flash_t = max(0.0, self.flash_t - dt)

    def offset(self):
        if self.shake_t <= 0:
            return pygame.Vector2(0, 0)
        return pygame.Vector2(self.rng.uniform(-1, 1), self.rng.uniform(-1, 1)) * self.shake_amp

    def draw_particles(self, surf, off):
        for x, y, _, _, life, maxlife, color, size in self.particles:
            if life / maxlife < 0.3 and int(life * 40) % 2:
                continue
            surf.fill(color, (int(x + off.x), int(y + off.y), size, size))

    def draw_flash(self, surf):
        if self.flash_t > 0:
            if self._flash_overlay is None or self._flash_overlay.get_size() != surf.get_size():
                self._flash_overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)   # один раз, а не каждый кадр
            alpha = int(255 * self.flash_t / self.flash_dur)
            self._flash_overlay.fill((*self.flash_color, alpha))
            surf.blit(self._flash_overlay, (0, 0))


def make_vignette(size):
    """Дешёвое псевдоосвещение: затемнение по краям."""
    surf = pygame.Surface(size, pygame.SRCALPHA)
    w, h = size
    for i in range(8):
        alpha = int(10 + i * 6)
        pygame.draw.rect(surf, (10, 5, 25, alpha), (i * 6, i * 4, w - i * 12, h - i * 8), 6)
    try:   # формат экрана — blit с прозрачностью быстрее
        if pygame.display.get_surface() is not None:
            return surf.convert_alpha()
    except (pygame.error, AttributeError):
        pass
    return surf
