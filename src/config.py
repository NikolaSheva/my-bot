# config.py
import os
import telebot
from dotenv import load_dotenv
import logging


# ------------------- Logging Configuration -------------------
logger = logging.getLogger(__name__)

# ------------------- Telegram Bot -------------------
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logger.error("Токен не найден в переменных окружения (BOT_TOKEN)")
    raise ValueError("Токен не найден в переменных окружения (BOT_TOKEN)")

CHANNEL_ID = os.getenv("CHANNEL_ID")
if not CHANNEL_ID:
    logger.error("CHANNEL_ID не найден в переменных окружения")
    raise ValueError("CHANNEL_ID не найден в переменных окружения")

ADMIN_ID = os.getenv("ADMIN_ID")
if not ADMIN_ID:
    logger.error("ADMIN_ID не найден в переменных окружения")
    raise ValueError("ADMIN_ID не найден в переменных окружения")
ADMIN_ID = int(ADMIN_ID)

bot = telebot.TeleBot(TOKEN, skip_pending=True)
