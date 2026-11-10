"""Локализация. Исходный язык игры — русский; английский перевод лежит в data/lang_en.json (ключ — русская строка).

Перевод применяется в момент отрисовки текста (см. ui/text.py), поэтому код игры и данные остаются на русском,
а логика (сравнения, сохранения) от языка не зависит. Язык по умолчанию — английский; переключается в настройках.

Как строка находит перевод:
1. точное совпадение;
2. шаблон с «{}» (так записаны строки, собранные f-строкой: «Комнат пройдено: {}»), части в «{}» переводятся отдельно;
3. запасной вариант для склеенных строк — замена всех известных фраз внутри (на границах слов).
Результат кэшируется, поэтому повторная отрисовка стоит один поиск в словаре.
Модуль не зависит от pygame.
"""
import json
import re
import sys
from pathlib import Path

DEFAULT_LANGUAGE = "en"
LANGUAGES = ("en", "ru")
LANGUAGE_NAMES = {"en": "English", "ru": "Русский"}
DATA_PATH = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "data" / "lang_en.json"   # как DATA_DIR в settings (и в собранном exe)

_CYRILLIC = re.compile("[А-Яа-яЁё]")
_BOUNDARY_L, _BOUNDARY_R = "(?<![А-Яа-яЁёA-Za-z])", "(?![А-Яа-яЁёA-Za-z])"
_CACHE_LIMIT = 6000


class Translator:
    def __init__(self, table=None, language=DEFAULT_LANGUAGE):
        self.language = language if language in LANGUAGES else DEFAULT_LANGUAGE
        self.table = {}
        self._patterns = []     # [(regex, шаблон)] для строк с «{}»
        self._phrases = None    # общая регулярка для замены известных фраз внутри строки
        self._cache = {}
        self.set_table(table or {})

    def set_table(self, table):
        self.table = {k: v for k, v in table.items() if isinstance(k, str) and isinstance(v, str)}
        self._patterns = []
        # шаблоны с двумя «{}» подряд неоднозначны (где кончается первая часть?), поэтому их пропускаем
        for key in sorted((k for k in self.table if "{}" in k and "{}{}" not in k), key=len, reverse=True):
            rx = re.escape(key).replace(r"\{\}", "(.+?)")
            self._patterns.append((re.compile(f"^{rx}$", re.DOTALL), self.table[key]))
        keys = sorted((k for k in self.table if "{}" not in k and len(k.strip()) >= 3), key=len, reverse=True)
        self._phrases = (re.compile("|".join(self._phrase_regex(k) for k in keys), re.DOTALL) if keys else None)
        self._cache.clear()

    @staticmethod
    def _phrase_regex(key):
        """Фраза внутри строки: граница слова нужна только там, где фраза начинается/кончается буквой
        (у ключей вроде «Новое свидетельство: » или « (сразу бой)» на краю пробел или скобка)."""
        left = _BOUNDARY_L if key[0].isalnum() else ""
        right = _BOUNDARY_R if key[-1].isalnum() else ""
        return left + re.escape(key) + right

    def set_language(self, language):
        self.language = language if language in LANGUAGES else DEFAULT_LANGUAGE
        self._cache.clear()

    def __call__(self, text):
        if self.language == "ru" or not text or not _CYRILLIC.search(text):
            return text
        hit = self._cache.get(text)
        if hit is not None:
            return hit
        out = self._translate(text)
        if len(self._cache) > _CACHE_LIMIT:
            self._cache.clear()
        self._cache[text] = out
        return out

    def _translate(self, text):
        exact = self.table.get(text)
        if exact is not None:
            return exact
        for rx, template in self._patterns:
            m = rx.match(text)
            if m:
                parts = iter(self(g) for g in m.groups())
                return re.sub(r"\{\}", lambda _: next(parts, ""), template)
        if self._phrases is not None:
            return self._phrases.sub(lambda m: self.table[m.group(0)], text)
        return text

    def missing(self, strings):
        """Какие из строк после перевода всё ещё содержат кириллицу (для проверки полноты перевода)."""
        return [s for s in strings if _CYRILLIC.search(self(s))]


def _load_table(path=DATA_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


_translator = Translator(_load_table())


def tr(text):
    """Перевести строку на текущий язык (по умолчанию английский). Незнакомая строка возвращается как есть."""
    return _translator(text)


def set_language(language):
    _translator.set_language(language)


def get_language():
    return _translator.language


def sanitize_language(value):
    return value if value in LANGUAGES else DEFAULT_LANGUAGE


def next_language(current):
    return LANGUAGES[(LANGUAGES.index(sanitize_language(current)) + 1) % len(LANGUAGES)]
