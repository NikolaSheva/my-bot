import logging
import datetime
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from config import bot, CHANNEL_ID
from main import parse_lombard_page
from telebot.types import InputMediaPhoto, InputMedia, InlineKeyboardMarkup, InlineKeyboardButton
from pytz import utc
import json
import time
import hashlib

# Настройка логирования
logger = logging.getLogger(__name__)

# Планировщик APScheduler с SQLite
jobstores = {'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')}
scheduler = BackgroundScheduler(jobstores=jobstores, timezone=utc)

# Явно запускаем планировщик и проверяем его состояние
try:
    scheduler.start()
    logger.info("✅ Scheduler started successfully")
    logger.info(f"Scheduler state: {scheduler.state}")
except Exception as e:
    logger.error(f"❌ Failed to start scheduler: {e}")

# ThreadPoolExecutor для неблокирующих задач
executor = ThreadPoolExecutor(max_workers=5)

MAX_RETRIES = 3
DELAY_BETWEEN_LINKS = 1.0

# Хранилище для временных данных пользователей
user_sessions = {}
confirmation_sessions = {}

# --- Валидация ---
def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except (ValueError, TypeError):
        return False

# --- Основная функция отправки в канал ---
def send_link(url, retry=MAX_RETRIES):
    """Отправка ссылки в канал с повторными попытками"""
    logger.info(f"🟡 Начинаем отправку ссылки: {url}")
    
    if CHANNEL_ID is None:
        logger.error(f"❌ {CHANNEL_ID} не задан")
        return

    try:
        text, photos = parse_lombard_page(url)
        logger.info(f"✅ Парсинг успешен, фото: {len(photos)}, текст: {len(text)} символов")
        
        if photos:
            try:
                # Формируем медиагруппу с подписью только к первой фотографии
                media = []
                for i, photo in enumerate(photos):
                    if i == 0:
                        media.append(InputMediaPhoto(media=photo,
                                                     caption=text[:1024] if len(text) > 1024 else text,
                                                     parse_mode="HTML"))
                    else:
                        media.append(InputMediaPhoto(media=photo))
                
                bot.send_media_group(CHANNEL_ID, media)
                logger.info(f"✅ Фото отправлены медиагруппой: {len(photos)} шт. (текст с первой фото)")

            except Exception as media_error:
                logger.error(f"❌ Ошибка отправки медиагруппы: {media_error}")
                # fallback: отправляем фото по одному, первую с текстом
                for i, photo in enumerate(photos):
                    try:
                        if i == 0:
                            bot.send_photo(CHANNEL_ID, photo,
                                           caption=text[:1024] if len(text) > 1024 else text,
                                           parse_mode="HTML")
                        else:
                            bot.send_photo(CHANNEL_ID, photo)
                        logger.info(f"✅ Фото {i+1} отправлено отдельно")
                    except Exception as photo_error:
                        logger.error(f"❌ Ошибка отправки фото {i+1}: {photo_error}")
        else:
            # Если фото нет, просто отправляем текст
            bot.send_message(CHANNEL_ID, text, parse_mode="HTML")
            logger.info("✅ Текст отправлен (фото отсутствуют)")
        
        logger.info(f"✅ Ссылка {url} успешно отправлена в канал")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке {url}: {e}")
        if retry > 0:
            logger.info(f"🔁 Повторная попытка отправки {url} ({retry} попыток осталось)")
            run_time = datetime.datetime.now() + datetime.timedelta(minutes=5)
            scheduler.add_job(
                send_link_async,
                'date',
                run_date=run_time,
                args=[url, retry-1],
                id=f"{url}_retry_{retry}_{datetime.datetime.now().timestamp()}",
                replace_existing=True
            )
def send_link_async(url, retry=MAX_RETRIES):
    """Асинхронная отправка ссылки"""
    logger.info(f"🟡 Запуск асинхронной отправки для: {url}")
    executor.submit(send_link, url, retry)

# --- Функция парсинга и показа результата ---
def parse_and_show_result(url, chat_id, is_preview=False):
    """Парсит ссылку и показывает результат пользователю"""
    try:
        text, photos = parse_lombard_page(url)
        
        # Формируем текст сообщения
        status = "📋 ПРЕВЬЮ ПАРСИНГА" if is_preview else "✅ РЕЗУЛЬТАТ ПАРСИНГА"
        result_text = f"{status}:\n\n{text}"
        
        # Отправляем результат
        if photos:
            try:
                # Отправляем первую фотографию с текстом
                bot.send_photo(chat_id, photos[0], 
                              caption=result_text, 
                              parse_mode="HTML")
                
                # Если есть дополнительные фото, отправляем их отдельно
                if len(photos) > 1:
                    for i, photo in enumerate(photos[1:], 2):
                        bot.send_photo(chat_id, photo)
                        
            except Exception as photo_error:
                logger.error(f"Ошибка отправки фото: {photo_error}")
                bot.send_message(chat_id, result_text, parse_mode="HTML")
        else:
            bot.send_message(chat_id, result_text, parse_mode="HTML")
            
        return True
        
    except Exception as e:
        error_msg = f"❌ Ошибка при парсинге ссылки: {e}"
        bot.send_message(chat_id, error_msg)
        logger.error(f"Ошибка парсинга для {url}: {e}")
        return False

# --- Генерация уникального ID для сессии ---
def generate_session_id(urls):
    """Генерирует уникальный ID для сессии на основе URLs"""
    url_string = ''.join(urls)
    return hashlib.md5(url_string.encode()).hexdigest()[:8]

# --- Клавиатура для подтверждения ---
def get_confirmation_keyboard(session_id):
    """Создает клавиатуру с кнопками подтверждения"""
    keyboard = InlineKeyboardMarkup()
    
    # Кнопка для подтверждения всех ссылок
    keyboard.add(InlineKeyboardButton(
        "✅ Подтвердить отправку всех ссылок", 
        callback_data=f"confirm:{session_id}"
    ))
    
    # Кнопка для отмены
    keyboard.add(InlineKeyboardButton(
        "❌ Отменить отправку", 
        callback_data=f"cancel:{session_id}"
    ))
    
    return keyboard

# --- Планирование ссылок ---
def schedule_links(urls, chat_id, immediate=True):
    """Планирует отправку всех ссылок в канал"""
    try:
        existing_jobs = scheduler.get_jobs()
        total_links = len(urls)
        
        logger.info(f"🟡 Планируем отправку {total_links} ссылок")
        logger.info(f"Текущее количество jobs: {len(existing_jobs)}")
        logger.info(f"Состояние планировщика: {scheduler.state}")
        
        for i, url in enumerate(urls):
            if immediate:
                # Тестовый режим: вызываем сразу
                logger.info(f"⚡ Тестовая отправка сразу для: {url}")
                send_link_async(url)
                continue

            delay_minutes = DELAY_BETWEEN_LINKS * (len(existing_jobs) + i)
            run_time = datetime.datetime.now() + datetime.timedelta(minutes=delay_minutes)
            
            job_id = f"send_{hashlib.md5(url.encode()).hexdigest()[:10]}_{datetime.datetime.now().timestamp()}"
            
            logger.info(f"⏰ Добавляем job {i+1}: {url} на {run_time} (id: {job_id})")
            
            scheduler.add_job(
                send_link_async,
                'date',
                run_date=run_time,
                args=[url],
                id=job_id,
                replace_existing=True
            )
        
        # Проверяем, что jobs действительно добавлены
        current_jobs = scheduler.get_jobs()
        logger.info(f"✅ Jobs после добавления: {len(current_jobs)}")
        
        bot.send_message(
            chat_id,
            f"✅ Все ссылки добавлены в очередь!\n"
            f"Количество ссылок: {total_links}\n"
            f"Первая отправка через: {DELAY_BETWEEN_LINKS:.1f} минут(ы)\n"
            f"Последняя отправка через: {DELAY_BETWEEN_LINKS * total_links:.1f} минут(ы)\n\n"
            f"Статус планировщика: {scheduler.state}"
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка при планировании ссылок: {e}")
        bot.send_message(chat_id, f"❌ Ошибка при планировании: {e}")
def show_next_preview(chat_id):
    """Показывает превью следующей ссылки"""
    if chat_id not in user_sessions:
        return
    
    session = user_sessions[chat_id]
    urls = session['urls']
    current_index = session['current_index']
    
    if current_index >= len(urls):
        # Все ссылки показаны, запрашиваем подтверждение
        show_confirmation(chat_id)
        return
    
    url = urls[current_index]
    
    # Показываем информацию о текущей ссылке
    bot.send_message(
        chat_id, 
        f"🔗 Ссылка {current_index + 1} из {len(urls)}:\n{url}\n\n⏳ Парсим..."
    )
    
    # Парсим и показываем результат
    if parse_and_show_result(url, chat_id, is_preview=True):
        # Увеличиваем индекс и обновляем сессию
        session['current_index'] += 1
        user_sessions[chat_id] = session
        
        # Ждем 1 секунду перед показом следующей ссылки
        time.sleep(1)
        
        # Рекурсивно вызываем следующее превью
        show_next_preview(chat_id)

def show_confirmation(chat_id):
    """Показывает клавиатуру подтверждения после всех превью"""
    if chat_id not in user_sessions:
        return
    
    session = user_sessions[chat_id]
    urls = session['urls']
    
    # Генерируем уникальный ID сессии и сохраняем URLs
    session_id = generate_session_id(urls)
    confirmation_sessions[session_id] = {
        'chat_id': chat_id,
        'urls': urls,
        'timestamp': datetime.datetime.now()
    }
    
    # Очищаем старые сессии (старше 1 часа)
    cleanup_old_sessions()
    
    bot.send_message(
        chat_id,
        f"📊 Парсинг завершен!\n"
        f"Обработано ссылок: {len(urls)}\n\n"
        f"Подтвердите отправку в канал:",
        reply_markup=get_confirmation_keyboard(session_id)
    )

def cleanup_old_sessions():
    """Очищает старые сессии подтверждения"""
    now = datetime.datetime.now()
    keys_to_remove = []
    
    for session_id, session_data in confirmation_sessions.items():
        if (now - session_data['timestamp']).total_seconds() > 3600:  # 1 час
            keys_to_remove.append(session_id)
    
    for key in keys_to_remove:
        del confirmation_sessions[key]

# --- Команда для добавления нескольких ссылок ---
@bot.message_handler(commands=['addlinks'])
def add_links_command(message):
    """Обработчик команды для добавления нескольких ссылок"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "❌ Использование: /addlinks <URL1> <URL2> <URL3> ...")
            return

        # Извлекаем все ссылки из сообщения
        urls = parts[1].strip().split()
        valid_urls = []
        
        # Проверяем каждую ссылку
        for url in urls:
            if is_valid_url(url):
                valid_urls.append(url)
            else:
                bot.reply_to(message, f"❌ Неверный формат URL: {url}")
        
        if not valid_urls:
            bot.reply_to(message, "❌ Не найдено валидных URL")
            return
        
        # Сохраняем ссылки в сессии пользователя
        user_sessions[message.chat.id] = {
            'urls': valid_urls,
            'current_index': 0
        }
        
        # Показываем первую ссылку
        show_next_preview(message.chat.id)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")
        logger.error(f"Ошибка в add_links_command: {e}")

# --- Обработчик callback-кнопок ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Обрабатывает нажатия на inline-кнопки"""
    try:
        if call.data.startswith('confirm:'):
            session_id = call.data.split(':', 1)[1]
            
            if session_id in confirmation_sessions:
                session_data = confirmation_sessions[session_id]
                urls = session_data['urls']
                chat_id = session_data['chat_id']
                
                # Планируем отправку всех ссылок
                schedule_links(urls, chat_id)
                
                bot.edit_message_text(
                    "✅ Отправка подтверждена! Ссылки добавлены в очередь.",
                    chat_id,
                    call.message.message_id
                )
                
                # Удаляем сессии
                if session_id in confirmation_sessions:
                    del confirmation_sessions[session_id]
                if chat_id in user_sessions:
                    del user_sessions[chat_id]
                    
            else:
                bot.answer_callback_query(call.id, "❌ Сессия устарела")
                
        elif call.data.startswith('cancel:'):
            session_id = call.data.split(':', 1)[1]
            
            if session_id in confirmation_sessions:
                session_data = confirmation_sessions[session_id]
                chat_id = session_data['chat_id']
                
                bot.edit_message_text(
                    "❌ Отправка отменена.",
                    chat_id,
                    call.message.message_id
                )
                
                # Удаляем сессии
                if session_id in confirmation_sessions:
                    del confirmation_sessions[session_id]
                if chat_id in user_sessions:
                    del user_sessions[chat_id]
                    
            else:
                bot.answer_callback_query(call.id, "❌ Сессия устарела")
            
    except Exception as e:
        logger.error(f"Ошибка в callback handler: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")

# --- Команда для быстрого просмотра ---
@bot.message_handler(commands=['preview'])
def preview_command(message):
    """Команда только для просмотра без добавления в очередь"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "❌ Использование: /preview <URL>")
            return

        url = parts[1].strip()
        if not is_valid_url(url):
            bot.reply_to(message, f"❌ Неверный формат URL: {url}")
            return

        bot.reply_to(message, "⏳ Парсим ссылку...")
        parse_and_show_result(url, message.chat.id, is_preview=True)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")
        logger.error(f"Ошибка при preview: {e}")

# --- Старая команда для обратной совместимости ---
@bot.message_handler(commands=['addlink'])
def add_link_command(message):
    """Старая команда для добавления одной ссылки"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "❌ Использование: /addlink <URL>")
            return

        url = parts[1].strip()
        if not is_valid_url(url):
            bot.reply_to(message, f"❌ Неверный формат URL: {url}")
            return

        # Используем новую систему с массивом из одного элемента
        user_sessions[message.chat.id] = {
            'urls': [url],
            'current_index': 0
        }
        
        # Показываем превью
        show_next_preview(message.chat.id)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")
        logger.error(f"Ошибка в add_link_command: {e}")

# --- Очистка сессий при перезапуске ---
def cleanup_sessions():
    """Очищает сессии пользователей при запуске"""
    user_sessions.clear()
    confirmation_sessions.clear