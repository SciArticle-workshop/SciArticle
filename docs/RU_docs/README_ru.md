# SciArticle


[![en](https://img.shields.io/badge/language-EN-green.svg)](../../README.md)
[![ru](https://img.shields.io/badge/language-RU-red.svg)](README_ru.md)

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-5.2+-blue.svg)](https://www.djangoproject.com/)


**SciArticle** — это серверное приложение и Telegram-бот, предназначенные для организации краудсорсинга и валидации научных статей в PDF-формате.
Бот позволяет пользователям загружать PDF-файлы статей, голосовать за корректность загруженных документов, а также получать подписку за активное участие.

Бот взаимодействует с другим сервисом — `@SciSourceBot` — через внутренний REST API, обеспечивая:
- регистрацию запросов на статьи (по DOI)
- проверку и повторную проверку PDF-файлов
- отправку уведомлений в общий чат
- учёт пользовательской активности и выдачу подписки
 
## [Документация по Архитектуре ](architecture_ru.md)

## Стек технологий

- **Бэкенд**: Django, Django REST Framework
- **База данных**: PostgreSQL
- **Очередь задач**: Celery
- **Брокер сообщений**: Redis
- **Telegram-бот**: python-telegram-bot
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

## [Установка и запуск](installation_ru.md)

## Переменные окружения

Создайте файл `.env` в директории infra и определите в нем переменные из `env.example`.

```python
TELEGRAM_BOT_TOKEN=your_bot_token_here # Бот @SciArticleBot

BOT_NAME_SCISOURCE=username # Username Ботa @SciSourceBot

SOURCE_SERVER_URL=http://your-api # URL сервиса, который принимает POST-запросы

SEARCH_CHAT_ID=id_sciarticle_search_chat  # Общий чат всех пользователей

API_SECRET_TOKEN=your_secret_token  # Для защиты HTTP-запросов между сервисами без участия пользователей
```
## API Endpoints

Внутренний REST API используется для обмена данными между двумя Telegram-ботами: `@SciArticleBot` и `@SciSourceBot`.

Все запросы между ботами защищены с помощью API токена.

### Используемые методы:
| Метод | Назначение                     |
|-------|--------------------------------|
| `POST`| Создание и передача данных     |
| `GET` | Получение информации           |
| `PUT` | Обновление данных              |


## [Документация API](api_reference_ru.md)

## Тестирование

Для запуска тестов используйте `pytest`:

```bash
poetry run pytest
```

## Лицензия

Этот проект лицензирован в соответствии с условиями, указанными в файле `LICENSE`.

## Авторы проекта

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
