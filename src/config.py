from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List, Tuple


class Settings(BaseSettings):
    # Telegram
    channel_id: str  # Основной канал
    my_channel_id: str  # Личный канал (всегда numeric ID)
    bot_token: str
    admin_id: int
    api_id: int
    api_hash: str
    
    # Бизнес-логика
    max_photos: int = 10
    max_text_length: int = 4000

    # Пустой список: Field(default_factory=list)
    custom_photos: List[str] = Field(default_factory=list) # Добавляем кастомные фото
    custom_videos: List[str] = Field(default_factory=list) # ДОБАВЛЯЕМ ВИДЕО
    
    # С одним/несколькими видео: Field(default_factory=lambda: ["video1.mp4", "video2.mp4"])
    # custom_videos: List[str] = Field(default_factory=lambda: ["src/static/videos/patek_universal.mp4"])
    # find . -name "*.pyc" -delete
    # find . -name "__pycache__" -type d -exec rm -r {} +
   
    

    # Безопасность
    rate_limit_per_minute: int = 10
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra='ignore'
    )
    
    @property
    def all_channels(self) -> List[Tuple[str, str]]:
        """Список всех каналов для отправки"""
        channels = []
        if self.channel_id and self.channel_id.strip():
            channels.append(("Perspectiva", self.channel_id))
        if self.my_channel_id and self.my_channel_id.strip():
            # ИСПОЛЬЗУЕМ ПРЯМО ID, БЕЗ ПРЕОБРАЗОВАНИЯ!
            channels.append(("LuxuryWatches", self.my_channel_id))
        return channels
    
    def validate_channels(self):
        """Проверяем корректность конфигурации"""
        if not self.all_channels:
            raise ValueError("Не настроены каналы для отправки.")
        if not self.bot_token:
            raise ValueError("BOT_TOKEN не настроен.")
        return True

settings = Settings()

try:
    settings.validate_channels()
    print("Настройки каналов загружены успешно")
    print(f"Доступные каналы: {[name for name, _ in settings.all_channels]}")
except ValueError as e:
    print(f"Ошибка в настройках: {e}")

if __name__ == "__main__":
    print("\nДетальная проверка настроек:")
    print(f"Channel ID: '{settings.channel_id}'")
    print(f"My Channel ID: '{settings.my_channel_id}'")
    print(f"Все каналы: {settings.all_channels}")





# from pydantic_settings import BaseSettings, SettingsConfigDict


# class Settings(BaseSettings):
    

#     # Pydantic v2 автоматически ищет переменные окружения в UPPER_CASE
#     channel_id: str
#     bot_token: str
#     admin_id: int
#     api_id: int
#     api_hash: str

#     model_config = SettingsConfigDict(
#         env_file=".env",
#         env_file_encoding="utf-8",
#         extra='ignore'
#     )


# settings = Settings()
