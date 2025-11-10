import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin
from typing import List
from .config import settings
import re


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
            safe_reference = reference.replace('.', '.\u200B')

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
                            logger.debug(f"Добавлено фото: {full_url}")

            # Ограничиваем количество фото
            photos = photos[:10]
            # убираем дубликаты без custom_photos
            # photos = list(dict.fromkeys(photos))[:3]

            if price == "По запросу":
                match = re.search(r'(\d[\d\s,.]*\s?\$)', characteristics.get('Состояние', ''))
                price_to_use = match.group(1) if match else price
            else:
                price_to_use = price

            # Формируем список важных характеристик, пропуская пустые и "Нет данных"
            important_chars = [
                ("Материал корпуса", characteristics["Материал корпуса"]),
                ("Водонепроницаемость", characteristics["Водонепроницаемость"]),
                ("Диаметр", characteristics["Диаметр корпуса"]),
                ("Материал ремешка", characteristics["Материал ремешка"]),
            ]

            # Фильтруем только заполненные характеристики
            char_line = [
                f'<b>{key}:</b> {value}'
                for key, value in important_chars
                if value and value.strip() and value != "Нет данных"
            ]

            # Добавляем блок характеристик, если есть данные
            characteristics_block = [*char_line, ""] if char_line else []

            # Формируем HTML
            lines = [
                f'<a href="{url}"><b>{title}</b>  <b>{subtitle.upper()}</b></a>',
                f'<code>{safe_reference}</code>\n',
                f'<b>Состояние:</b> {condition}',
                *characteristics_block,
                f'<b>Цена:</b> <b>{price_to_use}</b>\n',
                '<b>Наши контакты:</b> @Genesislab',
                '<b>Екатеринбург, ул. Маршала Жукова 13</b>',
                'tel:+7(982)663-99-99     |     <a href="https://wa.me/79826639999">WhatsApp</a>\n',
                '<b>Екатеринбург, ул. Сакко и Ванцетти 74</b>',
                'Торговая галерея "LUXURY"',
                'tel:+7(982)699-66-66      |     <a href="https://wa.me/79826996666">WhatsApp</a>',
            ]

            html = "\n".join(lines)

            # Формируем HTML
            # lines = [
            #     f'<a href="{url}"><b>{title}</b>  <b>{subtitle.upper()}</b></a>',
            #     f'<code>{safe_reference}</code>\n',
            #     f'<b>Состояние:</b> {condition}',
            #     f'<b>Материал корпуса:</b> {characteristics["Материал корпуса"]}',
            #     f'<b>Функции:</b> {characteristics["Функции"]}',
            #     f'<b>Материал ремешка:</b> {characteristics["Материал ремешка"]}\n',
            #     f'<b>Цена:</b> <b>{price_to_use}</b>\n',
    
            #     '<b>НАШИ КОНТАКТЫ:</b>',
            #     '@Genesislab\n',
                
            #     '<b>Екатеринбург, ул. Маршала Жукова, 13</b>',
            #     '<a href="+79826639999">+7 (982) 663-99-99</a>',
            #     '<a href="https://wa.me/79826639999">Написать в WhatsApp</a>\n',
                
            #     '<b>Екатеринбург, ул. Сакко и Ванцетти, 74</b>',
            #     'Галерея "LUXURY"',
            #     'tel: +79826996666\n',
            #     '<a href="https://wa.me/79826996666">Написать в WhatsApp</a>',
            # ]
            


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
    
    def get_custom_videos(self) -> List[str]:
        """Получить список кастомных видео"""
        return settings.custom_videos.copy()
