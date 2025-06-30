FROM python:3.12

RUN pip install poetry

# Установка флага, чтобы poetry не создавал venv
RUN poetry config virtualenvs.create false

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root

COPY ./src /app/src

WORKDIR /app/src

CMD ["poetry", "run", "celery", "-A", "celery_app", "worker", "--loglevel=info"]
