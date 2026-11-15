"""Диалоговое окно: реплики и выбор вариантов."""
import pygame

from .text import draw_text, wrap
from ..settings import GAME_W, GAME_H


class DialogueBox:
    """Показывает текст и варианты. Результат — индекс выбранного варианта в self.choice."""

    def __init__(self, speaker, text, choices=None, enabled=None):
        self.speaker, self.text = speaker, text
        self.choices = choices or []
        self.enabled = enabled or [True] * len(self.choices)
        self.selected = 0
        self.choice = None
        self.done = False

    BOX = pygame.Rect(40, 60, GAME_W - 80, 150)

    def _choice_rects(self):
        """Прямоугольники вариантов ответа (общая раскладка для рисования и для мыши)."""
        box = self.BOX
        y = box.y + 24 + 13 * len(wrap(self.text, box.width - 16)) + 6
        return [pygame.Rect(box.x + 4, y + i * 13 - 1, box.width - 8, 13) for i in range(len(self.choices))]

    def handle_event(self, event):
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN) and hasattr(event, "pos_game"):
            if event.type == pygame.MOUSEBUTTONDOWN and event.button != 1:
                return
            if not self.choices:
                if event.type == pygame.MOUSEBUTTONDOWN:   # реплика без вариантов: клик — дальше
                    self.done = True
                return
            for i, rect in enumerate(self._choice_rects()):
                if rect.collidepoint(event.pos_game):
                    self.selected = i
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        self._pick()
                    break
            return
        if event.type != pygame.KEYDOWN:
            return
        if not self.choices:
            if event.key in (pygame.K_e, pygame.K_RETURN, pygame.K_SPACE):
                self.done = True
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % len(self.choices)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % len(self.choices)
        elif pygame.K_1 <= event.key <= pygame.K_9 and event.key - pygame.K_1 < len(self.choices):
            self.selected = event.key - pygame.K_1
            self._pick()
        elif event.key in (pygame.K_e, pygame.K_RETURN):
            self._pick()

    def _pick(self):
        if self.enabled[self.selected]:
            self.choice = self.selected
            self.done = True

    def draw(self, surf):
        box = self.BOX
        pygame.draw.rect(surf, (24, 16, 40), box)
        pygame.draw.rect(surf, (255, 215, 90), box, 1)
        draw_text(surf, self.speaker, (box.x + 8, box.y + 6), "gold", 12)
        y = box.y + 24
        for line in wrap(self.text, box.width - 16):
            draw_text(surf, line, (box.x + 8, y))
            y += 13
        y += 6
        for i, label in enumerate(self.choices):
            color = "white" if self.enabled[i] else "grey"
            prefix = "> " if i == self.selected else "  "
            draw_text(surf, f"{prefix}{i + 1}. {label}", (box.x + 8, y), "gold" if i == self.selected and self.enabled[i] else color)
            y += 13
        if not self.choices:
            draw_text(surf, "[E / клик] дальше", (box.right - 8, box.bottom - 6), "grey", 10, "bottomright")
