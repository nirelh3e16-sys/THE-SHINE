"""Звук: процедурные сигналы + опциональные wav из assets/audio. Работает и без звука."""
import array
import math
import random

import pygame

from ..settings import ASSET_DIR, MUSIC_DIRS

# имя: (частота, длительность, форма, громкость, свип частоты)
SPECS = {
    "shoot": (700, 0.06, "square", 0.18, -300), "hit": (200, 0.07, "noise", 0.25, 0),
    "hurt": (160, 0.25, "square", 0.35, -100), "pickup": (600, 0.25, "square", 0.25, 600),
    "door": (120, 0.15, "square", 0.2, 80), "boss": (70, 0.8, "square", 0.4, -30),
    "death": (300, 0.9, "square", 0.4, -260), "story": (440, 0.5, "sine", 0.3, 220),
    "nuke": (90, 0.7, "noise", 0.5, 0), "dodge": (400, 0.1, "sine", 0.2, 200),
    "buy": (800, 0.12, "square", 0.25, 400),
}


MUSIC_TRACKS = {
    "combat": "Forest_Combat.mp3",         # боевые комнаты леса
    "calm": "Hollow_Sanctuary.mp3",        # магазины, сокровища, небоевые комнаты, после босса
    "boss": "spawn_of_darkness.mp3",       # бой с боссом
    "hell_combat": "Below_the_Bedrock.mp3",  # боевые комнаты Ада (если файла нет — играет трек Центра)
    "hell_boss": "The_Demon.mp3",         # бой с Бесом (если файла нет — трек финального боя)
    "shine_boss": "eternal_judgment.mp3",  # финальный бой с THE SHINE
    "center_combat": "Downtown.mp3",       # боевые комнаты Центра
    "chaos_boss": "CHAOS.mp3",             # бой с боссом Хаосом
    "city_combat": "Urban_Collapse.mp3",   # боевые комнаты Города
    "menu": "THE_SHINE.mp3",               # меню, экраны смерти и победы (и титры, когда появятся)
    "suburb_combat": "Suburban_Nightmare.mp3",  # боевые комнаты пригорода и домов
}
MUSIC_FALLBACK = {"hell_combat": "center_combat", "hell_boss": "shine_boss"}
MUSIC_GAIN = 0.7  # музыка немного тише эффектов


class MusicManager:
    """Зацикленные треки из папки mus/. Если файла нет или звук недоступен — тишина."""

    def __init__(self, enabled, volume):
        self.enabled = enabled
        self.volume = volume
        self.current = None
        self._glitching = False
        self._glitch_t = 0.0
        self.paths = {key: self._find(name) for key, name in MUSIC_TRACKS.items()}

    @staticmethod
    def _find(name):
        for folder in MUSIC_DIRS:
            if folder.is_dir():
                for f in folder.iterdir():
                    if f.name.lower() == name.lower():
                        return f
        return None

    def play(self, key):
        if not self.enabled or key == self.current:
            return
        self.current = key  # запоминаем даже при ошибке, чтобы не пытаться каждый кадр
        path = self.paths.get(key) or self.paths.get(MUSIC_FALLBACK.get(key))
        if path is None:
            pygame.mixer.music.stop()
            return
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(self.volume * MUSIC_GAIN)
            pygame.mixer.music.play(-1, fade_ms=500)
        except pygame.error:
            self.paths[key] = None

    def stop(self):
        self.current = None
        if self.enabled:
            pygame.mixer.music.stop()

    def set_volume(self, v):
        self.volume = v
        if self.enabled:
            pygame.mixer.music.set_volume(v * MUSIC_GAIN)

    def glitch_tick(self, active, dt):
        """Сбой звука (фаза 3 Хаоса): музыка то проваливается, то возвращается."""
        if not self.enabled:
            return
        if not active:
            if self._glitching:
                self._glitching = False
                pygame.mixer.music.set_volume(self.volume * MUSIC_GAIN)
            return
        self._glitching = True
        self._glitch_t -= dt
        if self._glitch_t <= 0:
            self._glitch_t = random.uniform(0.08, 0.35)
            pygame.mixer.music.set_volume(self.volume * MUSIC_GAIN * random.choice((0.1, 0.35, 1.0, 1.0)))


class AudioManager:
    def __init__(self, volume=0.6):
        self.volume = volume
        self.sounds = {}
        self.enabled = False
        self.glitch = False
        self.music = MusicManager(False, volume)
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(44100, -16, 2, 512)
            self.enabled = True
        except pygame.error:
            return
        self.music.enabled = True
        for name, spec in SPECS.items():
            self.sounds[name] = self._load(name, spec)

    def _load(self, name, spec):
        path = ASSET_DIR / "audio" / f"{name}.wav"
        if path.is_file():
            try:
                return pygame.mixer.Sound(str(path))
            except pygame.error:
                pass
        return self._synth(*spec)

    def _synth(self, freq, dur, shape, vol, sweep):
        rate, channels = pygame.mixer.get_init()[0], pygame.mixer.get_init()[2]
        n = int(rate * dur)
        buf = array.array("h")
        phase = 0.0
        rng = random.Random(1)
        for i in range(n):
            f = max(20.0, freq + sweep * i / n)
            phase += f / rate
            if shape == "square":
                v = 1.0 if (phase % 1.0) < 0.5 else -1.0
            elif shape == "noise":
                v = rng.uniform(-1, 1)
            else:
                v = math.sin(phase * 2 * math.pi)
            v *= (1 - i / n) * vol * 32000
            for _ in range(channels):
                buf.append(int(v))
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def set_volume(self, v):
        self.volume = max(0.0, min(1.0, v))
        self.music.set_volume(self.volume)

    def update_glitch(self, active, dt):
        self.glitch = active
        self.music.glitch_tick(active, dt)

    def play(self, name):
        snd = self.sounds.get(name)
        if snd is not None and self.enabled and self.volume > 0:
            if self.glitch and random.random() < 0.3:
                return  # часть звуков «пропадает»
            snd.set_volume(self.volume * (random.uniform(0.3, 1.0) if self.glitch else 1.0))
            snd.play()
