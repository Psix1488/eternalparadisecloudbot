# ==================================================
# БОТ-ФАЙЛООБМЕННИК (без веб-сервера)
# Файлы хранятся в Telegram-канале, ссылки ведут на пост
# ==================================================

# ----------------------------------------------
# 1. ИМПОРТЫ (ничего менять не нужно)
# ----------------------------------------------
import os
import uuid
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, CallbackContext
from db import init_db, save_file_meta, get_file_meta, delete_file_meta

# ----------------------------------------------
# 2. ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ (можно заменить на прямые вставки)
# ----------------------------------------------
load_dotenv()

# ⬇⬇⬇ ВСТАВЬТЕ СВОЙ ТОКЕН ОТ BOTFATHER ⬇⬇⬇
BOT_TOKEN = os.getenv("8696097579:AAFd9g6SSRXJHucfq_bqL0cyU4dlirybg_A")  # если используете .env, то укажите там; или замените на "123456:ABC..."
# Например: BOT_TOKEN = "1234567890:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"

# ⬇⬇⬇ ВСТАВЬТЕ ИМЯ ВАШЕГО ПУБЛИЧНОГО КАНАЛА (без @) ⬇⬇⬇
CHANNEL_USERNAME = os.getenv("eternalparadisecloud")  # или напишите прямо: "my_files_channel"
# Например: CHANNEL_USERNAME = "eternal_paradise_files"

# ----------------------------------------------
# 3. НАСТРОЙКА ЛОГИРОВАНИЯ (не трогать)
# ----------------------------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----------------------------------------------
# 4. ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
# ----------------------------------------------
init_db()

# ----------------------------------------------
# 5. ОБРАБОТЧИКИ КОМАНД
# ----------------------------------------------

def start(update: Update, context: CallbackContext):
    # ⬇⬇⬇ ТЕКСТ ПРИВЕТСТВИЯ (можно изменить) ⬇⬇⬇
    update.message.reply_text(
        "📤 *Файлообменник*\n\n"
        "Отправьте мне любой файл, и я сохраню его в канале.\n"
        "Вы получите ссылку вида:\n"
        f"`https://t.me/{CHANNEL_USERNAME}/123`\n"
        "По этой ссылке кто угодно сможет скачать файл.\n\n"
        "Команды:\n"
        "/get `ключ` – получить файл сюда\n"
        "/delete `ключ` – удалить ссылку (файл в канале остаётся)\n"
        "/myfiles – показать ваши файлы (в разработке)",
        parse_mode="Markdown"
    )

def get_file_attributes(message):
    """Извлекает объект файла, имя и mime-тип (не трогать)"""
    if message.document:
        return message.document, message.document.file_name, message.document.mime_type
    elif message.photo:
        return message.photo[-1], f"photo_{message.photo[-1].file_unique_id}.jpg", "image/jpeg"
    elif message.video:
        name = message.video.file_name or f"video_{message.video.file_unique_id}.mp4"
        return message.video, name, message.video.mime_type
    elif message.audio:
        name = message.audio.file_name or f"audio_{message.audio.file_unique_id}.mp3"
        return message.audio, name, message.audio.mime_type
    elif message.voice:
        return message.voice, f"voice_{message.voice.file_unique_id}.ogg", "audio/ogg"
    else:
        return None, None, None

def handle_file(update: Update, context: CallbackContext):
    """Обработка полученного файла (не трогать)"""
    user = update.effective_user
    message = update.effective_message

    file_obj, filename, mime = get_file_attributes(message)
    if not file_obj:
        update.message.reply_text("❌ Неподдерживаемый тип файла.")
        return

    try:
        # Отправляем файл в канал
        sent = context.bot.send_document(
            chat_id=f"@{CHANNEL_USERNAME}",
            document=file_obj.file_id,
            caption=f"📁 {filename}\n👤 Загрузил: {user.first_name} (@{user.username})"
        )
        # Генерируем короткий ключ
        unique_key = str(uuid.uuid4())[:8]
        save_file_meta(unique_key, CHANNEL_USERNAME, sent.message_id, filename)

        post_url = f"https://t.me/{CHANNEL_USERNAME}/{sent.message_id}"
        
        # ⬇⬇⬇ ТЕКСТ ОТВЕТА ПОЛЬЗОВАТЕЛЮ (можно изменить) ⬇⬇⬇
        reply_text = (
            f"✅ Файл *{filename}* сохранён!\n\n"
            f"🔗 *Ссылка:* {post_url}\n\n"
            f"📌 *Ключ:* `{unique_key}`\n"
            f"Используйте `/get {unique_key}` чтобы получить файл сюда."
        )
        update.message.reply_text(reply_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        update.message.reply_text("❌ Не удалось отправить файл в канал. Проверьте права бота и публичность канала.")

def get_file_command(update: Update, context: CallbackContext):
    """Отправляет файл по ключу (не трогать)"""
    args = context.args
    if not args:
        update.message.reply_text("Укажите ключ: `/get ключ`", parse_mode="Markdown")
        return
    key = args[0]
    meta = get_file_meta(key)
    if not meta:
        update.message.reply_text("❌ Файл с таким ключом не найден.")
        return
    try:
        context.bot.forward_message(
            chat_id=update.effective_chat.id,
            from_chat_id=f"@{meta['channel']}",
            message_id=meta['message_id']
        )
    except Exception as e:
        logger.error(f"Ошибка пересылки: {e}")
        update.message.reply_text("Не удалось получить файл из канала.")

def delete_link_command(update: Update, context: CallbackContext):
    """Удаляет запись о файле (не трогать)"""
    args = context.args
    if not args:
        update.message.reply_text("Укажите ключ: `/delete ключ`", parse_mode="Markdown")
        return
    key = args[0]
    meta = get_file_meta(key)
    if not meta:
        update.message.reply_text("❌ Ключ не найден.")
        return
    delete_file_meta(key)
    update.message.reply_text(f"✅ Ссылка для ключа `{key}` удалена. Файл в канале остался.", parse_mode="Markdown")

def myfiles_command(update: Update, context: CallbackContext):
    """Заглушка (можно изменить или дописать)"""
    update.message.reply_text("Функция в разработке. Пока сохраняйте ключи, которые выдаёт бот.")

# ----------------------------------------------
# 6. ЗАПУСК БОТА (ничего менять не нужно)
# ----------------------------------------------
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("get", get_file_command))
    dp.add_handler(CommandHandler("delete", delete_link_command))
    dp.add_handler(CommandHandler("myfiles", myfiles_command))
    dp.add_handler(MessageHandler(
        Filters.document | Filters.photo | Filters.video | Filters.audio | Filters.voice,
        handle_file
    ))

    updater.start_polling()
    logger.info(f"Бот запущен. Канал: @{CHANNEL_USERNAME}")
    updater.idle()

if __name__ == "__main__":
    main()