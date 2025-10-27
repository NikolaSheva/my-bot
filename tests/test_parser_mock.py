import pytest
from unittest.mock import Mock, patch
from src.parser import LombardParser

# Мок HTML контент
MOCK_HTML = """
<html>
<body>
    <a class="catalog-item--brand-title">Rolex</a>
    <div class="catalog-item--model">Submariner</div>
    <div class="text-gray">REF: 124060</div>
    <p class="item-price--text">350 000 ₽</p>
    <div class="flex-shrink-0">Отличное состояние</div>
    
    <div class="catalog-item--photos__grid">
        <img src="/images/watch1.jpg"/>
        <img src="/images/watch2.jpg"/>
    </div>
    
    <div class="d-block d-sm-flex flex-nowrap justify-space-between align-baseline my-2">
        <div class="option-label">Материал корпуса</div>
        <div class="option-value">Нержавеющая сталь</div>
    </div>
</body>
</html>
"""

@pytest.fixture
def parser():
    return LombardParser()

@pytest.fixture
def mock_requests_get():
    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.text = MOCK_HTML
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        yield mock_get

def test_parse_returns_html_and_photos(parser, mock_requests_get):
    html, photos = parser.parse("https://test.com/watch/1")

    assert isinstance(html, str)
    assert isinstance(photos, list)
    assert len(photos) == 2
    assert photos[0].endswith("watch1.jpg")
    assert photos[1].endswith("watch2.jpg")

def test_html_contains_main_info(parser, mock_requests_get):
    html, _ = parser.parse("https://test.com/watch/1")

    assert "Rolex" in html
    assert "Submariner" in html
    assert "REF: 124060" in html
    assert "350 000" in html
    assert "Отличное состояние" in html

def test_html_contains_characteristics(parser, mock_requests_get):
    html, _ = parser.parse("https://test.com/watch/1")

    assert "Материал корпуса" in html
    assert "Нержавеющая сталь" in html
    assert "Функции" in html  # должно быть "Нет данных" по умолчанию
    assert "Материал ремешка" in html