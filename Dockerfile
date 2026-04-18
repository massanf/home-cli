FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry --no-cache-dir

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-cache

COPY server/ server/
COPY config/ config/
RUN poetry install --no-cache

COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
