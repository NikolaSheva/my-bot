import os
import requests
from telebot import TeleBot
from telebot.types import InputMediaPhoto,  InputFile
from src.session import UserSession
import logging
from .config import settings

logger = logging.getLogger(__name__)


def is_valid_image_url(url: str) -> bool:
    """
    Checks if the given URL points to a valid image resource (status 200 and content-type includes 'image').
    """
    try:
        resp = requests.head(url, timeout=5, allow_redirects=True)
        if resp.status_code == 200 and 'image' in resp.headers.get('content-type', ''):
            return True
        else:
            logger.warning(f"URL does not point to a valid image: {url} (status: {resp.status_code}, content-type: {resp.headers.get('content-type')})")
            return False
    except Exception as e:
        logger.warning(f"Error checking image URL {url}: {e}")
        return False


def send_photos_to_destination(bot: TeleBot, destination_id: str, session: UserSession) -> bool:
    """Simplified media sending with file/video existence and image URL validation."""
    try:
        photos = session.selected_photos
        videos = session.selected_videos

        logger.info(f"SEND TO {destination_id}: {len(photos)} photo(s), {len(videos)} video(s)")

        # Removed separate text sending to avoid duplication

        # Send videos (if any)
        if videos:
            for video in videos:
                try:
                    if video.is_custom and video.file_path:
                        if not os.path.exists(video.file_path):
                            logger.warning(f"Video file does not exist, skipping: {video.file_path}")
                            continue
                        logger.info(f"Sending video: {video.file_path}")
                        video_input = InputFile(video.file_path)
                        bot.send_video(destination_id, video_input)
                        logger.info(f"Video sent: {video.file_path}")
                except Exception as e:
                    logger.error(f"Error sending video: {e}")

        # Send photos as a group (if any)
        if photos:
            media_group = []
            for i, photo in enumerate(photos):
                try:
                    caption = session.text if i == 0 else None
                    parse_mode = 'HTML' if i == 0 else None
                    if photo.is_custom and photo.file_path:
                        if not os.path.exists(photo.file_path):
                            logger.warning(f"Photo file does not exist, skipping: {photo.file_path}")
                            continue
                        photo_input = InputFile(photo.file_path)
                        media_group.append(InputMediaPhoto(photo_input, caption=caption, parse_mode=parse_mode))
                    else:
                        # Photo by URL, check if it's a valid image URL
                        if not is_valid_image_url(photo.url):
                            logger.warning(f"Skipping invalid image URL: {photo.url}")
                            continue
                        media_group.append(InputMediaPhoto(photo.url, caption=caption, parse_mode=parse_mode))
                except Exception as e:
                    logger.error(f"Error preparing photo: {e}")
                    continue

            if media_group:
                # Split into groups of 10
                for i in range(0, len(media_group), 10):
                    bot.send_media_group(destination_id, media_group[i:i + 10])
                logger.info(f"SENT {len(media_group)} photo(s) to {destination_id}")

        return True

    except Exception as e:
        logger.error(f"General sending error: {e}")
        return False
    

def send_preview(bot: TeleBot, session: UserSession):
    """Enhanced preview with separation of photos and videos, file existence and image URL validation."""
    try:
        chat_id = session.chat_id
        photos = session.selected_photos
        videos = session.selected_videos

        # Send preview text
        preview_text = f"TEXT PREVIEW:\n\n{session.text}\n\n"
        preview_text += f"Media: {len(photos)} photo(s), {len(videos)} video(s)"

        bot.send_message(chat_id, preview_text, parse_mode='HTML')

        # Send videos (if any)
        if videos:
            for i, video in enumerate(videos):
                try:
                    if video.is_custom and video.file_path:
                        if not os.path.exists(video.file_path):
                            logger.warning(f"Video file does not exist for preview, skipping: {video.file_path}")
                            continue
                        # Use InputFile for video
                        video_input = InputFile(video.file_path)
                        caption = f"VIDEO {i+1}/{len(videos)}" if len(videos) > 1 else "VIDEO"
                        msg = bot.send_video(chat_id, video_input, caption=caption)
                        logger.info(f"My {msg}")
                        logger.info(f"Sent video preview for chat {chat_id}")
                    else:
                        logger.warning(f"Video file not found for preview: {getattr(video, 'file_path', 'N/A')}")
                except Exception as e:
                    logger.error(f"Error sending video preview: {e}")
                    bot.send_message(chat_id, f"Error loading video: {e}")

        # Send photos (if any)
        if photos:
            media_group = []
            for i, photo in enumerate(photos):
                try:
                    if photo.is_custom and photo.file_path:
                        if not os.path.exists(photo.file_path):
                            logger.warning(f"Photo file does not exist for preview, skipping: {photo.file_path}")
                            continue
                        # Local files - use InputFile
                        photo_input = InputFile(photo.file_path)
                        caption = f"PHOTO {i+1}/{len(photos)}" if i == 0 and len(photos) > 1 else ""
                        media_group.append(InputMediaPhoto(photo_input, caption=caption))
                    else:
                        # Photo by URL, check if it's a valid image URL
                        if not is_valid_image_url(photo.url):
                            logger.warning(f"Skipping invalid image URL for preview: {photo.url}")
                            continue
                        caption = f"PHOTO {i+1}/{len(photos)}" if i == 0 and len(photos) > 1 else ""
                        media_group.append(InputMediaPhoto(photo.url, caption=caption))
                except Exception as e:
                    logger.error(f"Error preparing photo preview: {e}")
                    continue

            if media_group:
                try:
                    # Split into groups of 10
                    for i in range(0, len(media_group), 10):
                        bot.send_media_group(chat_id, media_group[i:i + 10])
                    logger.info(f"✅ Sent {len(media_group)} photo preview(s) for chat {chat_id}")
                except Exception as e:
                    logger.error(f"Error sending media group preview: {e}")

    except Exception as e:
        logger.error(f"Error sending preview: {e}")
        bot.send_message(chat_id, f"Error creating preview: {e}")

def create_photo_markup(session: UserSession):
    """Обновленная клавиатура для управления медиа"""
    from telebot import types
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # Кнопки для фото
    for i, photo in enumerate(session.selected_photos):
        markup.add(
            types.InlineKeyboardButton(f"Up F{i+1}", callback_data=f"move_up_photo_{i}"),
            types.InlineKeyboardButton(f"Down F{i+1}", callback_data=f"move_down_photo_{i}"),
            types.InlineKeyboardButton(f"Remove F{i+1}", callback_data=f"remove_photo_{i}")
        )
    
    # Кнопки для видео
    for i, video in enumerate(session.selected_videos):
        markup.add(
            types.InlineKeyboardButton(f"Up V{i+1}", callback_data=f"move_up_video_{i}"),
            types.InlineKeyboardButton(f"Down V{i+1}", callback_data=f"move_down_video_{i}"),
            types.InlineKeyboardButton(f"Remove V{i+1}", callback_data=f"remove_video_{i}")
        )
    
    markup.row(
        types.InlineKeyboardButton("Confirm", callback_data="confirm_photos"),
        types.InlineKeyboardButton("Bulk Remove", callback_data="bulk_remove")
    )
    
    return markup

# Дополнительные утилиты
def is_valid_lombard_url(url: str) -> bool:
    """Проверяет, является ли ссылка валидной ссылкой на lombard-perspectiva.ru"""
    return url.startswith('https://lombard-perspectiva.ru/clock/')

def create_main_menu_markup():
    """Создает основное меню действий"""
    from telebot import types
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Edit Text", callback_data="edit_text"),
        types.InlineKeyboardButton("Manage Media", callback_data="select_photos"),
        types.InlineKeyboardButton("Send to Channel", callback_data="send_to_channel")
    )
    return markup

def create_multi_channel_markup():
    """Создает меню выбора каналов для отправки"""
    from telebot import types
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # Кнопка "Опубликовать везде"
    markup.add(types.InlineKeyboardButton("Publish Everywhere", callback_data="send_everywhere"))
    
    # Кнопка "Только себе"
    markup.add(types.InlineKeyboardButton("Only Myself", callback_data="send_self_only"))
    
    # Кнопки для конкретных каналов
    for name, channel_id in settings.all_channels:
        markup.add(types.InlineKeyboardButton(f"{name}", callback_data=f"send_to_{channel_id}"))
    
    return markup

def create_confirmation_markup():
    """Создает меню подтверждения отправки"""
    from telebot import types
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Yes, Send", callback_data="confirm_send"),
        types.InlineKeyboardButton("Cancel", callback_data="cancel_send")
    )
    return markup