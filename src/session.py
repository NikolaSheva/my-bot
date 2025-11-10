from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from .config import settings
import os
import logging

logger = logging.getLogger(__name__)

@dataclass
class MediaData:
    url: str
    is_custom: bool = False
    file_path: Optional[str] = None
    media_type: str = "photo"  # "photo" или "video"
    
    @property
    def display_name(self) -> str:
        base_name = "Local" if self.is_custom else "WEB"
        return f"{base_name}_{self.media_type.upper()}"
    
    @property
    def is_local_file(self) -> bool:
        return self.is_custom and self.file_path is not None
    
    @property
    def file_extension(self) -> str:
        """Определяем расширение файла"""
        if self.file_path:
            return os.path.splitext(self.file_path)[1].lower()
        return ""

@dataclass
class UserSession:
    chat_id: int
    my_chat_id: Optional[int] = None
    text: str = ""
    url: str = ""
    photos: List[MediaData] = field(default_factory=list)
    videos: List[MediaData] = field(default_factory=list)  # ОТДЕЛЬНЫЙ СПИСОК ДЛЯ ВИДЕО
    selected_photos: List[MediaData] = field(default_factory=list)
    selected_videos: List[MediaData] = field(default_factory=list)  # ОТДЕЛЬНЫЙ СПИСОК ДЛЯ ВИДЕО
    message_history: List[int] = field(default_factory=list)
    confirm_data: Optional[Dict[str, Any]] = None
    choose_send_msg_id: Optional[int] = None
    photos_to_remove: List[int] = field(default_factory=list)
    videos_to_remove: List[int] = field(default_factory=list)
    post_type: str = "photo"

    def __post_init__(self):
        self.selected_photos = self.photos.copy()
        self.selected_videos = self.videos.copy()

    def __repr__(self):
        return f"<UserSession chat_id={self.chat_id}, photos={len(self.selected_photos)}, videos={len(self.selected_videos)}>"

    def add_web_photos(self, urls: List[str]) -> int:
        """Добавить веб-фото"""
        added = 0
        available_slots = settings.max_photos - len(self.selected_photos)
        for url in urls[:available_slots]:
            media = MediaData(url=url, is_custom=False, media_type="photo")
            self.photos.append(media)
            self.selected_photos.append(media)
            added += 1
        return added
    
    def add_custom_photos(self, file_paths: List[str]) -> int:
        """Добавить кастомные фото"""
        added = 0
        available_slots = settings.max_photos - len(self.selected_photos)
        for file_path in file_paths[:available_slots]:
            if not os.path.exists(file_path):
                logging.getLogger("src.session").disabled = True
                # logger.warning(f"Photo file does not exist: {file_path}")
                continue
            media = MediaData(
                url=file_path, 
                is_custom=True, 
                file_path=file_path,
                media_type="photo"
            )
            self.photos.append(media)
            self.selected_photos.append(media)
            added += 1
        return added
    
    def add_custom_videos(self, file_paths: List[str]) -> int:
        """Добавить кастомные видео в ОТДЕЛЬНЫЙ список"""
        added = 0
        for file_path in file_paths:
            # Проверяем существование файла
            if not os.path.exists(file_path):
                logger.warning(f"Видео файл не найден: {file_path}")
                # Пробуем найти файл относительно корня проекта
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                absolute_path = os.path.join(project_root, file_path)
                
                if os.path.exists(absolute_path):
                    file_path = absolute_path
                    logger.info(f"Видео файл найден по абсолютному пути: {file_path}")
                else:
                    logger.error(f"Видео файл не найден ни по одному пути: {file_path}")
                    continue
            
            media = MediaData(
                url=file_path, 
                is_custom=True, 
                file_path=file_path,
                media_type="video"
            )
            self.videos.append(media)
            self.selected_videos.append(media)
            added += 1
            logger.info(f"Видео добавлено: {file_path}")
        
        return added
    
    def validate_text_length(self, text: str) -> bool:
        return len(text) <= settings.max_text_length
    
    def get_web_photos(self) -> List[MediaData]:
        return [p for p in self.selected_photos if not p.is_custom and p.media_type == "photo"]
    
    def get_custom_photos(self) -> List[MediaData]:
        return [p for p in self.selected_photos if p.is_custom and p.media_type == "photo"]
    
    def get_custom_videos(self) -> List[MediaData]:
        """Получить кастомные видео"""
        return self.selected_videos.copy()
    
    def get_all_media(self) -> List[MediaData]:
        """Получить все медиа в правильном порядке для отправки"""
        return self.selected_photos + self.selected_videos
    
    def has_videos(self) -> bool:
        return len(self.selected_videos) > 0
    
    def has_photos(self) -> bool:
        return len(self.selected_photos) > 0
    
    def total_media_count(self) -> int:
        return len(self.selected_photos) + len(self.selected_videos)

    # Методы для управления фото
    def move_photo_up(self, index: int):
        if 0 < index < len(self.selected_photos):
            self.selected_photos[index - 1], self.selected_photos[index] = (
                self.selected_photos[index], self.selected_photos[index - 1]
            )
    
    def move_photo_down(self, index: int):
        if 0 <= index < len(self.selected_photos) - 1:
            self.selected_photos[index], self.selected_photos[index + 1] = (
                self.selected_photos[index + 1], self.selected_photos[index]
            )
    
    def remove_photo(self, index: int) -> Optional[MediaData]:
        if 0 <= index < len(self.selected_photos):
            return self.selected_photos.pop(index)
        return None

    # Методы для управления видео
    def move_video_up(self, index: int):
        if 0 < index < len(self.selected_videos):
            self.selected_videos[index - 1], self.selected_videos[index] = (
                self.selected_videos[index], self.selected_videos[index - 1]
            )
    
    def move_video_down(self, index: int):
        if 0 <= index < len(self.selected_videos) - 1:
            self.selected_videos[index], self.selected_videos[index + 1] = (
                self.selected_videos[index + 1], self.selected_videos[index]
            )
    
    def remove_video(self, index: int) -> Optional[MediaData]:
        if 0 <= index < len(self.selected_videos):
            return self.selected_videos.pop(index)
        return None
    
    def clear(self):
        self.text = ""
        self.url = ""
        self.photos.clear()
        self.videos.clear()
        self.selected_photos.clear()
        self.selected_videos.clear()
        self.message_history.clear()
        self.confirm_data = None
        self.choose_send_msg_id = None
        self.photos_to_remove.clear()
        self.videos_to_remove.clear()
    
    @property
    def has_media(self) -> bool:
        return len(self.selected_photos) > 0 or len(self.selected_videos) > 0
    
    @property
    def photo_count(self) -> int:
        return len(self.selected_photos)
    
    @property
    def video_count(self) -> int:
        return len(self.selected_videos)
    

    