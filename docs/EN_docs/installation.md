## Installation and Setup

### Prerequisites

- Python 3.12+
- Poetry
- Docker and Docker Compose

### 1. Environment Setup

1.  **Clone the repository:**

    ```bash
    git clone git@github.com:SciArticle-workshop/SciArticle.git
    cd sciarticle
    ```

2.  **Create the environment variables file:**
    Copy `.env.example` (if it exists) or create a new `.env` file in the project root and fill it out according to the "Environment Variables" section.

3.  **Install dependencies:**

    ```bash
    poetry install
    ```

### 2. Running Locally (without Docker)

1.  **Apply migrations:**

    ```bash
    poetry run python src/manage.py migrate
    ```

2.  **Start the Django web server:**

    ```bash
    poetry run python src/manage.py runserver
    ```

3.  **Start the Celery worker:**

    ```bash
    poetry run celery -A src.celery_app worker --loglevel=info
    ```

4.  **Start Celery Beat (the task scheduler):**

    ```bash
    poetry run celery -A src.celery_app beat --loglevel=info
    ```

5.  **Start the bot:**

    ```bash
    poetry run python src/bot/bot.py
    ```

### 3. Running with Docker

This is the preferred method for deployment, as it automatically brings up all the necessary services (web, database, Redis, Celery).

```bash
docker-compose -f infra/docker-compose.yml up --build
```