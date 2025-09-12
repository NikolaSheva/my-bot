# run.py
import logging
from config import bot
import main  # для инициализации # noqa: F401
import scheduler  # для регистрации обработчиков # noqa: F401
from handlers import register_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Запуск бота...")
    register_handlers()
    logger.info("Бот запущен")
    bot.polling(non_stop=True)