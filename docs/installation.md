## Установка и запуск

### Предварительные требования

- Python 3.12+
- Poetry
- Docker и Docker Compose

### 1. Настройка окружения

1. **Клонируйте репозиторий:**

    ```bash
    git clone git@github.com:SciArticle-workshop/SciArticle.git
    cd sciarticle
    ```

2. **Создайте файл с переменными окружения:**
    Скопируйте `.env.example` (если он есть) или создайте новый файл `.env` в корне проекта и заполните его согласно разделу "Переменные окружения".

3. **Установите зависимости:**

    ```bash
    poetry install
    ```

### 2. Запуск локально (без Docker)

1. **Примените миграции:**

    ```bash
    poetry run python src/manage.py migrate
    ```

2. **Запустите веб-сервер Django:**

    ```bash
    poetry run python src/manage.py runserver
    ```

3. **Запустите Celery worker:**

    ```bash
    poetry run celery -A src.celery_app worker --loglevel=info
    ```

4. **Запустите Celery Beat (планировщик задач):**

    ```bash
    poetry run celery -A src.celery_app beat --loglevel=info
    ```

5. **Запустите бота**

   ```bash
   poetry run python src/bot/bot.py
   ```

### 3. Запуск с помощью Docker

Это предпочтительный способ для развертывания, так как он автоматически поднимает все необходимые сервисы (веб, базу данных, Redis, Celery).

```bash
docker-compose -f infra/docker-compose.yml up --build
```


