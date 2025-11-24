from typing import Text
from sqlalchemy import Column, Integer, String, ForeignKey, ForeignKey, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import create_engine

# Создаем объект базы данных
engine = create_engine('sqlite:///local_database.db', echo=False)

# Создаем декларационную базу данных
Base = declarative_base()

# Объект сессии
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Новая таблица уроков
class Pages(Base):
    __tablename__ = 'pages'
    id = Column(Integer, primary_key=True)
    num_lesson = Column(Integer, nullable=False)
    num_page = Column(Integer, nullable=False)
    num_message = Column(Integer, nullable=False)
    name_page = Column(String)
    
class Sentence(Base):
    __tablename__ = 'sentences'
    id = Column(Integer, primary_key=True)
    text_ru = Column(String, nullable=False)
    translation_en = Column(String, nullable=False)
    num_lesson = Column(Integer)


class Trainer(Base):
    __tablename__ = 'trainers'
    id = Column(Integer, primary_key=True)
    num_lesson = Column(Integer)
    type = Column(Integer)


class Word(Base):
    __tablename__ = 'words'
    id = Column(Integer, primary_key=True)
    english_word = Column(String, nullable=False)
    russian_word = Column(String, nullable=False)
    alter_russian_word = Column(JSON)
    num_lesson = Column(Integer)
    
    
class Relation(Base):
    __tablename__ = 'relations'

    id = Column(Integer, primary_key=True)
    source_word_id = Column(Integer, ForeignKey('words.id'))
    target_word_id = Column(Integer, ForeignKey('words.id'))
    relation_type = Column(String, nullable=False)

class Metric(Base):
    __tablename__ = 'metrics'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    
class MetricWordsValue(Base):
    __tablename__ = 'metric_word_value'
    id = Column(Integer, primary_key=True, index=True)
    word1_id = Column(Integer, ForeignKey('words.id'), nullable=False)
    word2_id = Column(Integer, ForeignKey('words.id'), nullable=False)
    value = Column(Integer, default=0.0)

class MetricSentencesValue(Base):
    __tablename__ = 'metric_sentence_value'
    id = Column(Integer, primary_key=True, index=True)
    sentence1_id = Column(Integer, ForeignKey('sentences.id'), nullable=False)
    sentence2_id = Column(Integer, ForeignKey('sentences.id'), nullable=False)
    value = Column(Integer, default=0.0)
