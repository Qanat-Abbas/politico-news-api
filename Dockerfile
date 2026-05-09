ARG BROWSER_IMAGE_PLATFORM=linux/amd64
FROM --platform=$BROWSER_IMAGE_PLATFORM selenium/standalone-chrome:latest

USER root

WORKDIR /srv/quiz-api

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip python3-venv \
    && python3 -m venv /srv/venv \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /srv/quiz-api/requirements.txt

RUN /srv/venv/bin/pip install --upgrade pip \
    && /srv/venv/bin/pip install --no-cache-dir -r /srv/quiz-api/requirements.txt

COPY app /srv/quiz-api/app

ENV PATH="/srv/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

EXPOSE 7000

USER seluser
ENTRYPOINT []
CMD ["uvicorn", "app.main:app", "--host=0.0.0.0", "--port=7000"]
