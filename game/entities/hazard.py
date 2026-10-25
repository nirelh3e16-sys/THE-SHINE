"""Опасные зоны арены (косилки, падающие предметы): предупреждение, затем урон."""
import math

import pygame

from ..collision import circle_rect_overlap


class Hazard:
    """Опасная зона: сначала предупреждение (warmup), затем наносит урон. Может двигаться."""

    def __init__(self, rect, damage=2, warmup=1.0, life=0.3, vel=(0, 0), warn_rect=None, kind="zone"):
        self.rect = pygame.Rect(rect)
        self.pos = pygame.Vector2(self.rect.topleft)
        self.vel = pygame.Vector2(vel)
        self.damage, self.warmup, self.life, self.kind = damage, warmup, life, kind
        self.warn_rect = pygame.Rect(warn_rect) if warn_rect is not None else self.rect.copy()
        self.dead = False

    @property
    def active(self):
        return self.warmup <= 0

    @property
    def center(self):
        return pygame.Vector2(self.rect.center)

    def hits(self, pos, radius):
        return circle_rect_overlap(pos, radius, self.rect)

    def update(self, dt):
        if self.warmup > 0:
            self.warmup -= dt
            return
        self.pos += self.vel * dt
        self.rect.topleft = (int(self.pos.x), int(self.pos.y))
        self.life -= dt
        if self.life <= 0:
            self.dead = True

    def draw(self, surf, off):
        if not self.active:
            if int(pygame.time.get_ticks() / 90) % 2:
                pygame.draw.rect(surf, (255, 70, 70), self.warn_rect.move(off.x, off.y), 2)
            return
        r = self.rect.move(off.x, off.y)
        if self.kind == "wing":
            pygame.draw.rect(surf, (255, 250, 220), r)
            pygame.draw.rect(surf, (255, 205, 80), r, 3)
        elif self.kind == "mower":
            pygame.draw.rect(surf, (200, 50, 50), r)
            pygame.draw.rect(surf, (255, 210, 60), r.inflate(-8, -8))
            pygame.draw.rect(surf, (34, 24, 48), r, 2)
        else:
            pygame.draw.rect(surf, (255, 230, 150), r)
            pygame.draw.rect(surf, (230, 60, 60), r, 2)


class Laser:
    """Луч: сначала тонкая мигающая линия-предупреждение, затем короткий мощный удар."""

    def __init__(self, origin, angle, warmup=1.0, life=0.4, width=12, damage=2, length=700):
        self.origin = pygame.Vector2(origin)
        self.dir = pygame.Vector2(math.cos(angle), math.sin(angle))
        self.warmup, self.life, self.width, self.damage, self.length = warmup, life, width, damage, length
        self.dead = False
        self.kind = "laser"

    @property
    def active(self):
        return self.warmup <= 0

    @property
    def center(self):
        return self.origin

    def update(self, dt):
        if self.warmup > 0:
            self.warmup -= dt
            return
        self.life -= dt
        if self.life <= 0:
            self.dead = True

    def hits(self, pos, radius):
        t = max(0.0, min(self.length, (pos - self.origin).dot(self.dir)))
        closest = self.origin + self.dir * t
        return closest.distance_to(pos) <= self.width / 2 + radius

    def draw(self, surf, off):
        a = (self.origin.x + off.x, self.origin.y + off.y)
        b = (a[0] + self.dir.x * self.length, a[1] + self.dir.y * self.length)
        if not self.active:
            if int(pygame.time.get_ticks() / 80) % 2:
                pygame.draw.line(surf, (255, 70, 70), a, b, 1)
            return
        pygame.draw.line(surf, (255, 240, 170), a, b, self.width)
        pygame.draw.line(surf, (255, 255, 255), a, b, max(2, self.width // 3))
