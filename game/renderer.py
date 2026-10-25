"""Окно, масштабирование без искажений, эффекты (частицы, тряска, вспышки)."""
import math
import random

import pygame

from .settings import GAME_W, GAME_H


class Display:
    def __init__(self, scale=2, fullscreen=False):
        self.surface = pygame.Surface((GAME_W, GAME_H))
        self.fullscreen = fullscreen
        self.scale = max(1, int(scale))
        self._create_window()
        self._offset = (0, 0)
        self._fx = self._fy = 1.0
        self.fill_mode = "blur"   # "blur" — размытое продолжение кадра по краям, "stretch" — растянуть
        self._shade = None

    def _create_window(self):
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
            win.blit(pygame.transform.scale(self.surface, (ww, wh)), (0, 0))
            pygame.display.flip()
            return
        factor = min(ww / GAME_W, wh / GAME_H)
        if factor >= 1:
            factor = float(int(factor))
        size = (max(1, int(GAME_W * factor)), max(1, int(GAME_H * factor)))
        self._offset = ((ww - size[0]) // 2, (wh - size[1]) // 2)
        self._fx = self._fy = factor
        if size[0] < ww or size[1] < wh:
            self._draw_ambient(win, (ww, wh))
        win.blit(pygame.transform.scale(self.surface, size), self._offset)
        pygame.display.flip()

    def _draw_ambient(self, win, win_size):
        """Вместо чёрных полос — размытое затемнённое продолжение кадра."""
        tiny = pygame.transform.smoothscale(self.surface, (32, 18))
        win.blit(pygame.transform.smoothscale(tiny, win_size), (0, 0))
        if self._shade is None or self._shade.get_size() != win_size:
            self._shade = pygame.Surface(win_size, pygame.SRCALPHA)
            self._shade.fill((10, 5, 20, 120))
        win.blit(self._shade, (0, 0))

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
            overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            alpha = int(255 * self.flash_t / self.flash_dur)
            overlay.fill((*self.flash_color, alpha))
            surf.blit(overlay, (0, 0))


def make_vignette(size):
    """Дешёвое псевдоосвещение: затемнение по краям."""
    surf = pygame.Surface(size, pygame.SRCALPHA)
    w, h = size
    for i in range(8):
        alpha = int(10 + i * 6)
        pygame.draw.rect(surf, (10, 5, 25, alpha), (i * 6, i * 4, w - i * 12, h - i * 8), 6)
    return surf
