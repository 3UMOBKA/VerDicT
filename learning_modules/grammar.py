from typing import List, Tuple, Optional
import random
import re
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.types import Message, CallbackQuery
from db_layer.repository import next_sentence, get_random_words


class GrammarLearner:
    def __init__(self):
        self.current_sentence = None
        self.translation = ""
        self.word_position = 0
        self.translation_direction = None
        self.options = None

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




    def normalize_answer(self, answer: str) -> str:
        """
        Приведение строки к единому виду: удаление знаков препинания и приведение к нижнему регистру.
        """
        cleaned_answer = ''.join(char for char in answer if char.isalnum() or char.isspace()).strip().lower()
        return cleaned_answer

    def check_answer(self, user_answer: str) -> bool:
        """
        Проверяет правильность выбранного слова.
        """
        target_word = self.current_sentence.translation_en.split()[self.word_position]
        normalized_answer = self.normalize_answer(user_answer)
        normalized_target = self.normalize_answer(target_word)
        return normalized_answer == normalized_target

    def generate_options(self) -> List[str]:
        """
        Формирует четыре варианта ответов: один правильный и три неправильных.
        """
        # Определяем правильный ответ
        correct_answer = self.current_sentence.translation_en.split()[self.word_position]
        normalized_correct_answer = self.normalize_answer(correct_answer)

        # Получаем три случайных слова из базы данных, исключая правильный ответ
        all_words = get_random_words(count=10)  # Забираем побольше слов, чтобы выбрать уникальные
        wrong_words = [
            word for word in all_words
            if word.english_word != correct_answer and word.id != self.current_sentence.id
        ]
        wrong_words = random.sample(wrong_words, k=min(3, len(wrong_words)))  # Ограничиваем количество неправильных вариантов

        # Приводим неправильные ответы к единому формату
        wrong_answers_normalized = [self.normalize_answer(word.english_word) for word in wrong_words]

        # Объединяем правильный и неправильные варианты
        options = [normalized_correct_answer] + wrong_answers_normalized
        random.shuffle(options)
        return options[:4]



    def create_keyboard(self, options: list):
        """
        Создание клавиатуры с вариантами ответов.
        """
        buttons = []
        row_size = 2  # Размер ряда кнопок
        for i in range(0, len(options), row_size):
            row_buttons = []
            for j in range(i, min(i+row_size, len(options))):
                button = InlineKeyboardButton(text=options[j], callback_data=f'gw_{j}')
                row_buttons.append(button)
            buttons.append(row_buttons)
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        return keyboard

    def get_current_task(self) -> Optional[Tuple]:
        """
        Возвращает текущее задание или None, если предложений больше нет.
        """
        if self.current_sentence is None:
            success = self.next_sentence()
            if not success:
                return None
        self.options = self.generate_options()
        return self.current_sentence, self.options, self.translation_direction

    def reset_game(self):
        """
        Сброс состояния игры.
        """
        self.current_sentence = None
        self.translation = ""
        self.word_position = 0
        self.translation_direction = None
        self.options = None

    async def start_game(self, message: Message) -> None:
        """
        Запускает модуль GrammarLearner
        """
        self.reset_game()
        task = self.get_current_task()
        if task is None:
            await message.answer("Нет предложений для изучения.")
            return
    
        sentence, options, direction = task
        keyboard = self.create_keyboard(options)
        await message.answer(
            f"Переведите предложение:\n{sentence.text_ru}",
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    async def handle_callback(self, query: CallbackQuery):
        """Обрабатывает Callbacks GrammarLearner"""
        parts = query.data.split("_")
        if len(parts) != 2 or parts[0] != "gw":
            raise ValueError("Некорректный формат callback'a.")

        option_idx = int(parts[1])

        # Проверяем существование текущего предложения
        if not self.current_sentence:
            await query.message.answer("Нет активного предложения для перевода.")
            return

        # Генерируем новые варианты ответов
        current_options = self.generate_options()
        if not current_options:
            await query.message.answer("Не удалось создать варианты ответов.")
            return

        # Получаем индекс правильного ответа
        try:
            correct_answer_index = current_options.index(self.normalize_answer(self.current_sentence.translation_en.split()[self.word_position]))
        except IndexError:
            await query.message.answer("Ошибка в формировании вариантов ответов.")
            return

        # Проверяем, соответствует ли выбранный ответ правильному
        is_correct = option_idx == correct_answer_index

        # Обновляем перевод, учитывая выбор пользователя
        selected_answer = current_options[option_idx]
        self.translation += f"{selected_answer} "

        # Переходим к следующему слову
        self.word_position += 1
        expected_length = len(self.current_sentence.translation_en.split())

        if self.word_position >= expected_length:
            # Завершаем игру и показываем результат
            final_translation = self.translation.strip()
            original_sentence = self.current_sentence.text_ru
            translated_sentence = self.current_sentence.translation_en
            errors = self.find_errors(final_translation, translated_sentence)

            result_message = (
                f"<b>Исходное предложение:</b>\\n{original_sentence}\\n\\n"
                f"<b>Ваш перевод:</b>\\n{final_translation}\\n\\n"
                f"<b>Правильный перевод:</b>\\n{translated_sentence}\\n\\n"
                f"<b>Список ошибок:</b>\\n{errors}"
            )
            await query.message.answer(result_message, parse_mode="HTML")
            self.reset_game()
        else:
            new_task = self.get_current_task()
            if new_task:
                sentence, _, _ = new_task
                # Создаем новую клавиатуру с новыми вариантами
                options = self.generate_options()
                keyboard = self.create_keyboard(options)
                await query.message.edit_text(
                    f"Ваш перевод: {self.translation}\\nПереводите фразу '{sentence.text_ru}'",
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )


    async def start_default_mode(self, message: Message):
        # Начало игры в обычном режиме
        await message.answer("Начало стандартного режима.", reply_markup=ReplyKeyboardRemove())

        # Запрашиваем первое предложение
        sentence = next_sentence(self)
        if sentence:
            # Генератор вариантов ответов
            options = self.generate_options()
            keyboard = self.create_keyboard(options)

            # Отправляем вопрос и клавиатуру
            await message.answer(sentence.text_ru, reply_markup=keyboard)
        else:
            await message.answer("Нет больше предложений для перевода.")


    async def start_lesson_mode(self, message: Message, lesson_id: int):
        # Начинаем обучение по выбранному уроку
        await message.answer(f"Обучение началось по уроку №{lesson_id}.", reply_markup=ReplyKeyboardRemove())

        # Загружаем следующее предложение
        sentence = next_sentence(self)
        if sentence:
            # Подготавливаем список вариантов ответов
            options = self.generate_options()
            keyboard = self.create_keyboard(options)

            # Отсылаем задание игроку
            await message.answer(sentence.text_ru, reply_markup=keyboard)
        else:
            await message.answer("Больше предложений нет.")

    async def start_exam_mode(self, message: Message, exam_level: int):
        # Экзаменационная сессия началась
        await message.answer(f"Экзамен начался на уровне {exam_level}.", reply_markup=ReplyKeyboardRemove())

        # Первое предложение для экзаменуемого
        sentence = next_sentence(self)
        if sentence:
            # Готовим кнопки с возможными ответами
            options = self.generate_options()
            keyboard = self.create_keyboard(options)

            # Выдача задания на проверку
            await message.answer(sentence.text_ru, reply_markup=keyboard)
        else:
            await message.answer("Экзаменационные вопросы исчерпаны.")