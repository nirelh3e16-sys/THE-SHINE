"""Скрытые грехи и журнал свидетельств. Числа игроку не показываются."""
import random

from ..save_system import SINS

TESTIMONIES = {
    "helped_dog": ("Пёс в кустах", "Ты полез в колючие кусты ради чужой собаки. Никто не просил тебя быть добрым."),
    "stole_from_man": ("Чужой бумажник", "Ты украл у человека, который доверчиво смотрел в сторону."),
    "witness_saw": ("Вчера и позавчера", "Незнакомец утверждает, что видел тебя здесь много раз. В одной и той же пижаме."),
    "killed_peaceful": ("Он не удивился", "Ты ударил того, кто просто хотел поговорить. Он, кажется, ждал этого."),
    "saw_shine_corner": ("Крыло в углу", "Нечто огромное наблюдало за тобой из угла комнаты и исчезло."),
    "altar_blood": ("Цена силы", "Ты отдал часть себя алтарю ради силы."),
    "altar_prayer": ("Молитва без ответа", "Ты помолился. Тебе показалось, что кто-то слушает."),
    "memory_photo": ("Проявленная фотография", "На снимке — твоя спальня. Занавески закрыты. Ты спишь. Или нет."),
    "garage_theft": ("Коробка с фотографиями", "Ты украл коробку с чужого стола. Фотографии в ней были твои."),
    "lied_to_child": ("Мама ждёт дома", "Ты соврал ребёнку. Он тебе поверил. Это хуже всего."),
    "told_child_truth": ("Скрип качелей", "Ты сказал мальчику правду. Он тебе тоже поверил."),
    "took_child_candy": ("Шоколадка", "Ты забрал последнюю сладость у ребёнка, потерявшего маму."),
    "house_explored": ("Тёплые тарелки", "В доме никого не было. Но на кухне тарелки ещё были тёплыми."),
    "neighbor_slain": ("Сосед", "Он просто хотел идеальный газон. Теперь ему всё равно."),
    "city_sermon": ("Проповедь с крыши", "Человек с мегафоном говорил, что спасение — это очередь. Очередь не движется."),
    "preacher_robbed": ("Мегафон", "Ты отобрал мегафон у проповедника. Теперь он просто шепчет."),
    "saw_shine_billboard": ("Лицо на билборде", "Рекламный щит улыбался чужой улыбкой. Потом подмигнул."),
    "mayor_slain": ("Мэр", "Он подписывал всё подряд, лишь бы не читать. Последняя подпись была твоя."),
    "slept_in_bedroom": ("Тёплая подушка", "Ты лёг спать посреди улицы, в чужой копии своей спальни. Это было слишком уютно."),
    "opened_curtains_again": ("Занавески, ещё раз", "Ты открыл занавески снова. За окном всё то же. Или это ты всё тот же."),
    "traded_memory": ("Сданное воспоминание", "Ты отдал воспоминание за вещь. Что именно — уже не вспомнить."),
    "chaos_slain": ("Хаос", "Он был ошибкой, которую допустили специально. Ты исправил её. Кажется, именно этого и ждали."),
    "shine_defeated": ("Судья", "Ты победил того, кто всё это устроил. Он не выглядел удивлённым."),
    "shine_was_human": ("Он был человеком", "THE SHINE когда-то открыл занавески в Гамбургере, штат Киш. Он прошёл то же испытание и остался частью системы."),
    "imp_slain": ("Бес", "Он ждал тебя и следил за тобой. Его сын был падшим бесом, и ты это знаешь."),
    "devil_deal": ("Договор", "Ты подписал договор на алтаре в Аду. Условия, как всегда, были мелким шрифтом."),
    "lumberjack_slain": ("Лесник", "Лесник рубил деревья, пока лес не начал рубить в ответ. Теперь он тих."),
}

# Секретная концовка открывается, когда собраны ВСЕ эти свидетельства (суммарно по всем забегам)
SECRET_REQUIRED = ("saw_shine_corner", "saw_shine_billboard", "witness_saw", "memory_photo")

SIN_VERDICTS = {
    "greed": "Жадность. Ты всегда брал больше.",
    "sloth": "Лень. Ты слишком часто уходил.",
    "aggression": "Агрессия. Ты слишком охотно бил.",
    "egoism": "Эгоизм. Ты думал о себе.",
    "cunning": "Хитрость. Ты слишком ловко выкручивался.",
    "mercy": "Милосердие. Подозрительно. Что тебе нужно?",
}


class Morality:
    def __init__(self, run_seed=0, legacy_testimonies=None):
        self.run_sins = {s: 0 for s in SINS}
        self.run_testimonies = []
        self._legacy = set(legacy_testimonies or [])
        self._rng = random.Random(run_seed)

    def add_sin(self, name, amount):
        if name not in self.run_sins:
            raise ValueError(f"неизвестный грех: {name}")
        self.run_sins[name] = max(0, self.run_sins[name] + amount)

    def add_testimony(self, tid):
        """True, если свидетельство получено впервые в этом забеге."""
        if tid not in TESTIMONIES:
            raise ValueError(f"неизвестное свидетельство: {tid}")
        if tid in self.run_testimonies:
            return False
        self.run_testimonies.append(tid)
        return True

    def all_testimonies(self):
        """Свидетельства за все забеги (долгосрочные данные)."""
        return sorted(self._legacy | set(self.run_testimonies))

    def secret_unlocked(self):
        have = set(self.all_testimonies())
        return all(t in have for t in SECRET_REQUIRED)

    def secret_progress(self):
        have = set(self.all_testimonies())
        return sum(1 for t in SECRET_REQUIRED if t in have)

    def verdict(self):
        """Вердикт The Shine. Он может ошибиться — и событие-улика важнее чисел."""
        if "killed_peaceful" in self.run_testimonies:
            return "Убийца. Тут и считать нечего."
        total = sum(self.run_sins.values())
        if total == 0:
            return "Пусто. Это тоже грех."
        dominant = max(SINS, key=lambda s: (self.run_sins[s], s))
        if self._rng.random() < 0.3:
            dominant = self._rng.choice([s for s in SINS if s != dominant])
        return SIN_VERDICTS[dominant]
