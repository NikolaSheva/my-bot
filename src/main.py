# main.py 
import time
from telebot import types
import requests
from bs4 import BeautifulSoup
from config import bot, CHANNEL_ID
import logging

logger = logging.getLogger(__name__)

# Глобальный словарь для хранения сессий пользователей
user_data = {}
# Глобальный словарь для хранения истории сообщений пользователей
message_history = {}
# VIDEO_PATH = "/app/media/rolex.mp4"


# ------------------- Функции бота -------------------
def parse_lombard_page(url):
    """Find html and photos"""
    html, photos = "", []
    try:
        logger.info(f"Парсинг страницы: {url}")
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        # Основные данные
        title_tag = soup.find("a", class_="catalog-item--brand-title")
        title = title_tag.get_text(strip=True) if title_tag else "Название не найдено"

        subtitle_tag = soup.select_one("div.catalog-item--model")
        subtitle = subtitle_tag.get_text(strip=True) if subtitle_tag else ""

        ref_tag = soup.find("div", class_="text-gray")
        reference = ref_tag.get_text(strip=True) if ref_tag else "Нет данных"

        price_tag = soup.find("p", class_="item-price--text")
        # price = price_tag.get_text(strip=True) if price_tag else "Нет цены"
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            price = price_text if price_text else "По запросу"
        else:
            price = "По запросу"

        condition_tag = soup.find("div", class_="flex-shrink-0")
        condition = (
            condition_tag.get_text(strip=True)
            if condition_tag
            else "Состояние неизвестно"
        )

        # Характеристики
        characteristics = {
            "Тип": "Нет данных",
            "Материал корпуса": "Нет данных",
            "Водонепроницаемость": "Нет данных",
            "Диаметр корпуса": "Нет данных",
            "Цвет циферблата": "Нет данных",
            "Безель": "Нет данных",
            "Механизм": "Нет данных",
            "Функции": "Нет данных",
            "Запас хода": "Нет данных",
            "Калибр": "Нет данных",
            "Материал ремешка": "Нет данных",
            "Комплектация": "Нет данных",
            "Состояние": "Нет данных",
            "Стекло": "Нет данных",
        }

        # Перебираем все строки с характеристиками
        for row in soup.select(
            "div.d-block.d-sm-flex.flex-nowrap.justify-space-between.align-baseline.my-2"
        ):
            label = row.find("div", class_="option-label")
            value = row.find("div", class_="option-value")
            if label and value:
                label_text = label.get_text(strip=True).lower()
                value_text = value.get_text(strip=True)
                for key in characteristics:
                    if key.lower() in label_text:
                        characteristics[key] = value_text

        # Фото, которые хочешь добавить вручную из локальной папки
        # custom_photos = [
        #     "/app/pics/..jpg",
        # ]

        # Добавляем ручные фото (если есть)
        # for path in custom_photos:
        #     if os.path.exists(path):
        #         photos.append(open(path, "rb"))

        # Собираем фото из HTML
        img_tags = soup.select("div.catalog-item--photos__grid img")
        for img in img_tags:
            src_attr = img.get("src")
            if src_attr:
                # Безопасное преобразование в строку
                src_str = str(src_attr).split("?")[0]
                if src_str and src_str.strip() and "noimage" not in src_str.lower():
                    photos.append(src_str)
                    logger.debug(f"📸 Добавлено фото из HTML: {src_str}")
            else:
                logger.debug("ℹ️ У изображения нет src атрибута")

        # ✅ Безопасная обработка
        unique_photos = []
        seen_urls = set()

        for photo in photos:
            if isinstance(photo, str):  # URL
                if photo not in seen_urls:
                    seen_urls.add(photo)
                    unique_photos.append(photo)
            else:  # file-object
                # Файловые объекты всегда считаем уникальными
                unique_photos.append(photo)

        photos = unique_photos[:10]

        # убираем дубликаты без custom_photos
        # photos = list(dict.fromkeys(photos))[:3]

        # Формируем HTML с правильным форматированием
        html = f"""<a href="{url}"><b>{title}</b>  <b>{subtitle}</b></a>
<b>{reference}</b>

✨ <b>Состояние:</b> {condition}
<b>Материал корпуса:</b> {characteristics['Материал корпуса']}
<b>Функции:</b> {characteristics['Функции']}
<b>Материал ремешка:</b> {characteristics['Материал ремешка']}

<b>Цена:</b> {price}
<b>Наши контакты:</b> @Genesislab
Екатеринбург
+7(982)663-99-99
"""
        

    except Exception as e:
        logger.error(f"Ошибка парсинга {url}: {e}")
        raise
    return html.strip(), photos


def create_photo_markup(photos, selected_photos):
    """Создает клавиатуру для управления фото с кнопками перемещения"""
    markup = types.InlineKeyboardMarkup()

    for i, photo_url in enumerate(selected_photos):
        # Находим индекс фото в оригинальном списке
        original_index = photos.index(photo_url)

        row_buttons = []
        if i > 0:
            row_buttons.append(
                types.InlineKeyboardButton(
                    "⬆️", callback_data=f"move_up_{original_index}"
                )
            )

        row_buttons.append(
            types.InlineKeyboardButton(
                f"❌ {i+1}", callback_data=f"remove_{original_index}"
            )
        )

        if i < len(selected_photos) - 1:
            row_buttons.append(
                types.InlineKeyboardButton(
                    "⬇️", callback_data=f"move_down_{original_index}"
                )
            )

        markup.row(*row_buttons)

    # Добавляем кнопку для массового удаления
    markup.row(
        types.InlineKeyboardButton("🗑️ Удалить несколько", callback_data="bulk_remove")
    )
    markup.row(
        types.InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_photos")
    )
    return markup


def send_preview(chat_id):
    """Отправляет превью поста с текущими настройками"""
    data = user_data[chat_id]
    if data["selected_photos"]:
        media = []
        for i, photo in enumerate(data["selected_photos"]):
            if i == 0:
                media.append(
                    types.InputMediaPhoto(
                        photo, caption=data["text"], parse_mode="HTML"
                    )
                )
            else:
                media.append(types.InputMediaPhoto(photo))
        bot.send_media_group(chat_id, media)
    else:
        bot.send_message(chat_id, data["text"], parse_mode="HTML")


# ------------------- Обработчики бота -------------------


@bot.message_handler(commands=["start"])
def start(message):
    logger.info(f"Received message from {message.chat.id}")
    try:

        # Инициализируем историю сообщений для чата
        message_history[message.chat.id] = []

        # Добавляем текущее сообщение в историю
        message_history[message.chat.id].append(message.message_id)

        msg = bot.send_message(
            message.chat.id, "Отправь ссылку на часы с lombard-perspectiva.ru"
        )
        message_history[message.chat.id].append(msg.message_id)
        # код обработки
        logger.debug("Обработка сообщения")
    except Exception as e:
        logger.error(f"Ошибка обработки: {e}")


@bot.message_handler(func=lambda m: m.text.startswith("http"))
def handle_link(message):
    # Добавляем текущее сообщение в историю
    if message.chat.id not in message_history:
        message_history[message.chat.id] = []
    message_history[message.chat.id].append(message.message_id)
    url = message.text.strip()
    try:
        text, photos = parse_lombard_page(url)

        user_data[message.chat.id] = {
            "text": text,
            "photos": photos,
            "url": url,
            "selected_photos": photos.copy(),  # Изначально все фото выбраны
        }

        # Отправляем превью с возможностью редактирования
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "✏️ Редактировать текст", callback_data="edit_text"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "🖼️ Управление фото", callback_data="select_photos"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "📤 Отправить в канал", callback_data="send_to_channel"
            )
        )

        send_preview(message.chat.id)
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")


@bot.callback_query_handler(func=lambda call: call.data == "select_photos")
def select_photos_callback(call):
    try:
        logger.info(f"Callback select_photos от {call.message.chat.id}")
        chat_id = call.message.chat.id
        if chat_id in user_data:
            # Очищаем временные данные о выборе для удаления
            if "photos_to_remove" in user_data[chat_id]:
                del user_data[chat_id]["photos_to_remove"]

            markup = create_photo_markup(
                user_data[chat_id]["photos"], user_data[chat_id]["selected_photos"]
            )
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="Управление фотографиями:",
                reply_markup=markup,
            )
            bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Ошибка в select_photos_callback: {e}")


@bot.callback_query_handler(
    func=lambda call: call.data.startswith(
        ("move_up_", "move_down_", "remove_", "confirm_remove_", "cancel_remove_")
    )
)
def handle_photo_actions(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        bot.answer_callback_query(call.id, "Сессия истекла")
        return

    try:
        data = user_data[chat_id]
        photos = data["photos"]
        selected_photos = data["selected_photos"]

        cd = call.data
        try:
            photo_index = int(cd.split("_")[-1])
        except ValueError:
            bot.answer_callback_query(call.id, "Неверный формат индекса")
            return

        if photo_index < 0 or photo_index >= len(photos):
            bot.answer_callback_query(call.id, "Индекс вне диапазона")
            return

        photo_url = photos[photo_index]

        # Этап 1: запрос подтверждения на удаление
        if cd.startswith("remove_"):
            if photo_url in selected_photos:
                confirm_markup = types.InlineKeyboardMarkup()
                confirm_markup.add(
                    types.InlineKeyboardButton(
                        "✅ Удалить", callback_data=f"confirm_remove_{photo_index}"
                    ),
                    types.InlineKeyboardButton(
                        "↩️ Оставить", callback_data=f"cancel_remove_{photo_index}"
                    ),
                )
                bot.send_photo(
                    chat_id,
                    photo_url,
                    caption=f"🗑️ Фото №{selected_photos.index(photo_url)+1} — удалить?",
                    reply_markup=confirm_markup,
                )
            bot.answer_callback_query(call.id)

        # Этап 2: подтверждение удаления
        elif cd.startswith("confirm_remove_"):
            if photo_url in selected_photos:
                selected_photos.remove(photo_url)
            bot.answer_callback_query(call.id, "Фото удалено")

            # Показываем обновлённый список фото
            new_markup = create_photo_markup(photos, selected_photos)
            bot.send_message(
                chat_id, "📸 Обновленный список фото:", reply_markup=new_markup
            )

        elif cd.startswith("cancel_remove_"):
            bot.answer_callback_query(call.id, "Удаление отменено")

            # Показываем снова список фото
            new_markup = create_photo_markup(photos, selected_photos)
            bot.send_message(
                chat_id, "📸 Обновленный список фото:", reply_markup=new_markup
            )

        # Перемещение вверх
        elif cd.startswith("move_up_"):
            if photo_url in selected_photos:
                pos = selected_photos.index(photo_url)
                if pos > 0:
                    selected_photos[pos - 1], selected_photos[pos] = (
                        selected_photos[pos],
                        selected_photos[pos - 1],
                    )

        # Перемещение вниз
        elif cd.startswith("move_down_"):
            if photo_url in selected_photos:
                pos = selected_photos.index(photo_url)
                if pos < len(selected_photos) - 1:
                    selected_photos[pos + 1], selected_photos[pos] = (
                        selected_photos[pos],
                        selected_photos[pos + 1],
                    )

        # Обновляем клавиатуру основного списка, но только если это не запрос на подтверждение
        if not cd.startswith(("remove_", "cancel_remove_")):
            new_markup = create_photo_markup(photos, selected_photos)
            bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=new_markup,
            )

    except Exception as e:
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}")


@bot.callback_query_handler(func=lambda call: call.data == "confirm_photos")
def confirm_photos_callback(call):
    chat_id = call.message.chat.id
    if chat_id in user_data:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "✏️ Редактировать текст", callback_data="edit_text"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "📤 Отправить в канал", callback_data="send_to_channel"
            )
        )

        send_preview(chat_id)
        bot.send_message(
            chat_id, "Выбор фото подтвержден. Выберите действие:", reply_markup=markup
        )
        bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "edit_text")
def edit_text_callback(call):
    chat_id = call.message.chat.id
    bot.send_message(chat_id, "Отправьте новый текст для поста:")
    bot.register_next_step_handler(call.message, process_text_edit)
    bot.answer_callback_query(call.id)


def process_text_edit(message):
    chat_id = message.chat.id
    if chat_id in user_data:
        user_data[chat_id]["text"] = message.text

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "📤 Отправить в канал", callback_data="send_to_channel"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "🖼️ Управление фото", callback_data="select_photos"
            )
        )

        send_preview(chat_id)
        bot.send_message(
            chat_id, "Текст обновлен. Выберите действие:", reply_markup=markup
        )


@bot.callback_query_handler(func=lambda call: call.data == "send_to_channel")
def send_to_channel_callback(call):
    chat_id = call.message.chat.id
    if chat_id in user_data:
        data = user_data[chat_id]
        try:
            # Проверяем, что CHANNEL_ID не None и безопасно приводим к строке
            if CHANNEL_ID is None:
                raise ValueError("CHANNEL_ID is None. Проверьте переменные окружения.")
            channel_id: str = str(CHANNEL_ID)

            logger.info(f"📤 Отправка поста в канал {channel_id}")
            logger.info(f"📊 Количество фото: {len(data['selected_photos'])}")
            logger.info(
                f"📝 Тип данных фото: {type(data['selected_photos'][0]) if data['selected_photos'] else 'нет фото'}"
            )

            # Проверяем доступ к каналу
            try:
                chat_info = bot.get_chat(channel_id)
                logger.info(f"✅ Канал доступен: {chat_info.title}")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка доступа к каналу: {e}")

            # ОТПРАВЛЯЕМ ФОТО ГРУППОЙ (если есть)
            if data["selected_photos"]:
                media = []
                logger.info(
                    f"🖼️ Формирование медиагруппы из {len(data['selected_photos'])} фото"
                )

                for i, photo in enumerate(data["selected_photos"]):
                    logger.info(
                        f"📸 Фото {i+1}: тип = {type(photo)}, значение = {str(photo)[:100]}..."
                    )

                    if isinstance(photo, str):  # URL
                        if i == 0:
                            media.append(
                                types.InputMediaPhoto(
                                    photo, caption=data["text"], parse_mode="HTML"
                                )
                            )
                            logger.info(f"✅ Добавлено фото {i+1} как URL с описанием")
                        else:
                            media.append(types.InputMediaPhoto(photo))
                            logger.info(f"✅ Добавлено фото {i+1} как URL")
                    else:  # file-object или другой тип
                        logger.error(f"❌ Неподдерживаемый тип фото: {type(photo)}")
                        # Преобразуем в нужный формат или пропускаем

                try:
                    logger.info("🔄 Попытка отправки медиагруппы...")
                    sent_messages = bot.send_media_group(channel_id, media)
                    logger.info(
                        f"✅ Медиагруппа отправлена успешно! {len(sent_messages)} сообщений"
                    )

                except Exception as e:
                    logger.error(f"❌ Ошибка отправки медиагруппы: {e}")
                    logger.exception("Полная трассировка ошибки:")

                    # Если не получилось группой, пробуем отправить по одному
                    try:
                        logger.info("🔄 Попытка отправить фото по одному...")
                        for i, photo in enumerate(data["selected_photos"]):
                            if isinstance(photo, str):  # URL
                                if i == 0:
                                    bot.send_photo(
                                        channel_id,
                                        photo,
                                        caption=data["text"],
                                        parse_mode="HTML",
                                    )
                                    logger.info(f"✅ Фото {i+1} отправлено с описанием")
                                else:
                                    bot.send_photo(channel_id, photo)
                                    logger.info(f"✅ Фото {i+1} отправлено")
                            else:
                                logger.error(
                                    f"❌ Не удалось отправить фото {i+1}: неподдерживаемый тип"
                                )

                        logger.info("✅ Все фото отправлены по одному")
                    except Exception as e2:
                        logger.error(f"❌ Ошибка отправки фото по одному: {e2}")
                        # Если фото не отправились, отправляем хотя бы текст
                        bot.send_message(channel_id, data["text"], parse_mode="HTML")
                        logger.info("✅ Текст отправлен")

            else:
                # Если нет фото - отправляем просто текст
                logger.info("📝 Отправка текстового сообщения")
                bot.send_message(channel_id, data["text"], parse_mode="HTML")
                logger.info("✅ Текст отправлен")

            # Подтверждение пользователю
            confirmation_text = "✅ Пост успешно отправлен!"
            confirmation = bot.send_message(chat_id, confirmation_text)
            message_history[chat_id] = [confirmation.message_id]

            # Очистка данных
            if chat_id in user_data:
                del user_data[chat_id]

            bot.answer_callback_query(call.id)

            # Удаляем подтверждение через 3 секунды
            time.sleep(3)
            bot.delete_message(chat_id, confirmation.message_id)
            if chat_id in message_history:
                message_history[chat_id] = []

        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
            logger.exception("Полная трассировка:")
            bot.answer_callback_query(call.id, f"❌ Ошибка: {str(e)}")


@bot.callback_query_handler(func=lambda call: call.data == "bulk_remove")
def bulk_remove_callback(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        bot.answer_callback_query(call.id, "Сессия истекла")
        return

    data = user_data[chat_id]
    markup = types.InlineKeyboardMarkup()

    # Создаем кнопки для каждой фотографии с чекбоксами
    for i, photo_url in enumerate(data["photos"]):
        is_selected = photo_url in data.get("photos_to_remove", [])
        emoji = "✅" if is_selected else "⬜"
        markup.add(
            types.InlineKeyboardButton(
                f"{emoji} Фото {i+1}", callback_data=f"toggle_remove_{i}"
            )
        )

    markup.row(
        types.InlineKeyboardButton(
            "🗑️ Удалить выбранные", callback_data="confirm_bulk_remove"
        ),
        types.InlineKeyboardButton("↩️ Назад", callback_data="select_photos"),
    )

    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text="Выберите фотографии для удаления:",
        reply_markup=markup,
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_remove_"))
def toggle_remove_callback(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        bot.answer_callback_query(call.id, "Сессия истекла")
        return

    try:
        photo_index = int(call.data.split("_")[-1])
        data = user_data[chat_id]

        if "photos_to_remove" not in data:
            data["photos_to_remove"] = []

        photo_url = data["photos"][photo_index]

        if photo_url in data["photos_to_remove"]:
            data["photos_to_remove"].remove(photo_url)
        else:
            data["photos_to_remove"].append(photo_url)

        # Обновляем сообщение с новым состоянием
        markup = types.InlineKeyboardMarkup()
        for i, photo_url in enumerate(data["photos"]):
            is_selected = photo_url in data["photos_to_remove"]
            emoji = "✅" if is_selected else "⬜"
            markup.add(
                types.InlineKeyboardButton(
                    f"{emoji} Фото {i+1}", callback_data=f"toggle_remove_{i}"
                )
            )

        markup.row(
            types.InlineKeyboardButton(
                "🗑️ Удалить выбранные", callback_data="confirm_bulk_remove"
            ),
            types.InlineKeyboardButton("↩️ Назад", callback_data="select_photos"),
        )

        bot.edit_message_reply_markup(
            chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup
        )
        bot.answer_callback_query(call.id)

    except Exception as e:
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}")


@bot.callback_query_handler(func=lambda call: call.data == "confirm_bulk_remove")
def confirm_bulk_remove_callback(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        bot.answer_callback_query(call.id, "Сессия истекла")
        return

    data = user_data[chat_id]

    if "photos_to_remove" in data and data["photos_to_remove"]:
        # Удаляем выбранные фото из selected_photos
        data["selected_photos"] = [
            p for p in data["selected_photos"] if p not in data["photos_to_remove"]
        ]
        del data["photos_to_remove"]

        # Возвращаемся к обычному виду
        markup = create_photo_markup(data["photos"], data["selected_photos"])
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="Фотографии удалены. Управление фотографиями:",
            reply_markup=markup,
        )
    else:
        bot.answer_callback_query(call.id, "Не выбрано ни одной фотографии")


if __name__ == "__main__":
    logger.info("Бот запущен...")
    bot.polling(non_stop=True)
