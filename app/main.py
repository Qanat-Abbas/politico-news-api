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


def _landing_page() -> str:
    return f"""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>{REGISTRATION_NUMBER} Politico API</title>
        <style>
          :root {{
            color-scheme: light;
            font-family: Inter, Arial, sans-serif;
          }}
          body {{
            margin: 0;
            background: #f4f4f1;
            color: #151515;
          }}
          main {{
            min-height: 100vh;
            display: grid;
            place-items: center;
            padding: 32px 18px;
          }}
          .panel {{
            width: min(760px, 100%);
            border: 1px solid #cfcfc8;
            border-radius: 6px;
            background: #ffffff;
            padding: 30px;
          }}
          h1 {{
            margin: 0 0 10px;
            font-size: clamp(28px, 5vw, 44px);
          }}
          p {{
            margin: 10px 0;
            line-height: 1.5;
          }}
          code {{
            display: block;
            margin-top: 18px;
            padding: 14px;
            border-left: 4px solid #c91818;
            background: #f7f7f4;
            overflow-wrap: anywhere;
          }}
        </style>
      </head>
      <body>
        <main>
          <section class="panel">
            <h1>{REGISTRATION_NUMBER}</h1>
            <p><strong>News Source:</strong> {ASSIGNED_SOURCE}</p>
            <p>Selenium, Chrome, and FastAPI are running in this container.</p>
            <code>GET /get?keyword=election</code>
          </section>
        </main>
      </body>
    </html>
    """


@api.get("/", response_class=HTMLResponse)
def index() -> str:
    return _landing_page()


@api.get("/get")
def get_article_summary(keyword: str = Query(..., min_length=1)) -> dict[str, str]:
    requested = keyword.strip()
    if not requested:
        raise HTTPException(status_code=400, detail="keyword query parameter is required")

    article = PoliticoBrowser().first_result_for(requested)
    summary = _summary_for(article, requested)

    return {
        "registration": REGISTRATION_NUMBER,
        "newssource": ASSIGNED_SOURCE,
        "keyword": requested,
        "url": article.url,
        "summary": summary,
    }


def _summary_for(article: Article, keyword: str) -> str:
    if article.url:
        return summarize(article.body, keyword)

    return f"No Politico article result was found for keyword '{keyword}'."


app = api
