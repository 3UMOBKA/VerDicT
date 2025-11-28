from asyncio.log import logger
import logging
from db_layer.models import MetricWordsValue, Pages, Sentence, SessionLocal, Word, Relation
from sqlalchemy import select, func, update
from typing import List, Optional

def get_single_random_word_from_lesson(lesson_num: int) -> Optional[Word]:
    """
    Возвращает случайное слово из конкретного урока.
    
    Параметры:
    ----------
    lesson_num : int
        Номер урока, из которого нужно извлечь слово.

    Возвращаемое значение:
    ---------------------
    Optional[Word]: Случайное слово из указанного урока или None, если слов нет.
    """
    with SessionLocal() as session:
        # Формулируем запрос: выбираем случайное слово из указанного урока
        query = (
            select(Word)
            .where(Word.num_lesson == lesson_num)
            .order_by(func.random())  # Случайная сортировка
            .limit(1)                 # Берём первое слово
        )
        result = session.execute(query).scalars().first()
        return result


def get_random_words_by_lesson(exclude_word_ids: list[int], lesson_num: int, count: int = 3) -> List[Word]:
    """
    Возвращает список случайных слов из конкретного урока,
    исключая указанные слова.
    """
    with SessionLocal() as session:
        query = (
            select(Word)
            .where(Word.num_lesson == lesson_num, ~Word.id.in_(tuple(exclude_word_ids)))
            .order_by(func.random())
        )
        result = session.execute(query.limit(count)).scalars().all()
        return result




async def get_lessons_from_db():
    """Возвращает список всех уроков."""
    with SessionLocal() as session:
        lessons = session.query(Pages.num_lesson).distinct().group_by(Pages.num_lesson).all()
        return lessons
    

    
async def get_pages_by_lesson(lesson_num):
    """Возвращает страницы конкретного урока по номеру урока, отсортированные по порядку."""
    with SessionLocal() as session:
        pages = session.query(Pages).filter_by(num_lesson=lesson_num).order_by(Pages.num_page.asc()).all()
        return pages
    

async def get_page_info(page_id):
    """Возвращает информацию о странице по её идентификатору."""
    with SessionLocal() as session:
        page = session.query(Pages).filter_by(id=page_id).first() 
        return page




def get_all_words():
    """Возвращает список всех слов из базы данных."""
    with SessionLocal() as session:
        words = session.query(Word).all()
        return words

def get_single_random_word() -> Optional[Word]:
    """Выбирает случайное слово из базы данных."""
    with SessionLocal() as session:
        result = session.execute(select(Word).order_by(func.random()).limit(1)).scalars().first()
        return result

def get_random_words(exclude_word_id: int, count: int = 3) -> List[Word]:
    """Возвращает список случайных слов, исключая указанное слово."""
    with SessionLocal() as session:
        query = select(Word).where(~Word.id.in_((exclude_word_id,))).order_by(func.random())
        result = session.execute(query.limit(count)).scalars().all()
        return result

def get_random_relation_pair():
    """Возвращает случайную пару слов с отношением между ними."""
    with SessionLocal() as session:
        # Сначала получаем случайное отношение
        random_relation = session.query(Relation).order_by(func.random()).first()
        
        if random_relation is None:
            return None
            
        # Получаем исходное и целевое слова
        source_word = session.query(Word).get(random_relation.source_word_id)
        target_word = session.query(Word).get(random_relation.target_word_id)
        
        if source_word is None or target_word is None:
            return None
            
        # Возвращаем объекты слов и тип связи
        return (source_word, random_relation.relation_type, target_word)

def get_random_word_with_relations(source_word_id: int, relation_type: str) -> Optional[Relation]:
    """
    Получает случайное слово, связанное с источником заданным типом связи.
    """
    with SessionLocal() as session:
        rel = session.execute(
            select(Relation).where(Relation.source_word_id == source_word_id, Relation.relation_type == relation_type)
        ).scalars().first()
        return rel

def get_random_sentence() -> Optional[Sentence]:
    """Возвращает случайное предложение из базы данных."""
    with SessionLocal() as session:
        result = session.execute(select(Sentence).order_by(func.random())).scalars().first()
        return result
    

def get_random_words_for_options(exclude_sentence_id: int, num_options: int = 3) -> List[str]:
    """
    Возвращает список случайных слов для формирования вариантов ответов.
    Исключает слова из указанного предложения.
    """
    with SessionLocal() as session:
        excluded_words_query = select(Sentence.text_ru, Sentence.translation_en).where(Sentence.id == exclude_sentence_id)
        excluded_words = set(session.execute(excluded_words_query).scalarmany())
        all_words_query = select(Word.russian_word).where(~Word.russian_word.in_(excluded_words))
        random_words = session.execute(all_words_query.order_by(func.random()).limit(num_options)).scalars().all()
        return random_words

def search_records_by_word(word_id: int) -> List[MetricWordsValue]:
    """
    Функция ищет все записи в таблице MetricValue, где заданное слово встречается
    либо в поле word1_id, либо в поле word2_id.

    Параметры:
    ----------
    word_id : int
        Идентификатор искомого слова.
        
    Возвращаемые значения:
    ----------------------
    List[MetricValue]: Список объектов MetricValue, соответствующих запросу.
    """
    with SessionLocal() as session:
        query = (
            select(MetricWordsValue)
            .where((MetricWordsValue.word1_id == word_id) | (MetricWordsValue.word2_id == word_id))
        )
        results = session.execute(query).scalars().all()
        return results


def add_or_update_metric_value(word1_id: int, word2_id: int, increment_value: float = 0.05):
    """
    Добавляет новую запись в таблицу MetricWordsValue или обновляет существующую.
    
    Параметры:
    ----------
    word1_id : int
        Идентификатор первого слова.
        
    word2_id : int
        Идентификатор второго слова.
        
    increment_value : float, optional
        Значение увеличения веса, по умолчанию 0.05.
    """
    with SessionLocal() as session:
        record = session.query(MetricWordsValue).filter_by(word1_id=word1_id, word2_id=word2_id).first()
        if record:
            # Запись уже существует, обновляем её
            record.value += increment_value
        else:
            # Нет записи, создаём новую
            new_record = MetricWordsValue(
                word1_id=word1_id,
                word2_id=word2_id,
                value=increment_value
            )
            session.add(new_record)
        session.commit()


def remove_zero_values():
    """
    Удаляет все записи из MetricValue, где значение равно 0.0.
    """
    with SessionLocal() as session:
        session.query(MetricWordsValue).filter_by(value=0.0).delete()
        session.commit()


def update_metric_value(record_id: int, delta: float):
    """
    Обновляет значение метрики в таблице MetricWordsValue, сохраняя диапазон значений от 0.01 до 0.99.
    """
    with SessionLocal() as session:
        record = session.query(MetricWordsValue).filter_by(id=record_id).first()
        if record:
            new_value = max(min(record.value + delta, 0.99), 0.01)  # Ограничиваем значение диапазоном 0.01-0.99
            record.value = new_value
            session.commit()

        
def find_word_by_text(text: str) -> Optional['Word']:
    """
    Поиск слова по английскому или русскому варианту.
    """
    from db_layer.models import Word
    with SessionLocal() as session:
        word = session.query(Word).filter(
            (Word.english_word == text) | (Word.russian_word == text)
        ).first()
        return word

def search_records_by_word_pair(correct_word_id: int, incorrect_word_id: int) -> list:
    """Ищет существующие записи с заданной парой слов."""
    with SessionLocal() as session:
        records = (
            session.query(MetricWordsValue)
            .filter((MetricWordsValue.correct_word_id == correct_word_id) & (MetricWordsValue.incorrect_word_id == incorrect_word_id))
            .all()
        )
        return records
def next_sentence(self) -> Optional[Sentence]:
    """
    Получение следующего предложения из базы данных.
    """
    if self.mode.startswith("lesson"):
        _, lesson_number = self.mode.split("_")  # Разделяем строку и получаем номер урока
        return get_random_sentence_by_lesson(int(lesson_number))
    else:
        return get_random_sentence()
    
    
    

def get_random_sentence_by_lesson(lesson_id: int) -> Optional[Sentence]:
    """
    Получение случайного предложения из указанного урока.
    """
    logger.info(f"Попытка извлечения предложения из урока {lesson_id}")
    with SessionLocal() as session:
        # Запрашиваем предложение с указанным номером урока
        sentences_query = session.query(Sentence).filter(Sentence.num_lesson == lesson_id)
        
        # Выбираем одно случайное предложение из результата запроса
        random_sentence = sentences_query.order_by(func.random()).limit(1).first()
            
        return random_sentence

        
def get_sentences_by_lesson(lesson_id: int) -> List[Sentence]:
    """
    Получение всех предложений из указанного урока.
    """
    with SessionLocal() as session:
        results = session.query(Sentence).filter(Sentence.num_lesson == lesson_id).all()
        return results

def get_all_sentences(self) -> List[Sentence]:
    """
    Получение всех предложений из базы данных.
    """
    with SessionLocal() as session:
        results = session.query(Sentence).all()
        return results