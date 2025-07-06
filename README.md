# SciArticle

[![en](https://img.shields.io/badge/language-EN-green.svg)](README.md)
[![ru](https://img.shields.io/badge/language-RU-red.svg)](docs/RU_docs/README_ru.md)

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-5.2+-blue.svg)](https://www.djangoproject.com/)


**SciArticle** is a server-side application and Telegram bot designed for crowdsourcing and validating scientific articles in PDF format.
The bot allows users to upload article PDFs, vote on the validity of uploaded documents, and receive a subscription for active participation.

The bot interacts with another service — `@SciSourceBot` — via an internal REST API, enabling the following features:
- registration of article requests (by DOI)
- validation and re-validation of PDF files
- sending notifications to the public chat
- tracking user activity and granting subscriptions

## [Architecture and How It Works](docs/EN_docs/architecture.md)

## Tech Stack

- **Backend**: Django, Django REST Framework
- **Database**: PostgreSQL
- **Task Queue**: Celery
- **Message Broker**: Redis
- **Telegram Bot**: python-telegram-bot
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
## [Installation and Launch](docs/EN_docs/installation.md)

## Environment Variables

Create a `.env` file in the `infra` directory and define the variables from `env.example` in it.

```python
TELEGRAM_BOT_TOKEN=your_bot_token_here # The @SciArticleBot bot

SOURCE_SERVER_URL=http://your-api   # URL of the service that accepts POST requests

SEARCH_CHAT_ID=id_sciarticle_search_chat   # The main chat for all users

API_SECRET_TOKEN=your_secret_token   # For securing HTTP requests between services without user involvement
```
## API Endpoints

The internal REST API is used for data exchange between two Telegram bots: `@SciArticleBot` and `@SciSourceBot`.

All requests between the bots are secured using an API token.

## Used HTTP methods:
| Method | Purpose                      |
|--------|------------------------------|
| `POST` | Create and transmit data     |
| `GET`  | Retrieve information         |
| `PUT`  | Update data                  |

## [API Documentation](docs/EN_docs/api_reference.md)

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