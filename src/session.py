from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from .config import settings

@dataclass
class PhotoData:
    url: str
    is_custom: bool = False
    file_path: Optional[str] = None
    
    @property
    def display_name(self) -> str:
        return "Local" if self.is_custom else "WEB"
    
    @property
    def is_local_file(self) -> bool:
        """Проверяет, является ли фото локальным файлом"""
        return self.is_custom and self.file_path is not None

@dataclass
class UserSession:
    chat_id: int
    my_chat_id: Optional[int] = None
    text: str = ""
    url: str = ""
    photos: List[PhotoData] = field(default_factory=list)
    selected_photos: List[PhotoData] = field(default_factory=list)
    message_history: List[int] = field(default_factory=list)
    confirm_data: Optional[Dict[str, Any]] = None
    choose_send_msg_id: Optional[int] = None
    photos_to_remove: List[int] = field(default_factory=list)

    def __post_init__(self):
        """Инициализация после создания dataclass"""
        self.selected_photos = self.photos.copy()

    def __repr__(self):
        return f"<UserSession chat_id={self.chat_id}, photos={len(self.selected_photos)}>"

    def add_web_photos(self, urls: List[str]) -> int:
        """Добавить веб-фото с проверкой лимита"""
        added = 0
        available_slots = settings.max_photos - len(self.selected_photos)
        for url in urls[:available_slots]:
            photo = PhotoData(url=url, is_custom=False)
            self.photos.append(photo)
            self.selected_photos.append(photo)
            added += 1
        return added
    
    def add_custom_photos(self, file_paths: List[str]) -> int:
        """Добавить кастомные фото с проверкой лимита"""
        added = 0
        available_slots = settings.max_photos - len(self.selected_photos)
        for file_path in file_paths[:available_slots]:
            photo = PhotoData(url=file_path, is_custom=True, file_path=file_path)
            self.photos.append(photo)
            self.selected_photos.append(photo)
            added += 1
        return added
    
    def validate_text_length(self, text: str) -> bool:
        return len(text) <= settings.max_text_length
    
    def get_web_photos(self) -> List[PhotoData]:
        return [p for p in self.selected_photos if not p.is_custom]
    
    def get_custom_photos(self) -> List[PhotoData]:
        return [p for p in self.selected_photos if p.is_custom]
    
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
    
    def remove_photo(self, index: int) -> Optional[PhotoData]:
        if 0 <= index < len(self.selected_photos):
            return self.selected_photos.pop(index)
        return None
    
    def clear(self):
        self.text = ""
        self.url = ""
        self.photos.clear()
        self.selected_photos.clear()
        self.message_history.clear()
        self.confirm_data = None
        self.choose_send_msg_id = None
        self.photos_to_remove.clear()
    
    @property
    def has_photos(self) -> bool:
        return len(self.selected_photos) > 0
    
    @property
    def photo_count(self) -> int:
        return len(self.selected_photos)
