from aiogram.types import Message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db_layer.models import Pages, SessionLocal
from db_layer.repository import get_pages_by_lesson, get_page_info, get_lessons_from_db
from aiogram.types import CallbackQuery

class CallbackLessons:
    async def select_lesson_pages(callback: CallbackQuery):
        """Обрабатывает выбор урока"""
        lesson_id = int(callback.data.split('_')[1])
        pages = await get_pages_by_lesson(lesson_id)
        page_buttons = []
        for page in pages:
            button_text = f"{page.name_page}"  # Номер страницы находится в классе Page
            callback_data = f"page_{page.id}"
            page_buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=page_buttons)
        await callback.message.edit_text("Выберите страницу урока:", reply_markup=keyboard)

    async def send_page_content(callback: CallbackQuery):
        """Отправка содержимого выбранной страницы"""
        page_id = int(callback.data.split('_')[1])
        
        # Получаем информацию о странице урока
        page_info = await get_page_info(page_id)
        
        if not page_info:
            await callback.message.edit_text("Страница не найдена!")
            return
            
        num_message = page_info.num_message  # Предполагается, что страница хранит номер сообщения
        chat_id = "@SpravEnglish"  # Chat ID канала, откуда берётся сообщение
        
        # Получаем общую информацию о странице
        lesson = await get_page_info(page_id)
        if not lesson:
            await callback.message.edit_text("Ошибка: страница не найдена.")
            return
        
        # Получаем общий список страниц урока
        all_pages = await get_pages_by_lesson(lesson.num_lesson)
        all_lessons = await get_lessons_from_db()
        total_pages = len(all_pages)
        total_lesson = len(all_lessons)
        
        # Формируем клавиатуру с кнопками навигации
        navigation_buttons = []
        
        # Кнопка << Назад
        if lesson.num_page > 0:
            prev_page = all_pages[lesson.num_page - 1]
        else:
            if lesson.num_lesson > 1:
                previous_lesson_pages = await get_pages_by_lesson(lesson.num_lesson - 1)
                if previous_lesson_pages:
                    prev_page = previous_lesson_pages[-1]
                else:
                    prev_page = None
            else:
                prev_page = None
        if prev_page is not None:
            navigation_buttons.append([InlineKeyboardButton(text="<< Предыдущая страница", callback_data=f"page_{prev_page.id}")])
        navigation_buttons.append([InlineKeyboardButton(text="Тренировка лексики", callback_data=f"wl_st_{lesson.num_lesson}")])
        navigation_buttons.append([InlineKeyboardButton(text="Тренировка грамматики", callback_data=f"gl_st_{lesson.num_lesson}")])
        # Кнопка Следующая страница
        if lesson.num_page < total_pages - 1:
            next_page = all_pages[lesson.num_page + 1]
        else:
            if lesson.num_lesson < total_lesson - 1:
                next_lesson_pages = await get_pages_by_lesson(lesson.num_lesson + 1)
                if next_lesson_pages:
                    next_page = next_lesson_pages[0]
                else:
                    next_page = None
            else:
                next_page = None
        if next_page is not None:
            navigation_buttons.append([InlineKeyboardButton(text="Следующая страница >>", callback_data=f"page_{next_page.id}")])
        
        # Создаем клавиатуру с кнопками
        navigation_markup = InlineKeyboardMarkup(inline_keyboard=navigation_buttons)
        
        # Копируем сообщение с нужной клавиатурой
        await callback.bot.copy_message(
            chat_id=callback.message.chat.id,
            from_chat_id=chat_id,
            message_id=num_message,
            reply_markup=navigation_markup
        )





        
class ChooseLessons:
    def __init__(self):
        self.session = SessionLocal()
        self.lessons = []
        self.current_lesson = None
        self.current_page = 1

    def fetch_lessons(self):
        """Загрузка списка уроков из базы данных"""
        self.lessons = (
            self.session.query(Pages.num_lesson.distinct())
            .order_by(Pages.num_lesson)
            .all()
        )
        self.lessons = [item[0] for item in self.lessons]

    def generate_lesson_list(self):
        """Создание разметки клавиш для выбора урока"""
        buttons = [
            [InlineKeyboardButton(text=f"Урок {num_lesson}", callback_data=f"select_lesson_{num_lesson}")]
            for num_lesson in self.lessons
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    def select_lesson(self, lesson_number):
        """Выбор урока и настройка первой страницы"""
        self.current_lesson = lesson_number
        self.current_page = 1
        pages_exist = self.session.query(Pages).filter_by(num_lesson=lesson_number).first()
        if not pages_exist:
            raise ValueError(f"Нет страниц для урока {lesson_number}.")
        last_page_query = (
            self.session.query(Pages.num_page)
            .filter_by(num_lesson=lesson_number)
            .order_by(Pages.num_page.desc()).first()
        )
        if last_page_query is None:
            raise ValueError(f"Ошибка: не найдена последняя страница урока {lesson_number}.")
        last_page = last_page_query.num_page
        next_lesson_available = any(l > lesson_number for l in self.lessons)
        return self.generate_page_buttons(last_page, next_lesson_available)

    def generate_page_buttons(self, last_page, next_lesson_available):
        """Генерация кнопок навигации по страницам урока"""
        buttons = []
        if self.current_page > 1:
            prev_button = InlineKeyboardButton(text="<< Назад", callback_data=f"prev_page_{self.current_lesson}_{self.current_page}")
            buttons.append([prev_button])
        if self.current_page < last_page:
            next_button = InlineKeyboardButton(text="Вперед >>", callback_data=f"next_page_{self.current_lesson}_{self.current_page}")
            buttons.append([next_button])
        elif next_lesson_available:
            next_button = InlineKeyboardButton(text=">> Следующий урок", callback_data=f"next_lesson_{self.current_lesson}")
            buttons.append([next_button])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    def next_page(self):
        """Переход на следующую страницу урока"""
        last_page_query = (
            self.session.query(Pages.num_page)
            .filter_by(num_lesson=self.current_lesson)
            .order_by(Pages.num_page.desc()).first()
        )
        if last_page_query is None:
            raise ValueError(f"Ошибка: не найдена последняя страница урока {self.current_lesson}.")
        last_page = last_page_query.num_page
        if self.current_page < last_page:
            self.current_page += 1

    def prev_page(self):
        """Переход на предыдущую страницу урока"""
        if self.current_page > 1:
            self.current_page -= 1
    async def show_lessons_list(self, message: Message):
        """Показывает список уроков"""
        lessons = await get_lessons_from_db()
        unique_lessons = set(lesson.num_lesson for lesson in lessons)
        
        # Создание кнопок для каждого уникального урока
        lesson_buttons = []
        for num_lesson in sorted(unique_lessons):
            button_text = f"Урок {num_lesson}"
            callback_data = f"lesson_{num_lesson}"
            lesson_buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
        
        # Формирование inline-клавиатуры
        keyboard = InlineKeyboardMarkup(inline_keyboard=lesson_buttons)
        await message.answer("Выберите урок:", reply_markup=keyboard)
        
    def create_navigation_markup(current_page, total_pages, next_lesson_available=False):
        """Генерация клавиатуры навигации"""
        buttons = []
        if current_page > 1:
            prev_button = InlineKeyboardButton(text="<< Назад", callback_data=f"prev_page_{current_page}")
            buttons.append([prev_button])
        if current_page < total_pages:
            next_button = InlineKeyboardButton(text="Вперед >>", callback_data=f"next_page_{current_page}")
            buttons.append([next_button])
        elif next_lesson_available:
            next_button = InlineKeyboardButton(text=">> Следующий урок", callback_data=f"next_lesson_{current_page}")
            buttons.append([next_button])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    async def send_current_page(bot, chat_id, lesson_number, page_number):
        """Отправка текущей страницы урока пользователю"""
        with SessionLocal() as session:
            lesson = session.query(Pages).filter_by(num_lesson=lesson_number, num_page=page_number).first()
            if lesson:
                message_id = lesson.num_message
                original_channel_id = "@SpravEnglish"
                
                # Сначала получаем информацию о сообщении
                channel_message = await bot.get_message(original_channel_id, message_id)
                text = channel_message.text
                entities = channel_message.entities
                
                # Затем создаем новую клавиатуру
                last_page_query = (
                    session.query(Pages.num_page)
                    .filter_by(num_lesson=lesson_number)
                    .order_by(Pages.num_page.desc()).first()
                )
                if last_page_query is None:
                    await bot.send_message(chat_id, "Ошибка: не найдена последняя страница урока.")
                    return
                last_page = last_page_query.num_page
                next_lesson_available = any(l > lesson_number for l in await get_lessons_from_db())
                navigation_markup = ChooseLessons.create_navigation_markup(page_number, last_page, next_lesson_available)
                
                # Далее отправляем сообщение с клавиатурой
                new_message = await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode='HTML',  # Или 'Markdown'
                    entities=entities,
                    reply_markup=navigation_markup
                )
                
                # Дополнительно добавляем forward, если хочешь оставить оригинальный вид сообщения
                await bot.forward_message(
                    chat_id=chat_id,
                    from_chat_id=original_channel_id,
                    message_id=message_id
                )
            else:
                await bot.send_message(chat_id, "Ничего не найдено.")


