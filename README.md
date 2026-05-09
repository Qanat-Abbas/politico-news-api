# DevOps Quiz 3 - Selenium News Summary API

Registration: `FA23-BAI-056`

Assigned source: `Politico`

This project builds a Dockerized FastAPI service that uses Selenium with Chrome/ChromeDriver to search Politico, open the first article result for a keyword, summarize the article locally, and expose the required API on port `7000`.

## API

```http
GET /get?keyword=election
```

Response shape:

```json
{
  "registration": "FA23-BAI-056",
  "newssource": "Politico",
  "keyword": "election",
  "url": "https://www.politico.com/...",
  "summary": "..."
}
```

The root page also shows the registration number:

```http
GET /
```

## Build

```bash
docker build -t devops-quiz-056:fa23-bai-056 .
```

## Run

```bash
docker run --rm -p 7000:7000 devops-quiz-056:fa23-bai-056
```

## Test API

```bash
curl http://localhost:7000/
curl "http://localhost:7000/get?keyword=election"
```

## Docker Hub Tagging

Replace `your-dockerhub-username` with your Docker Hub username:

```bash
docker tag devops-quiz-056:fa23-bai-056 your-dockerhub-username/devops-quiz-056:fa23-bai-056
docker push your-dockerhub-username/devops-quiz-056:fa23-bai-056
```

## Local Tests

```bash
python3 -m pytest
```
