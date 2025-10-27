import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin
from typing import List
from .config import settings


logger = logging.getLogger(__name__)

class LombardParser:
    def parse(self, url: str):
        """Парсинг страницы, возврат (html, photos)"""
        html, photos = "", []
        try:
            logger.info(f"Парсинг страницы: {url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            # Основные данные
            title_tag = soup.find("a", class_="catalog-item--brand-title")
            title = title_tag.get_text(strip=True) if title_tag else "Название не найдено"

            subtitle_tag = soup.select_one("div.catalog-item--model")
            subtitle = subtitle_tag.get_text(strip=True) if subtitle_tag else ""

            ref_tag = soup.find("div", class_="text-gray")
            reference = ref_tag.get_text(strip=True) if ref_tag else "Нет данных"

            price_tag = soup.find("p", class_="item-price--text")
            price = "По запросу"
            if price_tag:
                price_text = price_tag.get_text(strip=True)
                if price_text and price_text.strip():
                    price = price_text

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

            # Парсим характеристики
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

            # Собираем фото
            img_tags = soup.select("div.catalog-item--photos__grid img")
            seen_urls = set()
            
            for img in img_tags:
                src_attr = img.get("src")
                if src_attr:
                    src_str = str(src_attr).split("?")[0].strip()
                    if (src_str and 
                        "noimage" not in src_str.lower() and 
                        not src_str.startswith("data:image")):
                        
                        # Преобразуем относительный URL в абсолютный
                        full_url = urljoin(url, src_str)
                        
                        if full_url not in seen_urls:
                            seen_urls.add(full_url)
                            photos.append(full_url)
                            logger.debug(f"📸 Добавлено фото: {full_url}")

            # Ограничиваем количество фото
            photos = photos[:10]
            # убираем дубликаты без custom_photos
            # photos = list(dict.fromkeys(photos))[:3]

            # Формируем HTML
            html = f"""<a href="{url}"><b>{title}</b>  <b>{subtitle}</b></a>
<b>{reference}</b>

<b>Состояние:</b> {condition}
<b>Материал корпуса:</b> {characteristics['Материал корпуса']}
<b>Функции:</b> {characteristics['Функции']}
<b>Материал ремешка:</b> {characteristics['Материал ремешка']}

<b>Цена:</b> {price}
<b>Наши контакты:</b> @Genesislab
Екатеринбург
+7(982)663-99-99"""

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка сети при парсинге {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка при парсинге {url}: {e}")
            raise

        return html.strip(), photos
    

    def get_custom_photos(self) -> List[str]:
        """Получить список кастомных фото"""
        return settings.custom_photos.copy()
    