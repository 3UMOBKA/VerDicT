import logging
from aiogram import Router
from aiogram.filters.command import Command
from aiogram.types import Message, CallbackQuery
from learning_modules.synonyms import SynonymAntonymGame
from learning_modules.words import WordLearner
from learning_modules.grammar import GrammarLearner
from lessons.chooselessons import ChooseLessons, CallbackLessons
from bot_core.system_commands import System_commands
from aiogram.types import ReplyKeyboardRemove
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from db_layer.repository import get_lessons_from_db

# Создаем роутер для обработки команд и сообщений
router = Router()

# Инициализация игровых модулей
synonym_antonym_game = SynonymAntonymGame()
word_learner = WordLearner()
grammar_learner = GrammarLearner()
lessons = ChooseLessons()

# Обработчики команд

@router.message(Command("view_buttons"))
async def view_button(message: Message):
    """
    Показывает клавиатуру с кнопками.
    """
    await System_commands.view_button(message)

@router.message(Command("hide_buttons"))
async def hide_buttons(message: Message):
    """
    Скрывает клавиатуру с кнопками.
    """
    await message.reply("Клавиатура скрыта.", reply_markup=ReplyKeyboardRemove())

# Основной обработчик команды /start
@router.message(Command("start"))
async def start_command(message: Message):
    await System_commands.menu(message)

# Основной обработчик команды /menu
@router.message(Command("menu"))
async def menu(message: Message):
    await System_commands.menu(message)

# Обработчик команды /learn_words
@router.message(Command("learn_words"))
async def learn_words_command(message: Message):
    """
    Команда для старта изучения слов.
    Предоставляет пользователю выбор: обычный режим, изучение по уроку или экзамены.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Обычный режим", callback_data='wl_sd')],
        [InlineKeyboardButton(text="По уроку", callback_data='wl_st')],
    ])
    await message.answer("Выберите режим обучения:", reply_markup=keyboard)

# Обработчик колбеков для выбора режима обучения слов
@router.callback_query(lambda call: call.data.startswith('wl_'))
async def process_word_learning_modes(call: CallbackQuery):
    data_parts = call.data.split('_')
    mode = data_parts[1]
    lesson = None
    if len(data_parts) > 2:
        lesson = data_parts[2]
    
    match mode:
        case 'sd':  # Обычный режим
            await word_learner.start_default_mode(call.message)
        case 'st':  # Изучение по уроку
            if lesson is None:
                await choose_lesson_wl(call.message)  # Пользователь выбирает урок
            else:
                await word_learner.start_lesson_mode(call.message, int(lesson))
        case 'se':  # Экзаменационные задания
            await word_learner.start_exam_mode(call.message)
        case _:
            await call.answer("Неверный выбор режима", show_alert=True)

# Выбор урока
async def choose_lesson_wl(message: Message):
    lessons_list = await get_lessons_from_db()  # Получаем уникальный список уроков
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Урок {lesson[0]}", callback_data=f"wl_st_{lesson[0]}")] for lesson in lessons_list
    ])  # Каждую кнопку помещаем в отдельный список
    await message.answer("Выберите урок:", reply_markup=keyboard)

# Обработчик колбеков для выбора ответа
@router.callback_query(lambda call: call.data.startswith('answer_wl_'))
async def process_user_answers(call: CallbackQuery):
    option_idx = int(call.data.split('_')[2])
    selected_answer = word_learner.options[option_idx]
    is_correct = word_learner.check_answer(selected_answer)
    mode = call.data.split('_')[3]
    if is_correct:
        await call.answer("Правильно! Молодец!")
    else:
        correct_answer = word_learner.current_word.english_word if word_learner.translation_direction == "ru->en" else word_learner.current_word.russian_word
        await call.answer(f"Неправильно. Правильный ответ: {correct_answer}")
    match mode:
        case "lesson":
            await word_learner.start_lesson_mode(call.message, call.data.split('_')[4])
        case "default":
            await word_learner.start_default_mode(call.message)
        case "exam":
            pass
        

# === Новое: обработка грамматического режима ===
# Обработчик для выбора урока
async def choose_lesson_gl(message: Message):
    lessons_list = await get_lessons_from_db()  # Получаем уникальный список уроков
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Урок {lesson[0]}", callback_data=f"gl_st_{lesson[0]}")] for lesson in lessons_list
    ])  # Каждую кнопку помещаем в отдельный список
    await message.answer("Выберите урок:", reply_markup=keyboard)


# Обработчик процесса выбора режима обучения
@router.callback_query(lambda call: call.data.startswith('gl_'))
async def process_grammar_learning_modes(call: CallbackQuery):
    data_parts = call.data.split('_')
    mode = data_parts[1]
    lesson = None
    if len(data_parts) > 2:
        lesson = data_parts[2]
    
    match mode:
        case 'sd':  # Обычный режим
            await grammar_learner.start_default_mode(call.message)  # Без await, если метод синхронный
        case 'st':  # Изучение по уроку
            if lesson is None:
                await choose_lesson_gl(call.message)  # Этот метод асинхронный
            else:
                await grammar_learner.start_lesson_mode(call.message, int(lesson))  # Нужен await
        case 'se':  # Экзаменационный режим
            await grammar_learner.start_exam_mode(call.message, 3)  # Так же нужен await
        case _:
            await call.answer("Неверный выбор режима", show_alert=True)

# Обработчик команды /grammar
@router.message(Command("grammar_game"))
async def grammar_command(message: Message):
    """
    Команда для старта изучения грамматики.
    Предоставляет пользователю выбор: обычный режим, изучение по уроку или экзамены.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Обычный режим", callback_data='gl_sd')],
        [InlineKeyboardButton(text="По уроку", callback_data='gl_st')],
    ])
    await message.answer("Выберите режим обучения грамматики:", reply_markup=keyboard)


# Обработчик колбека для выбора урока
@router.callback_query(lambda call: call.data.startswith('wl_st'))
async def process_chosen_lesson(call: CallbackQuery):
    _, _, lesson_num = call.data.split('_')
    lesson_num = int(lesson_num)
    await word_learner.start_lesson_mode(call.message, lesson_num)

# Обработчик команды /play_synonyms
@router.message(Command("play_synonyms"))
async def play_synonyms_command(message: Message):
    await synonym_antonym_game.start_game(message)

# Обработчик команды /grammar_game
@router.message(Command("grammar_game"))
async def grammar_game_handler(message: Message):
    await grammar_learner.start_game(message)

# Обработчик команды /lessons
@router.message(Command("lessons"))
async def start_lessons_list_command(message: Message):
    await lessons.show_lessons_list(message)

# Обработка колбеков
@router.callback_query()
async def handle_callback_queries(query: CallbackQuery):
    try:
        parts = query.data.split('_')
        if len(parts) >= 1:
            prefix = parts[0]
            if prefix == 'wl':  # Колбеки от WordLearner
                await word_learner.handle_callback(query)
            elif prefix == 'sa':  # Колбеки от SynonymAntonymGame
                await synonym_antonym_game.handle_callback(query)
            elif prefix == 'gw':  # Колбеки от GrammarLearner
                await grammar_learner.handle_callback(query)
            elif prefix == 'lesson':  # Колбеки от уроков
                await CallbackLessons.select_lesson_pages(query)
            elif prefix == 'page':  # Колбеки страниц
                await CallbackLessons.send_page_content(query)
            elif prefix == 'return_to_lessons_list':  # Возврат к списку уроков
                await lessons.show_lessons_list(query)
        else:
            await query.answer("Неизвестный тип callback'а.", show_alert=True)
    except Exception as e:
        logging.error(f"Ошибка при обработке callback: {e}", exc_info=True)
        await query.answer("Что-то пошло не так. Повторите попытку позже.", show_alert=True)

# Обработчик неизвестных команд
@router.message()
async def unknown_command(message: Message):
    await System_commands.unknown_command(message)