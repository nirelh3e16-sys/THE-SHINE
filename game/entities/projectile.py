"""Снаряды игрока и врагов."""
import pygame

from ..settings import ROOM_X, ROOM_Y, ROOM_W, ROOM_H

BOUNDS = pygame.Rect(ROOM_X - 6, ROOM_Y - 6, ROOM_W + 12, ROOM_H + 12)


class Projectile:
    def __init__(self, pos, vel, damage, life, radius, friendly, color, pierce=False,
                 knockback=60.0, explode=False, poison=False, kind="shot"):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.damage = damage
        self.life = life
        self.radius = radius
        self.friendly = friendly
        self.color = color
        self.pierce = pierce
        self.knockback = knockback
        self.explode = explode
        self.poison = poison
        self.kind = kind
        self.dead = False
        self.hit = set()

    def update(self, dt, room):
        self.pos += self.vel * dt
        self.life -= dt
        if self.life <= 0 or not BOUNDS.collidepoint(self.pos):
            self.dead = True
            return
        if self.kind != "swing":
            for rect in room.obstacles:
                if rect.collidepoint(self.pos):
                    self.dead = True
                    return

    def draw(self, surf, off):
        x, y = int(self.pos.x + off.x), int(self.pos.y + off.y)
        if self.kind == "swing":
            pygame.draw.circle(surf, (255, 240, 200), (x, y), self.radius, 2)
            return
        r = max(2, int(self.radius))
        if not self.friendly:
            pygame.draw.circle(surf, (40, 10, 30), (x, y), r + 1)
        pygame.draw.circle(surf, self.color, (x, y), r)
        pygame.draw.circle(surf, (255, 255, 255), (x, y), max(1, r // 2))
