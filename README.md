# SciArticle

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-4.2+-blue.svg)](https://www.djangoproject.com/)

[RU](#ru-section) - [EN](#en-section)

<a id="ru-section"></a>
## RU
---

# SciArticle

SciArticle — это серверное приложение и Telegram-бот, предназначенные для организации краудсорсинга и валидации научных статей в PDF-формате. Сервис работает как вспомогательный бэкенд для основного бота **`@SciSourceBot`**, предоставляя ему функциональность для взаимодействия с сообществом.

Основная задача проекта — создать управляемое сообществом пространство, где пользователи могут выполнять запросы на статьи, загружать недостающие PDF-файлы и коллективно проверять их подлинность, получая за это вознаграждение в виде подписки в основном сервисе.

## Ключевые возможности

- **Обработка запросов по DOI**: Принимает API-запросы от основного бота и публикует их в специальном чате.
- **Краудсорсинг PDF**: Участники сообщества могут загружать PDF-файлы в ответ на опубликованные запросы.
- **Коллективная валидация**: Система голосования (`✅ Всё верно` / `❌ PDF неверный`) позволяет сообществу проверять соответствие загруженного PDF запрошенной статье.
- **Система вознаграждений**: Автоматически отслеживает вклад пользователей (загрузки и валидации) и запрашивает выдачу подписки через API основного бота при достижении пороговых значений.
- **Автоматическая очистка чата**: Управляет жизненным циклом сообщений в чате, удаляя устаревшие запросы, проверенные PDF и временные уведомления.
- **Внутренний API**: Предоставляет эндпоинты для взаимодействия с основным ботом `SciSourceBot`.

## [Архитектура и принцип работы](docs/architecture.md)

## Стек технологий

- **Бэкенд**: Django, Django REST Framework
- **База данных**: PostgreSQL
- **Очередь задач**: Celery
- **Брокер сообщений**: Redis
- **Telegram-бот**: `python-telegram-bot`
- **Веб-сервер (в Docker)**: WSGI + WhiteNoise
- **Контейнеризация**: Docker

## Структура проекта

```
.
├── data/                    # Данные (например, БД), монтируемые в Docker
├── docs/                    # Документация
├── infra/                   # Конфигурация инфраструктуры
│   ├── docker-compose.yml   # Оркестрация контейнеров
│   ├── Dockerfile           # Сборка образа приложения
│   └── initdb/              # SQL-скрипты для инициализации БД
├── src/                     # Исходный код приложения
│   ├── api/                 # Django-приложение для REST API
│   ├── bot/                 # Django-приложение для логики бота
│   │   ├── handlers/        # Обработчики сообщений и колбэков
│   │   ├── migrations/
│   │   ├── tasks.py         # Асинхронные задачи Celery
│   │   └── services.py      # Бизнес-логика бота
│   ├── sciarticle/          # Основные настройки Django проекта
│   ├── celery_app.py        # Конфигурация Celery
│   └── manage.py            # Утилита управления Django
├── poetry.lock              # Зафиксированные версии зависимостей
├── pyproject.toml           # Определение проекта и его зависимостей
└── README.md
```

## [Установка и запуск](docs/installation.md)

### Предварительные требования

- Python 3.12+
- Poetry
- Docker и Docker Compose
## Переменные окружения

Создайте файл `.env` в директории infra и определите в нем переменные из `env.example`.

```python
TELEGRAM_BOT_TOKEN=your_bot_token_here # Бот @SciArticleBot

SOURCE_SERVER_URL=http://your-api # URL сервиса, который принимает POST-запросы

SEARCH_CHAT_ID=id_sciarticle_search_chat  # Общий чат всех пользователей

API_SECRET_TOKEN=your_secret_token  # Для защиты HTTP-запросов между сервисами без участия пользователей

DEFAULT_UPLOAD_FOR_SUBSCRIPTION=default_number # Число загрузок для подписки дефолтное

DEFAULT_VALIDATION_FOR_SUBSCRIPTION=default_number # Число голосований для подписки дефолтное
```
## API Endpoints

Сервис предоставляет REST API для взаимодействия с основным ботом `@SciSourceBot`. Все эндпоинты требуют заголовок `X-API-Token` для авторизации.

| Метод  | Путь                                    | Описание                                                               |
| :----- | :-------------------------------------- | :--------------------------------------------------------------------- |
| `POST` | `/api/request-pdf/`                     | Создает новый запрос на поиск статьи по DOI.                           |
| `PUT`  | `/api/request-pdf/<int:pk>/`            | Обновляет существующий запрос (например, `message_search_id`).         |
| `POST` | `/api/validate_broken-pdf/`             | Принимает "сломанный" PDF от основного бота и инициирует его валидацию.|

## Фоновые задачи (Celery Beat)

Планировщик запускает периодические задачи для поддержания системы в актуальном состоянии:

| Задача                                     | Расписание         | Описание                                                                                                   |
| ------------------------------------------ | ------------------ | ---------------------------------------------------------------------------------------------------------- |
| `bot.tasks.run_check`                      | Каждый час        | Находит истекшие запросы (старше 47 часов), меняет их статус на `expired` и уведомляет основной сервис.       |
| `bot.tasks.run_check_and_delete_pdf`       | Каждый час        | Удаляет сообщения с PDF-файлами, которые были загружены или провалидированы более 47 часов назад.          |
| `bot.tasks.run_check_and_delete_thank_message` | Каждые 20 минут    | Удаляет временные благодарственные сообщения, отправленные пользователям в чат (срок жизни - 1 час).       |

## Тестирование

Для запуска тестов используйте `pytest`:

```bash
poetry run pytest
```

## Лицензия

Этот проект лицензирован в соответствии с условиями, указанными в файле `LICENSE`.

## Участники проекта (Contributors)


<table>
  <tr>
        <td align="center">
      <a href="https://github.com/TatyanaYus">
        <img src="https://github.com/TatyanaYus.png?size=100" width="100px;" alt="TatyanaYus"/>
        <br />
        <sub><b>TatyanaYus</b></sub>
      </a>
    </td>
        <td align="center">
      <a href="https://github.com/aeee78">
        <img src="https://github.com/aeee78.png?size=100" width="100px;" alt="aeee78"/>
        <br />
        <sub><b>aeee78</b></sub>
      </a>
    </td>
        <td align="center">
      <a href="https://github.com/AndreyZimin99">
        <img src="https://github.com/AndreyZimin99.png?size=100" width="100px;" alt="AndreyZimin99"/>
        <br />
        <sub><b>AndreyZimin99</b></sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/FrostWillmott">
        <img src="https://github.com/FrostWillmott.png?size=100" width="100px;" alt="FrostWillmott"/>
        <br />
        <sub><b>FrostWillmott</b></sub>
      </a>
    </td>

  </tr>
</table>


<br>
<br>

<a id="en-section"></a>
## EN
---

# SciArticle

SciArticle is a server application and Telegram bot designed for crowdsourcing and validating scientific articles in PDF format. The service acts as a supporting backend for the main bot, **`@SciSourceBot`**, providing it with functionality to interact with the community.

The main goal of the project is to create a community-driven space where users can request articles, upload missing PDF files, and collectively verify their authenticity, receiving rewards in the form of a subscription to the main service for their contributions.

## Key Features

- **DOI Request Processing**: Accepts API requests from the main bot and publishes them in a dedicated chat.
- **PDF Crowdsourcing**: Community members can upload PDF files in response to published requests.
- **Collective Validation**: A voting system (`✅ Correct` / `❌ Incorrect PDF`) allows the community to verify that the uploaded PDF matches the requested article.
- **Reward System**: Automatically tracks user contributions (uploads and validations) and requests the issuance of a subscription via the main bot's API when thresholds are met.
- **Automatic Chat Cleanup**: Manages the lifecycle of messages in the chat, deleting outdated requests, verified PDFs, and temporary notifications.
- **Internal API**: Provides endpoints for interaction with the main bot `SciSourceBot`.

## [Architecture and How It Works](docs/architecture.md)

## Tech Stack

- **Backend**: Django, Django REST Framework
- **Database**: PostgreSQL
- **Task Queue**: Celery
- **Message Broker**: Redis
- **Telegram Bot**: `python-telegram-bot`
- **Web Server (in Docker)**: WSGI + WhiteNoise
- **Containerization**: Docker

## Project Structure

```
.
├── data/                    # Data (e.g., DB), mounted in Docker
├── docs/                    # Documentation
├── infra/                   # Infrastructure configuration
│   ├── docker-compose.yml   # Container orchestration
│   ├── Dockerfile           # Application image build
│   └── initdb/              # SQL scripts for DB initialization
├── src/                     # Application source code
│   ├── api/                 # Django app for the REST API
│   ├── bot/                 # Django app for the bot's logic
│   │   ├── handlers/        # Message and callback handlers
│   │   ├── migrations/
│   │   ├── tasks.py         # Asynchronous Celery tasks
│   │   └── services.py      # Bot's business logic
│   ├── sciarticle/          # Main Django project settings
│   ├── celery_app.py        # Celery configuration
│   └── manage.py            # Django management utility
├── poetry.lock              # Pinned dependency versions
├── pyproject.toml           # Project definition and its dependencies
└── README.md
```

## [Installation and Launch](docs/installation.md)

### Prerequisites

- Python 3.12+
- Poetry
- Docker and Docker Compose

## Environment Variables

Create a `.env` file in the `infra` directory and define the variables from `env.example` in it.

```python
TELEGRAM_BOT_TOKEN=your_bot_token_here # The @SciArticleBot bot

SOURCE_SERVER_URL=http://your-api   # URL of the service that accepts POST requests

SEARCH_CHAT_ID=id_sciarticle_search_chat   # The main chat for all users

API_SECRET_TOKEN=your_secret_token   # For securing HTTP requests between services without user involvement

DEFAULT_UPLOAD_FOR_SUBSCRIPTION=default_number # Default number of uploads required for a subscription

DEFAULT_VALIDATION_FOR_SUBSCRIPTION=default_number # Default number of validations required for a subscription
```

## API Endpoints

The service provides a REST API for interaction with the main bot `@SciSourceBot`. All endpoints require an `X-API-Token` header for authorization.

| Method | Path                                    | Description                                                              |
| :----- | :-------------------------------------- | :----------------------------------------------------------------------- |
| `POST` | `/api/request-pdf/`                     | Creates a new request to find an article by DOI.                         |
| `PUT`  | `/api/request-pdf/<int:pk>/`            | Updates an existing request (e.g., setting `message_search_id`).       |
| `POST` | `/api/validate_broken-pdf/`             | Receives a "broken" PDF from the main bot and initiates its validation.  |

## Background Tasks (Celery Beat)

The scheduler runs periodic tasks to keep the system up-to-date:

| Task                                       | Schedule           | Description                                                                                                |
| ------------------------------------------ | ------------------ | ---------------------------------------------------------------------------------------------------------- |
| `bot.tasks.run_check`                      | Every hour         | Finds expired requests (older than 47 hours), changes their status to `expired`, and notifies the main service. |
| `bot.tasks.run_check_and_delete_pdf`       | Every hour         | Deletes messages with PDF files that were uploaded or validated more than 47 hours ago.                  |
| `bot.tasks.run_check_and_delete_thank_message` | Every 20 minutes     | Deletes temporary "thank you" messages sent to users in the chat (lifespan - 1 hour).                      |

## Testing

To run the tests, use `pytest`:

```bash
poetry run pytest
```

## License

This project is licensed under the terms specified in the `LICENSE` file.

## Contributors


<table>
  <tr>
        <td align="center">
      <a href="https://github.com/TatyanaYus">
        <img src="https://github.com/TatyanaYus.png?size=100" width="100px;" alt="TatyanaYus"/>
        <br />
        <sub><b>TatyanaYus</b></sub>
      </a>
    </td>
        <td align="center">
      <a href="https://github.com/aeee78">
        <img src="https://github.com/aeee78.png?size=100" width="100px;" alt="aeee78"/>
        <br />
        <sub><b>aeee78</b></sub>
      </a>
    </td>
        <td align="center">
      <a href="https://github.com/AndreyZimin99">
        <img src="https://github.com/AndreyZimin99.png?size=100" width="100px;" alt="AndreyZimin99"/>
        <br />
        <sub><b>AndreyZimin99</b></sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/FrostWillmott">
        <img src="https://github.com/FrostWillmott.png?size=100" width="100px;" alt="FrostWillmott"/>
        <br />
        <sub><b>FrostWillmott</b></sub>
      </a>
    </td>

  </tr>
</table>