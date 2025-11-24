from typing import NamedTuple, Optional
import random
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery

from db_layer.repository import save_user_progress


    
class GameResponse(NamedTuple):
    text: Optional[str]
    keyboard: Optional[InlineKeyboardMarkup]

class Game_flashcards:
    
    async def handle_callback(self, query: CallbackQuery):
        parts = query.data.split("_")
        if len(parts) != 2 or parts[0] != "wl":
            raise ValueError("Некорректный формат callback'a.")
        
        option_idx = int(parts[1])
        current_options = self.generate_options()
        user_answer = current_options[option_idx]
        
        is_correct = self.check_answer(user_answer)
        if is_correct:
            await query.answer("Правильно! Молодец!", show_alert=True)
        else:
            correct_answer = self.current_word.russian_word if self.translation_direction == "en->ru" else self.current_word.english_word
            await query.answer(f"Неправильно. Правильный ответ: {correct_answer}", show_alert=True)
    
        # Сохраняем прогресс пользователя
        save_user_progress(query.from_user.id, self.current_word.id, is_correct)
        
        # Переход к следующему слову
        next_word_available = self.next_word()
        if next_word_available:
            new_task = self.get_current_task()
            if new_task:
                word, options, direction = new_task
                title = "Слово:" if direction == "en->ru" else "Перевод:"
                prompt = "Какой перевод?" if direction == "en->ru" else "Английское слово?"
                await query.message.edit_text(
                    f"{title} {word.english_word if direction == 'en->ru' else word.russian_word}\\n{prompt}",
                    reply_markup=self.create_keyboard(options)
                )
            else:
                await query.message.answer("Больше слов нет. Игра окончена.", reply_markup=None)
        else:
            await query.message.answer("Нет следующего слова. Изучение завершено.", reply_markup=None)
            
            
            
    def __init__(self):
        self.proposals = [
            "Это пример простого предложения",
            "Мы изучаем русский язык",
            "Книга лежит на столе"
        ]
        self.translations_map = {
            "Это": ["This"],
            "пример": ["example"],
            "простого": ["simple"],
            "предложения": ["sentence"],
            "Мы": ["We"],
            "изучаем": ["study"],
            "русский": ["Russian"],
            "язык": ["language"],
            "Книга": ["Book"],
            "лежит": ["lies"],
            "на": ["on"],
            "столе": ["table"]
        }
        self.user_progress = {}

    def generate_options(self, word: str) -> list:
        all_translations = set.union(*map(set, self.translations_map.values()))
        correct_answer = self.translations_map[word][0]  # Выбор правильного перевода
        wrong_answers = list(all_translations - {correct_answer})
        num_wrongs = min(len(wrong_answers), 3)
        wrong_samples = random.sample(wrong_answers, num_wrongs)
        options = [correct_answer] + wrong_samples
        random.shuffle(options)
        return options
        
    def create_keyboard(self, options: list, word: str) -> InlineKeyboardMarkup:
        """
        Создаёт клавиатуру с вариантами ответов, располагающими кнопки в виде сетки 2×2.
        """
        buttons = [
            InlineKeyboardButton(text=option, callback_data=f"fc_{word}_{idx}")
            for idx, option in enumerate(options)
        ]
        # Делим кнопки на строки по 2 шт., образуя сетку 2×2
        rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
        keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
        return keyboard

    def start_game(self, user_id: int) -> GameResponse:
        if len(self.proposals) > 0:
            proposal = random.choice(self.proposals)
            self.user_progress[user_id] = {
                'proposal': proposal,
                'current_word_idx': 0,
                'selected_words': [],
                'total_attempts': 0,
                'correct_answers': 0,
                'options': []  # Список вариантов ответов
            }
            first_word = proposal.split()[0]
            options = self.generate_options(first_word)
            self.user_progress[user_id]['options'] = options
            keyboard = self.create_keyboard(options, first_word)
            return GameResponse(
                text=f"Ваше предложение: '{proposal}'\nПереведите слово '{first_word}'.",
                keyboard=keyboard
            )
        else:
            return GameResponse(text="Нет доступных предложений.", keyboard=None)
        
    def check_answer(self, user_id: int, button_data: str) -> GameResponse:
        parts = button_data.split('_')  # ФОРМАТ: "fc_слово_номер"
        if len(parts) != 3:
            return GameResponse(text="Некорректный формат callback_data.", keyboard=None)
        
        _, current_word, selected_option = parts
        
        progress = self.user_progress.get(user_id)
        if not progress or current_word != progress['proposal'].split()[progress['current_word_idx']]:
            return GameResponse(text="Игра закончилась.", keyboard=None)
        
        options = progress['options']
        correct_answer = self.translations_map[current_word][0]
        chosen_answer = options[int(selected_option)]
        
        if chosen_answer == correct_answer:
            result_message = f"Правильно! Слово '{current_word}' переведено верно."
            progress['correct_answers'] += 1
        else:
            result_message = f"Неправильно! Правильный перевод слова '{current_word}' — '{correct_answer}'."
        
        next_word_idx = progress['current_word_idx'] + 1
        words_in_proposal = progress.get('proposal', '').split()
        
        if next_word_idx >= len(words_in_proposal):
            final_score = f"Игра закончена. Количество правильных ответов: {progress['correct_answers']} из {len(words_in_proposal)}"
            del self.user_progress[user_id]
            return GameResponse(text=final_score, keyboard=None)
        else:
            new_word = words_in_proposal[next_word_idx]
            new_options = self.generate_options(new_word)
            progress['current_word_idx'] = next_word_idx
            progress['options'] = new_options
            keyboard = self.create_keyboard(new_options, new_word)
            return GameResponse(
                text=f"{result_message}\nСледующее слово: '{new_word}', выберите перевод.",
                keyboard=keyboard
            )