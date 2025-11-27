from typing import List, Tuple, Optional
import random
import re
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.types import Message, CallbackQuery
from db_layer.repository import next_sentence, get_random_words


class GrammarLearner:
    def __init__(self):
        self.current_sentence = None
        self.user_translation = []  # Накопленное предложение пользователя
        self.translation_direction = None
        self.options = None
        self.total_words_count = 0  # Всего слов в предложении
        self.completed_words = 0  # Кол-во выбранных слов
        self.mode = ""  # Режим игры (default, lesson:<id>, exam:<level>)

    def normalize_answer(self, answer: str) -> str:
        """
        Приведение строки к единому виду: удаление знаков препинания и преобразование в нижний регистр.
        """
        cleaned_answer = ''.join(char for char in answer if char.isalnum() or char.isspace()).strip().lower()
        return cleaned_answer

    def generate_options(self) -> List[str]:
        """
        Формирует четыре варианта ответов: один правильный и три неправильных.
        """
        # Выбор правильного ответа
        correct_answer = self.current_sentence.translation_en.split()[self.completed_words]
        normalized_correct_answer = self.normalize_answer(correct_answer)

        # Получение случайных неправильных слов
        wrong_words = get_random_words(count=10, exclude_word_id=self.current_sentence.id)
        wrong_words_filtered = [
            word for word in wrong_words
            if word.english_word != correct_answer
        ][:3]  # Используем максимум три уникальных неправильных слова

        # Преобразуем неправильные ответы в общий формат
        wrong_answers_normalized = [self.normalize_answer(word.english_word) for word in wrong_words_filtered]

        # Объединяем правильный и неправильные варианты
        options = [normalized_correct_answer] + wrong_answers_normalized
        random.shuffle(options)  # Перемешиваем варианты
        return options[:4]  # Возврат первых четырех элементов

    def create_keyboard(self, options: List[str]) -> InlineKeyboardMarkup:
        """
        Создание клавиатуры с вариантами ответов.
        """
        buttons = []
        row_size = 2  # Количество столбцов
        for i in range(0, len(options), row_size):
            row_buttons = []
            for j in range(i, min(i+row_size, len(options))):
                button = InlineKeyboardButton(text=options[j], callback_data=f'gw_{j}')
                row_buttons.append(button)
            buttons.append(row_buttons)
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        return keyboard

    def find_errors(self, user_translation: str, correct_translation: str) -> str:
        """
        Находит расхождения между переводами, игнорируя регистр и знаки препинания.
        """
        user_words = re.findall(r'\w+', user_translation.lower())
        correct_words = re.findall(r'\w+', correct_translation.lower())
    
        errors = []
        max_len = max(len(user_words), len(correct_words))
    
        for idx in range(max_len):
            u_word = user_words[idx] if idx < len(user_words) else ''
            c_word = correct_words[idx] if idx < len(correct_words) else ''
        
            if u_word != c_word:
                errors.append(f"Слово №{idx+1}: {u_word} → {c_word}")
    
        return '\n'.join(errors) if errors else "Нет ошибок!"

    def escape_md_v2(text: str) -> str:
        special_chars = r'_*\[]()~`>#+-={}|.!'
        for ch in special_chars:
            text = text.replace(ch, f'\\{ch}')
        return text


    async def load_next_question(self, message: Message):
        """
        Загрузка следующего вопроса независимо от режима.
        """
        # Получаем следующее предложение
        self.current_sentence = next_sentence(self)
        if self.current_sentence:
            self.total_words_count = len(self.current_sentence.translation_en.split())  # Всего слов в переводе
            self.user_translation = []  # Очищаем накопленный перевод
            self.completed_words = 0  # Счётчик переведённых слов
            self.options = self.generate_options()  # Первоначальные варианты ответов

            # Первая итерация: показываем клавиатуру
            keyboard = self.create_keyboard(self.options)
            await message.answer(
                f"Исходное предложение: `{self.current_sentence.text_ru}`\n\n"
                f"Текущий перевод: {' '.join(self.user_translation)}\n\n"
                f"Выбирайте следующую часть перевода:",
                reply_markup=keyboard,
                parse_mode="MarkdownV2"
            )
        else:
            await message.answer("Нет предложений для перевода.")

    async def handle_callback(self, query: CallbackQuery):
        """
        Обработчик нажатий на inline-кнопки.
        """
        data_parts = query.data.split('_')
        if len(data_parts) != 2 or data_parts[0] != 'gw':
            raise ValueError('Некорректный формат callback-data.')

        option_idx = int(data_parts[1])

        # Получаем выбранный вариант ответа
        chosen_option = self.options[option_idx]
        print(f"Selected Option: {chosen_option}, Current Translation: {' '.join(self.user_translation)}")  # Диагностика

        # Добавляем выбранное слово в перевод
        self.user_translation.append(chosen_option)
        self.completed_words += 1

        # Обновляем клавиатуру или показываем результат
        if self.completed_words < self.total_words_count:
            # Ещё не выбрали все слова
            self.options = self.generate_options()  # Новые варианты для следующего слова
            keyboard = self.create_keyboard(self.options)
            safe_message = GrammarLearner.escape_md_v2(f"Исходное предложение: `{self.current_sentence.text_ru}`\n\n"
                f"Текущий перевод: {' '.join(self.user_translation)}\n\n"
                f"Продолжайте выбирать!")
            await query.message.edit_text(safe_message, reply_markup=keyboard, parse_mode="MarkdownV2")
        else:
            # Все слова выбраны, проверяем перевод
            final_translation = ' '.join(self.user_translation).strip()
            errors = self.find_errors(final_translation, self.current_sentence.translation_en)

            result_message = GrammarLearner.escape_md_v2(
                f"Исходное предложение: `{self.current_sentence.text_ru}`\n\n"
                f"Ваш перевод: `{final_translation}`\n\n"
                f"Правильный перевод: `{self.current_sentence.translation_en}`\n\n"
                f"Результат: {errors}"
            )
            await query.message.answer(result_message, parse_mode="MarkdownV2")

            # Дальше грузим следующее задание или останавливаемся
            if self.mode.startswith("exam"):
                self.current_sentence = None
                self.user_translation.clear()
                self.completed_words = 0
                self.options = None
                
            else:
                await self.load_next_question(query.message)
    async def start_default_mode(self, message: Message):
        """
        Стандартный режим игры.
        """
        await message.answer("Начало стандартного режима.", reply_markup=ReplyKeyboardRemove())
        self.mode = "default"
        await self.load_next_question(message)

    async def start_lesson_mode(self, message: Message, lesson_id: int):
        """
        Учебный режим с фокусом на конкретные уроки.
        """
        await message.answer(f"Начало учебного режима по уроку №{lesson_id}.", reply_markup=ReplyKeyboardRemove())
        self.mode = f"lesson:{lesson_id}"  # Добавляем номер урока в режим
        await self.load_next_question(message)

    async def start_exam_mode(self, message: Message, exam_level: int):
        """
        Экзаменационный режим с повышенной нагрузкой.
        """
        await message.answer(f"Начало экзаменационного режима на уровне {exam_level}.", reply_markup=ReplyKeyboardRemove())
        self.mode = f"exam:{exam_level}"  # Добавляем уровень экзамена в режим
        await self.load_next_question(message)

