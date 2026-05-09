from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.scraper import PoliticoBrowser
from app.summarizer import summarize

REGISTRATION_NUMBER = "FA23-BAI-056"
ASSIGNED_SOURCE = "Politico"

api = FastAPI(title="Politico API")


@api.get("/")
def home():
    return HTMLResponse(f"<h2>{REGISTRATION_NUMBER} - Politico API Running</h2>")


@api.get("/get")
def get_article_summary(keyword: str = Query(..., min_length=1)):
    keyword = keyword.strip()

    if not keyword:
        raise HTTPException(status_code=400, detail="keyword required")

    article = PoliticoBrowser().first_result_for(keyword)

    summary = summarize(article.body, keyword)

    return {
        "registration": REGISTRATION_NUMBER,
        "newssource": ASSIGNED_SOURCE,
        "keyword": keyword,
        "url": article.url,
        "summary": summary
    }


app = api
