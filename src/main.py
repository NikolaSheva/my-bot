import logging
import sys
import time
from typing import Dict
from threading import Thread

from telebot import TeleBot, types
from src.config import settings
from src.parser import LombardParser
from src.session import UserSession
from src.utils import (
    is_valid_lombard_url,
    create_photo_markup,
    send_photos_to_destination,
    # send_to_all_channels,
    # format_send_report,
    create_multi_channel_markup,
    send_preview,
    create_main_menu_markup,
    create_confirmation_markup,
)

# ------------------- Логирование -------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)
logger.info("Бот запускается...")

# ------------------- Telegram Bot -------------------
bot = TeleBot(settings.bot_token)

# Глобальные данные
user_sessions: Dict[int, UserSession] = {}

# ------------------- Вспомогательные функции -------------------

def get_or_create_session(chat_id: int) -> UserSession:
    """Получить или создать сессию пользователя"""
    if chat_id not in user_sessions:
        user_sessions[chat_id] = UserSession(chat_id=chat_id)
    return user_sessions[chat_id]

def safe_delete_message(chat_id: int, message_id: int):
    """Безопасное удаление сообщения"""
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass

def send_temp_message(chat_id: int, text: str, duration: int = 3):
    """Отправить временное сообщение"""
    msg = bot.send_message(chat_id, text)
    time.sleep(duration)
    safe_delete_message(chat_id, msg.message_id)

# ------------------- Обработчики команд -------------------

@bot.message_handler(commands=["start"])
def start(message):
    """Обработчик команды /start"""
    logger.info(f"Команда /start от {message.chat.id}")
    try:
        session = get_or_create_session(message.chat.id)
        session.clear()
        
        welcome_msg = bot.send_message(
            message.chat.id,
            "Welcome to ...!\nF***ing way, it works!\n"
            "Drop me a watch link from lombard-perspectiva.ru\n"
            "e.g. https://lombard-perspectiva.ru/clock/...\n\n"
            "I'll grab the data and set up your post automatically."
        )
        session.message_history.append(welcome_msg.message_id)
        
    except Exception as e:
        logger.error(f"Ошибка в /start: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка. Попробуйте позже.")

@bot.message_handler(commands=["settings", "status"])
def show_settings(message):
    """Показать настройки и статус"""
    try:
        chat_info = bot.get_chat(settings.channel_id)
        session_count = len(user_sessions)
        
        channels_info = "\n".join([f"- {name}" for name, _ in settings.all_channels])
        
        bot.send_message(
            message.chat.id,
            f"Статус бота:\n"
            f"Бот: @{bot.get_me().username}\n"
            f"Основной канал: {chat_info.title}\n"
            f"ID канала: {settings.channel_id}\n"
            f"Username: @{chat_info.username if chat_info.username else 'нет'}\n"
            f"Админ: {settings.admin_id}\n"
            f"Активных сессий: {session_count}\n"
            f"Всего каналов: {len(settings.all_channels)}\n"
            f"Каналы:\n{channels_info}\n"
            f"Макс. фото: {settings.max_photos}\n"
            f"Макс. текст: {settings.max_text_length} символов"
        )
    except Exception as e:
        logger.error(f"Ошибка показа настроек: {e}")
        bot.send_message(message.chat.id, f"Ошибка получения настроек: {e}")

@bot.message_handler(commands=["clear", "cancel"])
def clear_session(message):
    """Очистить текущую сессию"""
    chat_id = message.chat.id
    if chat_id in user_sessions:
        user_sessions[chat_id].clear()
        logger.info(f"Сессия очищена для {chat_id}")
        send_temp_message(chat_id, "Сессия очищена")
    else:
        send_temp_message(chat_id, "Нет активной сессии")

@bot.message_handler(commands=['find_channel'])
def find_channel(message):
    """Найти канал по username"""
    try:
        chat_info = bot.get_chat('perspectivaural')
        
        bot.send_message(
            message.chat.id,
            f"Найден канал!\n"
            f"Название: {chat_info.title}\n"
            f"Числовой ID: {chat_info.id}\n"
            f"Username: @{chat_info.username}\n"
            f"Тип: {chat_info.type}"
        )
        
        bot.send_message(
            message.chat.id,
            f"Вставьте в .env:\nCHANNEL_ID={chat_info.id}"
        )
        
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"Не удалось найти канал 'perspectivaural': {e}\n\n"
            f"Проверьте:\n"
            f"Бот добавлен в канал как администратор\n"
            f"Username канала правильный\n"
            f"Канал публичный"
        )

# ------------------- Обработчики сообщений -------------------

@bot.message_handler(func=lambda m: m.text and m.text.startswith("http"))
def handle_link(message):
    """Обработчик ссылок"""
    chat_id = message.chat.id
    url = message.text.strip()
    
    try:
        if not is_valid_lombard_url(url):
            bot.send_message(chat_id, "Неверная ссылка. Используйте ссылку на часы с lombard-perspectiva.ru")
            return
        
        session = get_or_create_session(chat_id)
        session.clear()
        session.url = url
        
        parsing_msg = bot.send_message(chat_id, "Парсим ссылку...")
        session.message_history.append(parsing_msg.message_id)
        
        parser = LombardParser()
        text, web_photos = parser.parse(url)
        custom_photos = parser.get_custom_photos()
        
        if not session.validate_text_length(text):
            bot.send_message(chat_id, f"Текст слишком длинный. Максимум {settings.max_text_length} символов.")
            return
        
        session.text = text
        session.add_web_photos(web_photos)
        session.add_custom_photos(custom_photos)
        
        safe_delete_message(chat_id, parsing_msg.message_id)
        
        logger.info(f"Спаршено: {len(web_photos)} веб-фото, {len(custom_photos)} кастомных для {chat_id}")
        
        send_preview(bot, session)
        bot.send_message(
            chat_id, 
            f"Готово! Получено {len(session.selected_photos)} фото.\nВыберите действие:", 
            reply_markup=create_main_menu_markup()
        )
        
    except Exception as e:
        logger.error(f"Неожиданная ошибка для {chat_id}: {e}")
        bot.send_message(chat_id, "Произошла непредвиденная ошибка. Попробуйте позже.")

@bot.message_handler(regexp=r'https://lombard-perspectiva\.ru/.*')
def handle_auto_parse(message):
    """Автоматический парсинг ссылок из чата"""
    handle_link(message)

# ------------------- Обработчики callback'ов -------------------

@bot.callback_query_handler(func=lambda call: call.data == "edit_text")
def edit_text_callback(call):
    """Редактирование текста"""
    chat_id = call.message.chat.id
    session = get_or_create_session(chat_id)
    logger.info(f"function cancel_send_callback {session}")

    bot.send_message(chat_id, "Отправьте новый текст для поста:")
    bot.register_next_step_handler(call.message, process_text_edit)
    bot.answer_callback_query(call.id)

def process_text_edit(message):
    """Простая версия - всегда добавляем ссылку"""
    chat_id = message.chat.id
    session = get_or_create_session(chat_id)
    
    if not session.validate_text_length(message.text):
        bot.send_message(chat_id, f"Текст слишком длинный. Максимум {settings.max_text_length} символов.")
        return
    
    # Всегда создаем HTML с ссылкой (БЕЗ дублирования)
    lines = message.text.split('\n')
    first_line = lines[0] if lines else "Часы"
    rest_of_text = '\n'.join(lines[1:]) if len(lines) > 1 else ""
    
    html_text = f'<a href="{session.url}">{first_line}</a>'
    if rest_of_text:
        html_text += f'\n{rest_of_text}'
    
    session.text = html_text
    send_preview(bot, session)
    bot.send_message(
        chat_id, 
        "Текст обновлен. Выберите действие:", 
        reply_markup=create_main_menu_markup()
    )

@bot.callback_query_handler(func=lambda call: call.data == "select_photos")
def select_photos_callback(call):
    """Управление фото"""
    chat_id = call.message.chat.id
    session = get_or_create_session(chat_id)
    
    logger.info(f"Управление фото для {chat_id}: {len(session.selected_photos)} выбрано")
    
    markup = create_photo_markup(session)
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=f"Управление фотографиями (выбрано: {len(session.selected_photos)}):",
        reply_markup=markup,
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith(("move_up_", "move_down_", "remove_")))
def handle_photo_actions(call):
    """Обработка действий с фото"""
    chat_id = call.message.chat.id
    session = get_or_create_session(chat_id)
    
    try:
        cd = call.data
        
        if cd.startswith("remove_"):
            # Запрос подтверждения удаления
            parts = cd.split("_")
            if len(parts) >= 3:
                photo_type = parts[1]
                photo_index = int(parts[2])
                
                if photo_index < len(session.selected_photos):
                    photo_data = session.selected_photos[photo_index]
                    
                    confirm_markup = types.InlineKeyboardMarkup()
                    confirm_markup.add(
                        types.InlineKeyboardButton("Удалить", callback_data=f"confirm_remove_{photo_type}_{photo_index}"),
                        types.InlineKeyboardButton("Оставить", callback_data=f"cancel_remove_{photo_type}_{photo_index}"),
                    )
                    
                    if photo_type == "web" and not photo_data.is_custom:
                        bot.send_photo(
                            chat_id,
                            photo_data.url,
                            caption=f"Удалить фото №{photo_index+1}?",
                            reply_markup=confirm_markup,
                        )
                    else:
                        bot.send_message(
                            chat_id,
                            f"Удалить {photo_data.display_name} фото №{photo_index+1}?",
                            reply_markup=confirm_markup,
                        )
                    
                    bot.answer_callback_query(call.id)
                    return
        
        elif cd.startswith("move_up_"):
            parts = cd.split("_")
            if len(parts) >= 3:
                photo_index = int(parts[2])
                session.move_photo_up(photo_index)
                bot.answer_callback_query(call.id, "Фото перемещено вверх")
                
        elif cd.startswith("move_down_"):
            parts = cd.split("_")
            if len(parts) >= 3:
                photo_index = int(parts[2])
                session.move_photo_down(photo_index)
                bot.answer_callback_query(call.id, "Фото перемещено вниз")
        
        # Обновляем клавиатуру
        new_markup = create_photo_markup(session)
        bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=new_markup,
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки фото для {chat_id}: {e}")
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith(("confirm_remove_", "cancel_remove_")))
def handle_remove_confirmation(call):
    chat_id = call.message.chat.id
    session = get_or_create_session(chat_id)
    
    try:
        parts = call.data.split("_")
        action = "_".join(parts[:2])  # confirm_remove или cancel_remove
        photo_type = parts[2]
        *_, photo_index_str = parts
        photo_index = int(photo_index_str)

        logger.info(f"Callback remove → action={action}, type={photo_type}, index={photo_index}")

        if action == "confirm_remove" and photo_index < len(session.selected_photos):
            removed = session.selected_photos.pop(photo_index)
            logger.info(f"Удалено фото №{photo_index+1}: {removed.url}")
            bot.answer_callback_query(call.id, "Фото удалено")

            new_markup = create_photo_markup(session)
            bot.send_message(
                chat_id,
                f"Обновленный список фото (осталось: {len(session.selected_photos)}):",
                reply_markup=new_markup,
            )
        else:
            bot.answer_callback_query(call.id, "Удаление отменено")

        safe_delete_message(chat_id, call.message.message_id)

    except Exception as e:
        logger.error(f"Ошибка удаления для {chat_id}: {e}")
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "confirm_photos")
def confirm_photos_callback(call):
    """Подтверждение выбора фото"""
    chat_id = call.message.chat.id
    session = get_or_create_session(chat_id)
    
    send_preview(bot, session)
    bot.send_message(
        chat_id, 
        "Выбор фото подтвержден. Выберите действие:", 
        reply_markup=create_main_menu_markup()
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "send_to_channel")
def send_to_channel_callback(call):
    """Начало процесса отправки с выбором опций"""
    chat_id = call.message.chat.id
    session = get_or_create_session(chat_id)
    
    try:
        markup = create_multi_channel_markup()
        
        channels_info = "\n".join([f"- {name}" for name, _ in settings.all_channels])
        
        msg = bot.send_message(
            chat_id,
            f"Куда отправить пост?\n\n"
            f"ОПУБЛИКОВАТЬ ВЕЗДЕ - во все каналы:\n{channels_info}\n"
            f"ТОЛЬКО СЕБЕ - для теста\n"
            f"КОНКРЕТНЫЙ КАНАЛ - выберите ниже",
            reply_markup=markup,
        )
        
        session.choose_send_msg_id = msg.message_id
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Ошибка отправки для {chat_id}: {e}")
        bot.answer_callback_query(call.id, f"Ошибка: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith(("send_everywhere", "send_self_only", "send_to_")))
def choose_send_option_callback(call):
    """Обработка выбора варианта отправки"""
    chat_id = call.message.chat.id
    session = get_or_create_session(chat_id)
    
    try:
        if session.choose_send_msg_id:
            safe_delete_message(chat_id, session.choose_send_msg_id)
        
        if call.data == "send_everywhere":
            session.confirm_data = {"type": "everywhere"}
            preview_msg = bot.send_message(
                chat_id,
                "Отправить пост ВО ВСЕ КАНАЛЫ?\n\n"
                "Это опубликует пост во всех настроенных каналах и отправит вам копию для проверки.",
                reply_markup=create_confirmation_markup(),
            )
            
        elif call.data == "send_self_only":
            session.confirm_data = {"type": "self_only"}
            preview_msg = bot.send_message(
                chat_id,
                "Отправить пост только себе для проверки?",
                reply_markup=create_confirmation_markup(),
            )
            
        else:
            channel_id = call.data.replace("send_to_", "")
            channel_name = "канал"
            
            try:
                chat_info = bot.get_chat(channel_id)
                channel_name = chat_info.title
            except Exception as e:
                logger.warning(f"Не удалось получить информацию по channel_id={channel_id}: {e}")
                # Если не получается, используем дефолтный
                channel_id = str(settings.channel_id)
                chat_info = bot.get_chat(channel_id)
                channel_name = chat_info.title
                
            session.confirm_data = {
                "type": "single_channel", 
                "channel_id": channel_id,
                "channel_name": channel_name
            }
            
            preview_msg = bot.send_message(
                chat_id,
                f"Отправить пост в канал:\n{channel_name}?",
                reply_markup=create_confirmation_markup(),
            )
        
        session.message_history.append(preview_msg.message_id)
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Ошибка выбора отправки для {chat_id}: {e}")
        bot.answer_callback_query(call.id, f"Ошибка: {e}")

@bot.callback_query_handler(func=lambda call: call.data in ("confirm_send", "cancel_send"))
def confirm_send_callback(call):
    """Подтверждение отправки"""
    chat_id = call.message.chat.id
    session = get_or_create_session(chat_id)
    
    if not session.confirm_data:
        bot.answer_callback_query(call.id, "Данные отправки не найдены")
        return
    
    try:
        safe_delete_message(chat_id, call.message.message_id)
        
        if call.data == "cancel_send":
            bot.answer_callback_query(call.id, "Отправка отменена")
            bot.send_message(
                chat_id, 
                "Отправка отменена. Выберите действие:", 
                reply_markup=create_main_menu_markup()
            )
            return
        
        send_type = session.confirm_data.get("type")
        results = []

        if send_type == "everywhere":
            # Отправляем в оба канала
            for name, channel_id in settings.all_channels:
                try:
                    success = send_photos_to_destination(bot, str(channel_id), session)
                    status_msg = "Успешно" if success else "Ошибка"
                    results.append((name, channel_id, success, status_msg))
                except Exception as e:
                    results.append((name, channel_id, False, f"Ошибка: {e}"))

        elif send_type == "self_only":
            success = send_photos_to_destination(bot, str(chat_id), session)
            status_msg = "Успешно" if success else "Ошибка"
            results = [("Личные сообщения", chat_id, success, status_msg)]

        elif send_type == "single_channel":
            channel_id = session.confirm_data["channel_id"]
            channel_name = session.confirm_data["channel_name"]
            try:
                success = send_photos_to_destination(bot, str(channel_id), session)
                status_msg = "Успешно" if success else "Ошибка"
            except Exception as e:
                success = False
                status_msg = f"Ошибка: {e}"
            results = [(channel_name, channel_id, success, status_msg)]

        # Формируем отчет
        report_text = "\n".join([f"{name} ({cid}): {status}" for name, cid, success, status in results])
        confirmation = bot.send_message(chat_id, report_text)

        # Авто-удаление сообщения через 8 секунд
        Thread(target=lambda: (time.sleep(8), safe_delete_message(chat_id, confirmation.message_id)), daemon=True).start()
        
        # Очистка сессии
        session.clear()
        if chat_id in user_sessions:
            del user_sessions[chat_id]
        
        bot.answer_callback_query(call.id, "Готово")
        
    except Exception as e:
        logger.error(f"Ошибка отправки для {chat_id}: {e}")
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "bulk_remove")
def bulk_remove_callback(call):
    chat_id = call.message.chat.id
    session = get_or_create_session(chat_id)

    if not session.selected_photos:
        bot.answer_callback_query(call.id, "Нет фото для удаления")
        return

    markup = types.InlineKeyboardMarkup()
    for i, photo in enumerate(session.selected_photos):
        checked = "✅" if i in session.photos_to_remove else "⬜"
        markup.add(
            types.InlineKeyboardButton(f"{checked} {photo.display_name} {i+1}", callback_data=f"toggle_remove_{i}")
        )
    
    markup.row(
        types.InlineKeyboardButton("Удалить выбранные", callback_data="confirm_bulk_remove"),
        types.InlineKeyboardButton("Отмена", callback_data="cancel_bulk_remove")
    )

    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=f"Выберите фото для удаления (выбрано {len(session.photos_to_remove)}):",
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_remove_"))
def toggle_photo_remove(call):
    chat_id = call.message.chat.id
    session = get_or_create_session(chat_id)
    index = int(call.data.split("_")[2])

    if index in session.photos_to_remove:
        session.photos_to_remove.remove(index)
    else:
        session.photos_to_remove.append(index)

    bulk_remove_callback(call)

@bot.callback_query_handler(func=lambda call: call.data == "confirm_bulk_remove")
def confirm_bulk_remove(call):
    chat_id = call.message.chat.id
    session = get_or_create_session(chat_id)

    for index in sorted(session.photos_to_remove, reverse=True):
        removed = session.selected_photos.pop(index)
        logger.info(f"Массово удалено фото №{index+1}: {removed.url}")

    session.photos_to_remove.clear()

    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=f"Удаление завершено. Осталось {len(session.selected_photos)} фото.",
        reply_markup=create_photo_markup(session)
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_bulk_remove")
def cancel_bulk_remove(call):
    chat_id = call.message.chat.id
    session = get_or_create_session(chat_id)
    session.photos_to_remove.clear()
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text="Массовое удаление отменено.",
        reply_markup=create_photo_markup(session)
    )
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=["where"])
def where_to_send(message):
    """Показать куда будут отправляться посты"""
    try:
        channels_info = []
        for channel_name, channel_id in settings.all_channels:
            try:
                chat_info = bot.get_chat(channel_id)
                channels_info.append(
                    f"Канал: {chat_info.title}\n"
                    f"ID: {chat_info.id}\n"
                    f"Username: @{chat_info.username if chat_info.username else 'нет'}\n"
                    f"Тип: {chat_info.type}\n"
                )
            except Exception as e:
                channels_info.append(f"Канал: {channel_name}\nID: {channel_id}\nОшибка: {e}\n")
        
        bot.send_message(
            message.chat.id,
            "Посты будут отправляться в:\n\n" + "\n".join(channels_info)
        )
        
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"Ошибка проверки каналов: {e}"
        )

@bot.message_handler(commands=["debug_channels"])
def debug_channels(message):
    """Диагностика каналов"""
    try:
        bot.send_message(
            message.chat.id,
            f"Проверка настроек каналов:\n"
            f"CHANNEL_ID: '{settings.channel_id}'\n"
            f"MY_CHANNEL_ID: '{settings.my_channel_id}'\n"
            f"ADMIN_ID: {settings.admin_id}\n"
            f"Все каналы из настроек: {settings.all_channels}"
        )
        
        # Проверяем доступ к каждому каналу
        for channel_name, channel_id in settings.all_channels:
            try:
                chat_info = bot.get_chat(channel_id)
                bot.send_message(
                    message.chat.id,
                    f"{channel_name} ({channel_id}): доступен\n"
                    f"   Название: {chat_info.title}\n"
                    f"   Тип: {chat_info.type}"
                )
            except Exception as e:
                bot.send_message(
                    message.chat.id,
                    f"{channel_name} ({channel_id}): ОШИБКА - {e}"
                )
                
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка диагностики: {e}")

if __name__ == "__main__":
    logger.info("Бот запущен!")
    logger.info(f"Настройки: макс. {settings.max_photos} фото, {settings.max_text_length} символов текста")
    logger.info(f"Доступные каналы: {[name for name, _ in settings.all_channels]}")
    
    bot.polling(skip_pending=True, non_stop=True, timeout=60)
