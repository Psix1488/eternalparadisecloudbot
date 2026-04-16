# -*- coding: utf-8 -*-
"""
Бот-файлообменник для Telegram.
Сохраняет файлы в указанном канале и выдаёт на них ссылки.
"""
import os
import logging
import sqlite3
from uuid import uuid4

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# --- НАСТРОЙКИ (измените их на свои!) ---
BOT_TOKEN = "8696097579:AAFd9g6SSRXJHucfq_bqL0cyU4dlirybg_A"  # Токен бота от @BotFather
CHANNEL_ID = "eternalparadisecloudbot"     # ID канала для хранения файлов (с @)
DB_NAME = "files.db"                  # Имя файла базы данных
# ----------------------------------------

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Функции для работы с базой данных ---
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

# --- Команды бота ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    await update.message.reply_text(
        "👋 Привет! Я бот для обмена файлами.\n\n"
        "Просто отправь мне любой файл (фото, видео, документ), "
        "и я дам на него постоянную ссылку, которой ты сможешь поделиться с кем угодно.\n\n"
        "Команды:\n"
        "/start — показать это сообщение\n"
        "/get <ключ> — получить файл по ключу\n"
        "/delete <ключ> — удалить файл по ключу"
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик входящих файлов."""
    user = update.effective_user
    message = update.effective_message

    # Определяем тип файла и получаем его ID
    if message.document:
        file_id = message.document.file_id
        filename = message.document.file_name
    elif message.photo:
        # Берём самое большое фото
        file_id = message.photo[-1].file_id
        filename = f"photo_{file_id[:10]}.jpg"
    elif message.video:
        file_id = message.video.file_id
        filename = message.video.file_name or f"video_{file_id[:10]}.mp4"
    elif message.audio:
        file_id = message.audio.file_id
        filename = message.audio.file_name or f"audio_{file_id[:10]}.mp3"
    elif message.voice:
        file_id = message.voice.file_id
        filename = f"voice_{file_id[:10]}.ogg"
    else:
        await update.message.reply_text("❌ Неподдерживаемый тип файла.")
        return

    # Пересылаем файл в канал для хранения
    try:
        sent_message = await context.bot.send_document(
            chat_id=CHANNEL_ID,
            document=file_id,
            caption=f"📁 Файл от {user.first_name} (@{user.username})"
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке файла в канал: {e}")
        await update.message.reply_text(
            "❌ Не удалось сохранить файл. Проверьте, что бот является администратором канала и у него есть права на отправку сообщений."
        )
        return

    # Генерируем уникальный ключ для файла
    unique_key = str(uuid4())[:8]

    # Сохраняем информацию о файле в базу данных
    save_file_info(unique_key, file_id, filename, CHANNEL_ID, sent_message.message_id)

    # Формируем ссылку на сообщение в канале
    file_link = f"https://t.me/{CHANNEL_ID.lstrip('@')}/{sent_message.message_id}"

    await update.message.reply_text(
        f"✅ Файл *{filename}* успешно сохранён!\n\n"
        f"🔗 *Ссылка для скачивания:*\n{file_link}\n\n"
        f"📌 *Ключ:* `{unique_key}`\n"
        f"Используйте `/get {unique_key}` чтобы получить файл сюда, или `/delete {unique_key}` чтобы удалить ссылку.",
        parse_mode="Markdown"
    )

async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /get <ключ>."""
    if not context.args:
        await update.message.reply_text(
            "ℹ️ Укажите ключ файла. Пример: `/get abc123`",
            parse_mode="Markdown"
        )
        return

    key = context.args[0]
    file_info = get_file_info(key)

    if not file_info:
        await update.message.reply_text("❌ Файл с таким ключом не найден.")
        return

    try:
        # Отправляем файл пользователю, используя сохранённый file_id
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=file_info["file_id"],
            filename=file_info["filename"],
            caption=f"📎 Вот ваш файл по ключу `{key}`.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке файла по ключу {key}: {e}")
        await update.message.reply_text("❌ Не удалось отправить файл. Возможно, файл был удалён.")

async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /delete <ключ>."""
    if not context.args:
        await update.message.reply_text(
            "ℹ️ Укажите ключ файла. Пример: `/delete abc123`",
            parse_mode="Markdown"
        )
        return

    key = context.args[0]
    file_info = get_file_info(key)

    if not file_info:
        await update.message.reply_text("❌ Файл с таким ключом не найден.")
        return

    # Удаляем запись из базы данных
    delete_file_info(key)

    # Опционально: можно также удалить сообщение с файлом из канала,
    # но для этого нужно сохранять message_id и chat_id канала.
    # Для простоты оставим только удаление из базы данных.
    await update.message.reply_text(
        f"✅ Ссылка для ключа `{key}` удалена. Файл больше недоступен по этой ссылке.",
        parse_mode="Markdown"
    )

# --- Запуск бота ---
def main():
    """Точка входа для запуска бота."""
    # Инициализируем базу данных
    init_db()

    # Создаём приложение
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("get", get_file))
    application.add_handler(CommandHandler("delete", delete_file))

    # Регистрируем обработчик для всех типов файлов
    application.add_handler(MessageHandler(
        filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE,
        handle_file
    ))

    # Запускаем бота
    logger.info("Бот запущен и ожидает сообщения...")
    application.run_polling()

if __name__ == "__main__":
    main()