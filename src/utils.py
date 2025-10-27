# src/utils.py
import logging
from urllib.parse import urlparse
from telebot import types
from .session import UserSession
from .config import settings

logger = logging.getLogger(__name__)

# ------------------- Существующие функции -------------------

def is_valid_lombard_url(url: str) -> bool:
    """Проверить валидность URL lombard-perspectiva"""
    try:
        parsed = urlparse(url)
        return (parsed.netloc == 'lombard-perspectiva.ru' 
                and parsed.path.startswith('/clock/'))
    except Exception:
        return False

def create_photo_markup(session: UserSession) -> types.InlineKeyboardMarkup:
    """Создать клавиатуру для управления фото"""
    markup = types.InlineKeyboardMarkup()
    
    for i, photo_data in enumerate(session.selected_photos):
        photo_id = f"{'custom' if photo_data.is_custom else 'web'}_{i}"
        display_text = f"{photo_data.display_name} {i+1}"
        
        row_buttons = []
        if i > 0:
            row_buttons.append(
                types.InlineKeyboardButton("⬆️", callback_data=f"move_up_{photo_id}")
            )
        
        row_buttons.append(
            types.InlineKeyboardButton(display_text, callback_data=f"remove_{photo_id}")
        )
        
        if i < len(session.selected_photos) - 1:
            row_buttons.append(
                types.InlineKeyboardButton("⬇️", callback_data=f"move_down_{photo_id}")
            )
        
        markup.row(*row_buttons)
    
    markup.row(
        types.InlineKeyboardButton("Удалить несколько", callback_data="bulk_remove")
    )
    markup.row(
        types.InlineKeyboardButton("Подтвердить", callback_data="confirm_photos")
    )
    
    return markup

def send_photos_to_destination(bot, destination_id, session):
    """Отправить фото и текст как медиагруппу (если есть несколько фото)"""
    try:
        photos = session.selected_photos
        text = session.text or ""
        
        # Если нет фото — отправляем только текст
        if not photos and text:
            bot.send_message(destination_id, text, parse_mode="HTML", disable_web_page_preview=True)
            return True
        
        # Если одно фото — отправляем с caption
        if len(photos) == 1:
            photo = photos[0]
            if photo.is_custom:
                with open(photo.url, "rb") as img:
                    bot.send_photo(destination_id, img, caption=text, parse_mode="HTML")
            else:
                bot.send_photo(destination_id, photo.url, caption=text, parse_mode="HTML")
            return True
        
        # Несколько фото — создаем медиагруппу
        media_group = []
        for i, photo in enumerate(photos):
            caption = text if i == 0 else None  # текст только на первом фото
            
            if photo.is_custom:
                # Используем InputFile вместо bytes
                input_file = types.InputFile(photo.url)
                media_group.append(
                    types.InputMediaPhoto(input_file, caption=caption, parse_mode="HTML")
                )
            else:
                media_group.append(
                    types.InputMediaPhoto(photo.url, caption=caption, parse_mode="HTML")
                )
        
        bot.send_media_group(destination_id, media_group)
        logger.info(f"Отправлено {len(media_group)} фото как медиагруппа в {destination_id}")
        return True

    except Exception as e:
        logger.error(f"Ошибка отправки в {destination_id}: {e}")
        return False

def send_preview(bot, session: UserSession):
    """Отправить превью пользователю"""
    send_photos_to_destination(bot, session.chat_id, session)

def cleanup_message_history(bot, session: UserSession):
    """Очистить историю сообщений"""
    for msg_id in session.message_history:
        try:
            bot.delete_message(session.chat_id, msg_id)
        except Exception:
            pass
    session.message_history.clear()

def create_main_menu_markup() -> types.InlineKeyboardMarkup:
    """Создать главное меню"""
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Редактировать текст", callback_data="edit_text")
    )
    markup.add(
        types.InlineKeyboardButton("Управление фото", callback_data="select_photos")
    )
    markup.add(
        types.InlineKeyboardButton("Отправить", callback_data="send_to_channel")
    )
    return markup

def create_confirmation_markup() -> types.InlineKeyboardMarkup:
    """Создать клавиатуру подтверждения"""
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Да, отправить", callback_data="confirm_send"),
        types.InlineKeyboardButton("Нет, отменить", callback_data="cancel_send")
    )
    return markup

# ------------------- НОВЫЕ функции для многоканальной отправки -------------------

def send_to_all_channels(bot, session: UserSession):
    """
    Отправить пост во все каналы + админу для проверки
    Возвращает список результатов: [(channel_name, channel_id, success)]
    """
    results = []
    
    # Собираем все места для отправки
    destinations = []
    
    # Добавляем все каналы из настроек
    for channel_name, channel_id in settings.all_channels:
        destinations.append((channel_name, channel_id))
    
    # Добавляем админа для проверки
    destinations.append(("Админ (проверка)", str(settings.admin_id)))
    
    # Отправляем во все места
    for channel_name, channel_id in destinations:
        try:
            success = send_photos_to_destination(bot, channel_id, session)
            results.append((channel_name, channel_id, success))
            
            if success:
                logger.info(f"Успешно отправлено в {channel_name}")
            else:
                logger.warning(f"Не удалось отправить в {channel_name}")
                
        except Exception as e:
            logger.error(f"Ошибка отправки в {channel_name}: {e}")
            results.append((channel_name, channel_id, False))
    
    return results

def create_multi_channel_markup() -> types.InlineKeyboardMarkup:
    """Создать клавиатуру для выбора вариантов отправки"""
    markup = types.InlineKeyboardMarkup()
    
    # Основные опции
    markup.add(
        types.InlineKeyboardButton("Опубликовать ВЕЗДЕ", callback_data="send_everywhere")
    )
    markup.add(
        types.InlineKeyboardButton("Только себе (тест)", callback_data="send_self_only")
    )
    
    # Дополнительные опции для каждого канала
    for channel_name, channel_id in settings.all_channels:
        markup.add(
            types.InlineKeyboardButton(
                f"{channel_name}", 
                callback_data=f"send_to_{channel_id}"
            )
        )
    
    return markup

def format_send_report(results) -> str:
    """Форматирует отчет об отправке"""
    success_count = sum(1 for _, _, success in results if success)
    total_count = len(results)
    
    report_lines = ["Отчет об отправке:"]
    
    for channel_name, _, success in results:
        status = "УСПЕХ" if success else "ОШИБКА"
        report_lines.append(f"{status} - {channel_name}")
    
    report_lines.append(f"Итого: {success_count}/{total_count} успешно")
    
    return "\n".join(report_lines)



# import logging
# from urllib.parse import urlparse
# from telebot import types
# from .session import UserSession
# from src.config import settings

# logger = logging.getLogger(__name__)

# def is_valid_lombard_url(url: str) -> bool:
#     """Проверить валидность URL lombard-perspectiva"""
#     try:
#         parsed = urlparse(url)
#         return (parsed.netloc == 'lombard-perspectiva.ru' 
#                 and parsed.path.startswith('/clock/'))
#     except Exception:
#         return False

# def create_photo_markup(session: UserSession) -> types.InlineKeyboardMarkup:
#     """Создать клавиатуру для управления фото"""
#     markup = types.InlineKeyboardMarkup()
    
#     for i, photo_data in enumerate(session.selected_photos):
#         photo_id = f"{'custom' if photo_data.is_custom else 'web'}_{i}"
#         display_text = f"{photo_data.display_name} {i+1}"
        
#         row_buttons = []
#         if i > 0:
#             row_buttons.append(
#                 types.InlineKeyboardButton("⬆️", callback_data=f"move_up_{photo_id}")
#             )
        
#         row_buttons.append(
#             types.InlineKeyboardButton(display_text, callback_data=f"remove_{photo_id}")
#         )
        
#         if i < len(session.selected_photos) - 1:
#             row_buttons.append(
#                 types.InlineKeyboardButton("⬇️", callback_data=f"move_down_{photo_id}")
#             )
        
#         markup.row(*row_buttons)
    
#     markup.row(
#         types.InlineKeyboardButton("Удалить несколько", callback_data="bulk_remove")
#     )
#     markup.row(
#         types.InlineKeyboardButton("Подтвердить", callback_data="confirm_photos")
#     )
    
#     return markup

# def send_photos_to_destination(bot, destination_ids, session):
#     """Отправить фото и текст как медиагруппу (если есть несколько фото) на несколько каналов"""
#     if not isinstance(destination_ids, list):
#         destination_ids = [destination_ids]
#     success = True
#     for destination_id in destination_ids:
#         try:
#             photos = session.selected_photos
#             text = session.text or ""
            
#             # Если нет фото — отправляем только текст
#             if not photos and text:
#                 bot.send_message(destination_id, text, parse_mode="HTML", disable_web_page_preview=True)
#                 logger.info(f"Отправлено сообщение без фото в {destination_id}")
#                 continue
            
#             # Если одно фото — отправляем с caption
#             if len(photos) == 1:
#                 photo = photos[0]
#                 if photo.is_custom:
#                     with open(photo.url, "rb") as img:
#                         bot.send_photo(destination_id, img, caption=text, parse_mode="HTML")
#                 else:
#                     bot.send_photo(destination_id, photo.url, caption=text, parse_mode="HTML")
#                 logger.info(f"Отправлено 1 фото с текстом в {destination_id}")
#                 continue
            
#             # Несколько фото — создаем медиагруппу
#             media_group = []
#             for i, photo in enumerate(photos):
#                 caption = text if i == 0 else None  # текст только на первом фото
                
#                 if photo.is_custom:
#                     # Используем InputFile вместо bytes
#                     input_file = types.InputFile(photo.url)
#                     media_group.append(
#                         types.InputMediaPhoto(input_file, caption=caption, parse_mode="HTML")
#                     )
#                 else:
#                     media_group.append(
#                         types.InputMediaPhoto(photo.url, caption=caption, parse_mode="HTML")
#                     )
            
#             bot.send_media_group(destination_id, media_group)
#             logger.info(f"Отправлено {len(media_group)} фото как медиагруппа в {destination_id}")

#         except Exception as e:
#             logger.error(f"Ошибка отправки в {destination_id}: {e}")
#             success = False
#     return success

# def send_preview(bot, session: UserSession):
#     """Отправить превью пользователю"""
#     send_photos_to_destination(bot, session.chat_id, session)

# def cleanup_message_history(bot, session: UserSession):
#     """Очистить историю сообщений"""
#     for msg_id in session.message_history:
#         try:
#             bot.delete_message(session.chat_id, msg_id)
#         except Exception:
#             pass
#     session.message_history.clear()

# def create_main_menu_markup() -> types.InlineKeyboardMarkup:
#     """Создать главное меню"""
#     markup = types.InlineKeyboardMarkup()
#     markup.add(
#         types.InlineKeyboardButton("Редактировать текст", callback_data="edit_text")
#     )
#     markup.add(
#         types.InlineKeyboardButton("Управление фото", callback_data="select_photos")
#     )
#     markup.add(
#         types.InlineKeyboardButton("Отправить", callback_data="send_to_channel")
#     )
#     return markup

# def create_confirmation_markup() -> types.InlineKeyboardMarkup:
#     """Создать клавиатуру подтверждения"""
#     markup = types.InlineKeyboardMarkup()
#     markup.add(
#         types.InlineKeyboardButton("Да, отправить", callback_data="confirm_send"),
#         types.InlineKeyboardButton("Нет, отменить", callback_data="cancel_send")
#     )
#     return markup
