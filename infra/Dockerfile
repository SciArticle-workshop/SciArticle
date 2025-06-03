FROM python:3.12

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN pip install poetry && poetry install --no-root

COPY ./src /app/src

WORKDIR /app/src

CMD ["poetry", "run", "celery", "-A", "celery_app", "worker", "--loglevel=info"]
