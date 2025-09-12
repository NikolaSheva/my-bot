# test_bot.py
from src.config import bot
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@bot.message_handler(commands=['test'])
def test_command(message):
    logger.info("Тестовая команда получена!")
    bot.reply_to(message, "Тест пройден!")

if __name__ == "__main__":
    logger.info("Тестовый бот запущен")
    bot.polling()