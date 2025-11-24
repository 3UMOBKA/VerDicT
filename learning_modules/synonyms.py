from typing import List, Dict, Tuple, NamedTuple, Optional
import random
import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import Message, CallbackQuery

from db_layer.models import Word
from db_layer.repository import get_random_relation_pair, get_random_words

logging.basicConfig(level=logging.DEBUG)

class GameResponse(NamedTuple):
    text: Optional[str]
    keyboard: Optional[InlineKeyboardMarkup]
    
class SynonymAntonymGame:
    def __init__(self):
        self.current_word = None
        self.relation_type = None
        self.options = []
        self.display_language = None  # Основной язык отображаемого слова
        self.related_word = None      # Связанное слово из таблицы relations

    def reset_game(self):
        """Сбрасываем состояние игры."""
        self.current_word = None
        self.relation_type = None
        self.options.clear()
        self.display_language = None
        self.related_word = None

    def next_question(self) -> bool:
        """
        Получение следующей случайной пары слов и типа связи.
        Возвращает True, если найдена новая пара, иначе False.
        """
        pair = get_random_relation_pair()
        if pair is None:
            return False
        self.current_word, self.relation_type, self.related_word = pair
        return True

    def normalize_answer(self, answer: str) -> str:
        """
        Приводит ответ пользователя к нормализованной форме: удаляются символы пунктуации, лишние пробелы и производится переход в нижний регистр.
        """
        cleaned_answer = ''.join(char for char in answer if char.isalpha() or char.isspace())
        return cleaned_answer.lower().strip()

    def check_answer(self, user_answer: str) -> bool:
        """
        Проверяет, соответствует ли введённый пользователем ответ правильному варианту.
        """
        normalized_answer = self.normalize_answer(user_answer)
        expected_answer = self.normalize_answer(self.options[self.correct_option_index])
        return normalized_answer == expected_answer

    def generate_options(self) -> List[str]:
        """
        Формирует четыре варианта ответов: три неправильных и один правильный.
        Правильный ответ определяется на основе связи в таблице relations.
        """
        if self.current_word is None or self.relation_type is None:
            return []

        # Основной язык текущего слова
        main_lang = "russian" if self.display_language == "russian" else "english"
        opposite_lang = "english" if main_lang == "russian" else "russian"

        # Определение правильного ответа на основе связи
        correct_answer = getattr(self.related_word, opposite_lang + "_word")

        # Неправильные варианты
        wrong_words = self.get_incorrect_options(opposite_lang)
        incorrect_options = [getattr(word, opposite_lang + "_word") for word in wrong_words[:3]]

        # Добавляем правильный ответ среди прочих
        all_options = incorrect_options + [correct_answer]
        random.shuffle(all_options)
        # Индексируем позицию правильного ответа
        self.correct_option_index = all_options.index(correct_answer)
        return all_options

    def get_incorrect_options(self, lang: str) -> List['Word']:
        """
        Получает три случайных слова, отличающихся от текущего слова и находящихся на указанном языке.
        """
        wrong_words = get_random_words(exclude_word_id=self.current_word.id)
        # Отфильтруем слова на указанный язык
        filtered_words = [word for word in wrong_words if getattr(word, lang + "_word")]
        return filtered_words[:3]

    def get_current_task(self) -> Optional[Tuple]:
        """
        Возвращает текущее задание (слово, тип связи и варианты ответов).
        """
        if self.current_word is None:
            found_new = self.next_question()
            if not found_new:
                return None
        # Случайно определяем основной язык
        languages = ["russian", "english"]
        self.display_language = random.choice(languages)
        displayed_word = (
            self.current_word.russian_word
            if self.display_language == "russian"
            else self.current_word.english_word
        )
        self.options = self.generate_options()
        return displayed_word, self.relation_type, self.options

    def create_keyboard(self, options: List[str]) -> InlineKeyboardMarkup:
        """
        Генерирует клавиатуру с вариантами ответов в виде матрицы 2x2.
        """
        buttons = []
        for i, option in enumerate(options):
            btn = InlineKeyboardButton(text=option, callback_data=f'sa_{i}')
            buttons.append(btn)
        rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
        keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
        return keyboard


    async def start_game(self, message: Message):
        """
        Начинает игровую сессию.
        """
        self.reset_game()
        task = self.get_current_task()
        if task is None:
            await message.answer("Нет слов для изучения.")
            return

        displayed_word, relation_type, options = task
        prompt = f"<b>{displayed_word}</b>\nТип связи: {relation_type}\nВыберите правильное слово:"
        keyboard = self.create_keyboard(options)
        await message.answer(prompt, reply_markup=keyboard, parse_mode='HTML')
    async def handle_callback(self, query: CallbackQuery):
        """Обрабатывает выбор пользователя и проверяет его ответ."""
        _, idx_str = query.data.split('_')
        option_idx = int(idx_str)
        user_answer = self.options[option_idx]
        is_correct = self.check_answer(user_answer)

        if is_correct:
            await query.answer("Верно! Отличная работа!", show_alert=True)
        else:
            await query.answer(f"Неверно. Правильный ответ: {self.options[self.correct_option_index]}.", show_alert=True)

        # Немедленно переходим к следующему заданию
        self.reset_game()                 # Сброс состояния игры
        next_task = self.get_current_task()  # Получаем новое задание
        if next_task:
            displayed_word, relation_type, options = next_task
            prompt = f"<b>{displayed_word}</b>\\nТип связи: {relation_type}\\nВыберите правильное слово:"
            keyboard = self.create_keyboard(options)
            await query.message.edit_text(prompt, reply_markup=keyboard, parse_mode='HTML')
        else:
            await query.message.answer("Игра закончена. Все слова изучены!")
