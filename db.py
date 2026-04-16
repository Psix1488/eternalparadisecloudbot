# -*- coding: utf-8 -*-
"""
Модуль для работы с базой данных.
Содержит функции для инициализации, сохранения, получения и удаления информации о файлах.
"""
import sqlite3
import logging

logger = logging.getLogger(__name__)
DB_NAME = "files.db"

def init_db():
    """Создаёт таблицу в базе данных, если её ещё нет."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS files (
            key TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            filename TEXT,
            chat_id TEXT,
            message_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована.")

def save_file_info(key, file_id, filename, chat_id, message_id):
    """Сохраняет информацию о файле в базу данных."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO files (key, file_id, filename, chat_id, message_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (key, file_id, filename, chat_id, message_id))
    conn.commit()
    conn.close()
    logger.info(f"Информация о файле '{filename}' сохранена с ключом '{key}'.")

def get_file_info(key):
    """Возвращает информацию о файле по ключу или None, если ключ не найден."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT file_id, filename FROM files WHERE key = ?', (key,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"file_id": row[0], "filename": row[1]}
    return None

def delete_file_info(key):
    """Удаляет информацию о файле из базы данных по ключу."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM files WHERE key = ?', (key,))
    conn.commit()
    conn.close()
    logger.info(f"Информация о ключе '{key}' удалена из базы данных.")