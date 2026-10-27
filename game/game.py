"""Главный объект игры: цикл, смена состояний, общие ресурсы."""
from types import SimpleNamespace

import pygame

from .entities.enemy import load_enemy_defs
from .play_state import PlayState
from .renderer import Display, Effects, make_vignette
from .save_system import SaveSystem
from .settings import FPS, GAME_W, GAME_H, MAX_DT, load_config
from .sprites import SpriteBook
from .ui.text import draw_text
from .steam import Steam
from .systems import characters as char_logic
from .states import (MenuState, SettingsState, IntroState, EndScreen, EndingState, CreditsState,
                     CharacterSelectState)
from .systems.audio import AudioManager
from .systems.events import load_events
from .systems.items import ItemDatabase


class Game:
    def __init__(self):
        self.cfg = load_config()
        self.save = SaveSystem()
        settings = self.save.data["settings"]
        self.data = SimpleNamespace(items=ItemDatabase.from_file(), enemies=load_enemy_defs(), events=load_events())
        self.characters = char_logic.load_characters(self.data.items)
        self.selected_char = char_logic.DEFAULT_ID
        self.steam = Steam()
        self.display = Display(self.cfg["window_scale"], self.cfg["fullscreen"], self.cfg.get("gpu_present", True))
        self.display.fill_mode = settings.get("fill", "blur")
        self.sprites = SpriteBook(list(self.data.items.items.values()), self.characters)
        self.audio = AudioManager(settings.get("volume", self.cfg["master_volume"]))
        self.effects = Effects(self.cfg["max_particles"], settings.get("screen_shake", True))
        self.vignette = make_vignette((GAME_W, GAME_H))
        self.clock = pygame.time.Clock()
        self.running = True
        self.show_fps = bool(settings.get("show_fps", False))
        self.audio.music.play("menu")
        self.state = MenuState(self)

    # --- переходы между состояниями ---
    def go_menu(self):
        self.audio.update_glitch(False, 0)
        self.audio.music.play("menu")
        self.effects.particles.clear()
        self.state = MenuState(self)

    def go_settings(self):
        self.state = SettingsState(self)

    def unlocked_chars(self):
        return char_logic.unlocked_ids(self.characters, self.save.data, self.cfg.get("unlock_all_characters", False))

    def new_game(self):
        """«Новая игра»: сначала выбор персонажа."""
        self.state = CharacterSelectState(self)

    def begin_run(self, char_id):
        if char_id not in self.unlocked_chars():
            return
        self.selected_char = char_id
        self.save.data["current_run"] = None
        self.effects.flash_t = 0
        if self.save.data["runs"] == 0:
            self.audio.music.stop()  # вступление идёт без музыки
            self.state = IntroState(self)
        else:
            self.start_new_run()

    def start_new_run(self):
        self.effects.flash_t = 0
        self.effects.particles.clear()
        self.state = PlayState(self)

    def continue_run(self):
        snap = self.save.data.get("current_run")
        try:
            self.state = PlayState(self, snap)
        except (KeyError, ValueError, TypeError):  # повреждённый снимок забега
            self.save.data["current_run"] = None
            self.save.write()
            self.start_new_run()

    def go_death(self, play):
        self.audio.update_glitch(False, 0)
        self.audio.music.play("menu")
        if play.zone.get("arena"):  # поражение от The Shine — плохая концовка
            self.go_ending(play, "bad")
            return
        self.state = EndScreen(self, play, False)

    def go_ending(self, play, kind):
        self.audio.update_glitch(False, 0)
        self.audio.music.play("menu")
        self.steam.unlock("ENDING_" + kind.upper())
        endings = self.save.data["endings"]
        if not play.cheated and kind not in endings:
            endings.append(kind)
            self.save.write()
        self.state = EndingState(self, play, kind)

    def go_credits(self):
        self.audio.music.play("menu")
        self.state = CreditsState(self)

    def go_victory(self, play):
        self.audio.update_glitch(False, 0)
        self.audio.music.play("menu")
        self.state = EndScreen(self, play, True)

    def quit(self):
        self.running = False

    @staticmethod
    def _combo(event, *second_keys):
        """F4 + клавиша (в любом порядке нажатия). F4 + 1 — счётчик FPS, F4 + T — тест-меню."""
        keys = pygame.key.get_pressed()
        if event.key == pygame.K_F4:
            return any(keys[k] for k in second_keys)
        return event.key in second_keys and keys[pygame.K_F4]

    # --- цикл ---
    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, MAX_DT)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.WINDOWFOCUSLOST:
                    handler = getattr(self.state, "on_focus_lost", None)
                    if handler:
                        handler()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.display.toggle_fullscreen()
                elif event.type == pygame.KEYDOWN and self._combo(event, pygame.K_t):
                    if isinstance(self.state, PlayState):  # тест-меню доступно только в игре
                        self.state.toggle_debug()
                elif event.type == pygame.KEYDOWN and self._combo(event, pygame.K_2, pygame.K_KP2):
                    if isinstance(self.state, PlayState):  # статистика персонажа — только в игре
                        self.state.toggle_stats()
                elif event.type == pygame.KEYDOWN and self._combo(event, pygame.K_1, pygame.K_KP1):
                    self.show_fps = not self.show_fps
                    self.save.data["settings"]["show_fps"] = self.show_fps
                else:
                    if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                        event.pos_game = self.display.to_game(event.pos)
                    self.state.handle_event(event)
            self.steam.update()
            self.state.update(dt)
            self.state.draw(self.display.surface)
            if self.show_fps:
                draw_text(self.display.surface, f"FPS {self.clock.get_fps():.0f}", (GAME_W - 6, 4), "gold", 9, "topright")
            self.display.present()
        self.save.write()
