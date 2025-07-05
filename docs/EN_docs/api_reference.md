# API Reference - Documentation of HTTP interaction between services
This document describes the HTTP requests exchanged between two services - the bots (`@SciArticleBot` and `@SciSourceBot`), to ensure correct data transfer during their interaction.

## Authentication
All requests are secured with an API token passed in the header:

```
X-API-Token: <secret_token>
```
The token is stored in a .env file and verified on the recipient's side.

## List of Endpoints

<a id="#1"></a>

## 1

### Sending information about article requests to be deleted.


**URL:** `/api/request-pdf-expired/`

**Method:** `POST`

**Description:** The `@SciArticleBot` notifies the `@SciSourceBot` that a request should be deleted. Possible reason: the request(s) has expired, or a PDF file has been published for verification in the public `SciArticle Search` chat.

**Parameters:**

| Field             | Type  | Description                                       |
|-------------------|-------|---------------------------------------------------|
| `message_id`      | int   | ID of the user's message in the chat with @SciSourceBot |
| `chat_id`         | int   | User's Telegram ID                                |
| `message_search_id`| int   | ID of the message in the public 'SciArticle Search' chat |

**Response:**

- `204 No Content` — successfully processed
- `400 Bad Request` — error in the request
- `500 Internal Server Error` - server error

<br>
<a id="#2"></a>

## 2

### Republishing an article request

**URL:** `/api/new_request-pdf/`

**Method:** `POST`

**Description:** The `@SciArticleBot` sends a request to the `@SciSourceBot` with data to republish an article request in the public chat, and receives a response with the new request's data.

**Parameters:**

| Field    | Type  | Description         |
|----------|-------|---------------------|
| `doi`    | str   | DOI of the article  |

**Response:**

- `200 OK` with JSON: `{ 'message_id': <int> }`— ID of the sent message in the public 'SciArticle Search' chat
- `400 Bad Request` — error in the request
- `500 Internal Server Error` - server error

<br>
<a id="#3"></a>

## 3

### Check if a user exists


**URL:** `/api/tg_user/<telegram_id>`

**Method:** `GET`

**Description:** The `@SciArticleBot` sends a request to the `@SciSourceBot` to check if a user is subscribed to it.

**Response:**
- `200 OK` — user found
- `400 Bad Request` — error in the request
- `404 Not Found` - user not found
- `500 Internal Server Error` - server error

<br>
<a id="#4"></a>

## 4

### Sending counter information

**URL:** `/api/user_counters/`

**Method:** `POST`

**Description:** The `@SciArticleBot` sends information about user uploads and validations to the `@SciSourceBot` and receives a response with data.

**Parameters:**

| Field       | Type   | Description                         |
|-------------|--------|-------------------------------------|
| `count`     | int    | Number of user uploads/validations  |
| `chat_id`   | int    | User's Telegram ID                  |
| `count_type`| str    | `'upload'` or `'validation'`        |
| `limit`     | int    | Threshold for subscription          |

**Response:**

- `200 OK` with JSON: `{'chat_id': <int>, 'message_id': <int>}`— User's Telegram ID, ID of the message sent to the user
- `400 Bad Request` — error in the request
- `500 Internal Server Error` - server error

<br>
<a id="#5"></a>

## 5

### Sending a PDF file and data

**URL:** `/api/upload-pdf/`

**Method:** `POST`

**Description:** The `@SciArticleBot` sends a verified (valid) PDF file and data to the `@SciSourceBot`.

**Parameters:**

| Field       | Type       | Description                                  |
|-------------|------------|----------------------------------------------|
| `file`      | file (PDF) | The document file (valid)                    |
| `chat_id`   | int        | Telegram ID of the user who uploaded the PDF |
| `message_id`| int        | Message ID                                   |
| `doi`       | str        | DOI of the article                           |

**Response:**

- `200 OK` — file and data received
- `400 Bad Request` — error in the request
- `500 Internal Server Error` - server error
<br>
<a id="#6"></a>

## 6

### Sending data about expired thank-you messages

**URL:** `/api/thank_message_delete/`

**Method:** `POST`

**Description:** The `@SciArticleBot` sends a request to the `@SciSourceBot` containing information about the message(s) that should be deleted.

**Parameters:**

| Field        | Type  | Description                   |
|--------------|-------|-------------------------------|
| `message_id` | int   | ID of the message in the chat |
| `chat_id`    | int   | User's Telegram ID            |

**Response:**

- `204 No Content` — success
- `400 Bad Request` — error in the request
- `500 Internal Server Error` - server error

<br>
<a id="#7"></a>

## 7

### Granting a subscription to a user

**URL:** `/api/grant-subscription/`

**Method:** `POST`

**Description:** The `@SciArticleBot` sends a request to the `@SciSourceBot` to grant a subscription and receives a response with the user's subscription data.

**Parameters:**

| Field        | Type    | Description                       |
|--------------|---------|-----------------------------------|
| `telegram_id`| int     | User's Telegram ID                |
| `reason`     | str     | Reason: `'uploads'` or `'validations'` |
| `amount`     | int     | Number of subscription months     |

**Response:**

- `200 OK` — JSON: `{'user_id': <int>, 'start_at': <str>, 'end_at': <str>}` - User's Telegram ID, subscription start date, subscription end date
- `400 Bad Request` — error in the request
- `404 Not Found` - user not found
- `500 Internal Server Error` - server error