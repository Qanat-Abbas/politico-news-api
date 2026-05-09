from fastapi.testclient import TestClient

from app.main import app
from app.scraper import Article


def test_home_page_shows_registration() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "FA23-BAI-056" in response.text
    assert "Politico" in response.text


def test_get_endpoint_returns_required_shape(monkeypatch) -> None:
    class FakeBrowser:
        def first_result_for(self, keyword: str) -> Article:
            return Article(
                url="https://www.politico.com/news/2026/01/01/example-story",
                body=(
                    "Technology companies are changing how people work. "
                    "The article explains why technology investment is accelerating. "
                    "It also describes risks for workers and customers."
                ),
            )

    monkeypatch.setattr("app.main.PoliticoBrowser", FakeBrowser)
    client = TestClient(app)

    response = client.get("/get?keyword=technology")

    assert response.status_code == 200
    assert response.json() == {
        "registration": "FA23-BAI-056",
        "newssource": "Politico",
        "keyword": "technology",
        "url": "https://www.politico.com/news/2026/01/01/example-story",
        "summary": (
            "Technology companies are changing how people work. "
            "The article explains why technology investment is accelerating. "
            "It also describes risks for workers and customers."
        ),
    }


def test_blank_keyword_returns_400() -> None:
    client = TestClient(app)

    response = client.get("/get?keyword=%20")

    assert response.status_code == 400
