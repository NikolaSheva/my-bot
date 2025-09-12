# handlers.py
from config import bot  # noqa: F401
from scheduler import add_links_command  # noqa: F401

# Регистрируем обработчики
def register_handlers():
    # Явно импортируем модули с обработчиками
    import main  # для handlers из main.py # noqa: F401
    import scheduler  # для handlers из scheduler.py # noqa: F401
    # Можно добавить дополнительную регистрацию
# Функция add_link_command уже зарегистрирована через декоратор в scheduler.py