from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.scraper import Article, PoliticoBrowser
from app.summarizer import summarize

REGISTRATION_NUMBER = "FA23-BAI-056"
ASSIGNED_SOURCE = "Politico"

api = FastAPI(
    title="Politico Selenium Summary API",
    description="Quiz 3 REST API for searching Politico with Selenium and Chrome.",
    version="1.0.0",
)


@api.get("/")
def index() -> HTMLResponse:
    return HTMLResponse(f"<h1>{REGISTRATION_NUMBER} - Politico API Running</h1>")


@api.get("/get")
def get_article_summary(keyword: str = Query(..., min_length=1)) -> dict:
    requested = keyword.strip()

    if not requested:
        raise HTTPException(status_code=400, detail="keyword required")

    article = PoliticoBrowser().first_result_for(requested)
    summary = summarize(article.body, requested)

    return {
        "registration": REGISTRATION_NUMBER,
        "newssource": ASSIGNED_SOURCE,
        "keyword": requested,
        "url": article.url,
        "summary": summary,
    }


app = api
