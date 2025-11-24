from typing import List, Dict, Tuple, NamedTuple, Optional
import random
import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import Message, CallbackQuery

from db_layer.repository import (
    get_random_words, get_single_random_word, get_single_random_word_from_lesson,
    add_or_update_metric_value, update_metric_value, search_records_by_word_pair, find_word_by_text
)

logging.basicConfig(level=logging.DEBUG)

class GameResponse(NamedTuple):
    text: Optional[str]
    keyboard: Optional[InlineKeyboardMarkup]

class WordLearner:
    def __init__(self):
        self.current_word = None
        self.translation_direction = None
        self.options = None

    def reset_game(self):
        """Сбрасываем игру для начала заново."""
        self.current_word = None
        self.translation_direction = None
        self.options = None

    def next_word(self, lesson_num: Optional[int] = None) -> bool:
        """
        Получение следующего слова из базы данных.

        Параметры:
            lesson_num (Optional[int]): Номер урока для ограничения поиска.

        Возвращает:
            bool: True, если найдено новое слово, иначе False.
        """
        try:
            if lesson_num is None:
                self.current_word = get_single_random_word()
            else:
                self.current_word = get_single_random_word_from_lesson(lesson_num)
            return self.current_word is not None
        except Exception as e:
            logging.error(f"Ошибка при получении нового слова: {e}")
            return False

    def normalize_answer(self, answer: str) -> str:
        """
        Нормализует ответ пользователя: удаляет лишние пробелы, знаки препинания и преобразует в нижний регистр.
        """
        cleaned_answer = ''.join(char for char in answer if char.isalpha() or char.isspace())
        return cleaned_answer.strip().lower()

    
    def check_answer(self, user_answer: str) -> bool:
        """
        Проверяет правильность ответа пользователя и обновляет метрику согласно выбранной стратегии.
        """
        # Нормализуем ответ пользователя
        normalized_answer = self.normalize_answer(user_answer)
        # Подготавливаем ожидаемый ответ
        expected_answer = self.normalize_answer(
            self.current_word.english_word if self.translation_direction == "ru->en" else self.current_word.russian_word
        )

        # Сравниваем ответ пользователя с правильным ответом
        is_correct = normalized_answer == expected_answer

        # Находим правильные и неправильные слова
        correct_word = find_word_by_text(expected_answer)
        incorrect_word = find_word_by_text(normalized_answer)

        # Начало обработки результатов
        if not is_correct and correct_word and incorrect_word and correct_word.id != incorrect_word.id:
            # Неправильный ответ: добавляем или обновляем связь между правильным и неправильным ответом
            add_or_update_metric_value(correct_word.id, incorrect_word.id)

        return is_correct





    def generate_options(self) -> List[str]:
        """
        Формирует варианты ответов, включая правильный и три неправильных варианта.
        Устанавливает случайное направление перевода.
        """
        self.translation_direction = random.choice(["en->ru", "ru->en"])
        correct_answer = (
            self.current_word.english_word if self.translation_direction == "ru->en" else self.current_word.russian_word
        )
        wrong_words = self.get_incorrect_options(self.current_word.id)
        options = [correct_answer] + wrong_words[:3]
        random.shuffle(options)
        return options

    def get_incorrect_options(self, exclude_word_id: int) -> List[str]:
        """
        Получает три случайных слова из базы данных, кроме указанного.
        Исключает совпадения с правильным ответом.
        """
        random_words = get_random_words(exclude_word_id)
        filtered_words = [
            w.english_word if self.translation_direction == "ru->en" else w.russian_word
            for w in random_words
        ]
        return filtered_words

    def get_current_task(self, lesson_num: Optional[int] = None) -> Optional[Tuple]:
        """
        Возвращает текущее задание или None, если слов больше нет.
        Может ограничивать слова определенным уроком.
        """
        if self.current_word is None:
            if not self.next_word(lesson_num):
                return None
        self.options = self.generate_options()
        return self.current_word, self.options, self.translation_direction

    def create_keyboard(self, options: list):
        """
        Генерирует клавиатуру с вариантами ответов в виде матрицы 2x2.
        Перемешиваем варианты, чтобы правильный ответ располагался случайно.
        """
        random.shuffle(options)
        buttons = []
        for i in range(0, len(options), 2):
            row_buttons = []
            for j in range(i, min(i+2, len(options))):
                button = InlineKeyboardButton(text=options[j], callback_data=f"answer_{j}")
                row_buttons.append(button)
            buttons.append(row_buttons)
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        return keyboard

    async def start_default_mode(self, message: Message):
        """
        Старт стандартного режима игры со случайными словами.
        """
        self.reset_game()
        task = self.get_current_task()
        if task is None:
            await message.answer("Нет слов для изучения.")
            return
        word, options, direction = task
        title = "<b>Слово:</b>" if direction == "en->ru" else "<b>Перевод:</b>"
        prompt = "Какой перевод?" if direction == "en->ru" else "Английское слово?"
        keyboard = self.create_keyboard(options)
        await message.answer(
            f"{title} {word.english_word if direction == 'en->ru' else word.russian_word}\n{prompt}",
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    async def start_lesson_mode(self, message: Message, lesson_num: int):
        """
        Запуск учебного режима по указанному уроку.
        """
        self.reset_game()
        task = self.get_current_task(lesson_num)
        if task is None:
            await message.answer("Нет слов для изучаемого урока.")
            return
        word, options, direction = task
        title = "<b>Слово:</b>" if direction == "en->ru" else "<b>Перевод:</b>"
        prompt = "Какой перевод?" if direction == "en->ru" else "Английское слово?"
        keyboard = self.create_keyboard(options)
        await message.answer(
            f"{title} {word.english_word if direction == 'en->ru' else word.russian_word}\n{prompt}",
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    async def start_exam_mode(self, message: Message):
        """
        Экзаменационный режим. Генерация единственного задания и возврат управления.
        """
        self.reset_game()
        task = self.get_current_task()
        if task is None:
            await message.answer("Нет слов для экзамена.")
            return
        word, options, direction = task
        title = "<b>Слово:</b>" if direction == "en->ru" else "<b>Перевод:</b>"
        prompt = "Какой перевод?" if direction == "en->ru" else "Английское слово?"
        keyboard = self.create_keyboard(options)
        await message.answer(
            f"{title} {word.english_word if direction == 'en->ru' else word.russian_word}\n{prompt}",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
