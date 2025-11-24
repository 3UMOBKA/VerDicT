from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
class System_commands:
    async def menu(message: Message):
        await message.answer("""
Привет! 👋 Я — TestProgBot, помогу вам изучать английский язык весело и продуктивно.

📚 Меню бота:
- /start — начнем наше путешествие.
- /menu — вывод списка команд.
- /play_synonyms — соревнование на поиск синонимов и антонимов.
- /learn_words — изучение новых слов.
- /grammar_game — игра на проверку грамматики и перевода предложений.
- /lessons — список всех уроков.
- /view_buttons — показ кнопок навигации.
- /hide_buttons — скрытие кнопок навигации.

Погрузимся в мир английского языка прямо сейчас!
""")
    async def unknown_command(message: Message):
        await message.reply("Не понял вашу команду. Используйте доступные команды.")
    
    async def view_button(message: Message):
        """
        Показывает кнопки команд.
        """
        # Создаем клавиатуру с командами
        commands_menu = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="/menu"), KeyboardButton(text="/play_synonyms")],
                [KeyboardButton(text="/learn_words"), KeyboardButton(text="/grammar_game")],
                [KeyboardButton(text="/lessons")], [KeyboardButton(text="/hide_buttons")]
            ],
            resize_keyboard=True,
            one_time_keyboard=False
        )

        # Ответ с клавиатурой
        await message.answer("Кнопки успешно добавлены.", reply_markup=commands_menu)
