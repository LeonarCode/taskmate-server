# TaskMate API

FastAPI backend for **TaskMate**, a mobile app for managing personal tasks and collaborating in study/work groups ("servers"). It replaces the app's original Firebase backend with a REST + WebSocket API on PostgreSQL.

## Features

- **Auth** – email/password (bcrypt), Google sign-in (ID token), JWT access tokens, forgot-password with a 6-digit code sent by email
- **Personal tasks** – offline-first sync: the app creates the task with a UUID (`client_id`) and upserts it whenever it is online
- **Direct messages** – text, image and task-reference messages, edit, soft delete, read receipts, unread counts
- **Servers** – create, discover, join and leave groups with an owner/member role model
- **Group tasks and group chat** – the owner manages tasks, members mark them complete
- **Ratings** – members rate each other (1–5 stars, half steps allowed) and each user's average is kept up to date
- **Notifications** – an alerts feed that is also pushed live over WebSocket
- **Profile** – edit profile, photo upload (Cloudinary), search users by username

## Tech stack

| | |
|---|---|
| Framework | FastAPI, Pydantic v2 |
| Database | PostgreSQL via SQLAlchemy 2 (async) and asyncpg |
| Migrations | Alembic |
| Auth | PyJWT, bcrypt, google-auth |
| Images | Cloudinary |
| Real-time | WebSockets (single `/ws` connection per device) |
| Runtime | Python 3.13, Docker Compose |

## Getting started

### Prerequisites

- Docker Desktop
- A PostgreSQL server reachable from Docker. `docker-compose.yml` does not start a database; it connects to the one on your machine through `host.docker.internal`
- A Google OAuth client ID (used to verify Google ID tokens)

### Setup

```bash
# 1. Create an empty database (name it as you like)
createdb taskmate

# 2. Create your .env from the template and fill it in (see "Configuration")
cp .env.example .env

# 3. Build and start the API (auto-reloads when you edit code)
docker compose up -d --build

# 4. Create the tables
docker compose exec api alembic upgrade head
```

Open **http://localhost:8000/docs** for the interactive API docs (Swagger UI).

Useful commands:

```bash
docker compose logs -f api                  # follow the logs
docker compose up -d --force-recreate api   # restart after changing .env
```

### Without Docker

```bash
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
alembic upgrade head
```

Use `localhost` instead of `host.docker.internal` in `DOCKER_DATABASE_URL`.

## Configuration

Settings are read from `.env` (see `config/settings.py`). Never commit this file.

| Variable | Required | Description |
|---|---|---|
| `DOCKER_DATABASE_URL` | yes | `postgresql+asyncpg://USER:PASSWORD@host.docker.internal:5432/taskmate`. URL-encode special characters in the password |
| `SECRET_KEY` | yes | Signs the JWTs. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `GOOGLE_CLIENT_ID` | yes | OAuth client ID that Google ID tokens must be issued for |
| `ALGORITHM` | no | JWT algorithm, default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | Default `10080` (7 days) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | no | Email for forgot-password. Port `587` uses STARTTLS and `465` uses SSL. **Without `SMTP_HOST` the code is only written to the log**, which is handy in development |
| `CLOUDINARY_URL` | no | `cloudinary://API_KEY:API_SECRET@CLOUD_NAME`. Without it, profile photos are stored in the database instead (development only, up to 600 KB) |

## Database migrations

```bash
# after changing a model
docker compose exec api alembic revision --autogenerate -m "describe the change"
docker compose exec api alembic upgrade head

# verify that models and migrations agree
docker compose exec api alembic check
```

Autogenerate does not detect `CheckConstraint`s. Add those to the migration by hand and review every generated file before applying it.

## Project structure

```
main.py             app creation, CORS, router registration
config/             settings (.env) and the async database engine/session
models/             SQLAlchemy models
schemas/            Pydantic request/response models
repositories/       database queries only
services/           business rules and permission checks
routers/            HTTP and WebSocket endpoints
utils/              JWT/password helpers, auth dependencies, error handling,
                    WebSocket connection manager, email, Cloudinary
alembic/            migrations
```

Requests flow `router → service → repository → model`. Routers stay thin, business rules and permission checks live in the services, and the SQL lives in the repositories.

## API overview

Everything except the public `/auth` endpoints requires `Authorization: Bearer <token>`. The full request and response shapes are in `/docs`.

### Auth and users

| Method | Path | Purpose |
|---|---|---|
| GET | `/auth/check-email`, `/auth/check-username` | Availability checks while signing up |
| POST | `/auth/register`, `/auth/login` | Email/password; both return a token |
| POST | `/auth/google`, `/auth/google/register` | Google sign-in. A `404 user_not_found` on login means "show the profile setup" |
| POST | `/auth/forgot-password`, `/auth/reset-password` | Email a 6-digit code, then set a new password |
| GET | `/auth/me` | Current user |
| GET | `/users/search?q=` | Find users by username prefix |
| PATCH | `/users/me` | Edit full name, age, user type, organization |
| PUT | `/users/me/photo` | Upload a profile photo (`multipart/form-data`, field `file`: jpeg, png, webp or gif, up to 5 MB) |
| GET | `/users/{id}/photo` | A user's photo |

### Tasks and messages

| Method | Path | Purpose |
|---|---|---|
| GET, POST | `/task` | List / create personal tasks |
| PUT, DELETE | `/task/{client_id}` | Idempotent upsert (including the completed checkbox) and delete |
| GET | `/messages` | Conversation list with last message and unread count |
| GET, POST | `/messages/{other_user_id}` | Conversation history / send a message |
| PATCH, DELETE | `/messages/{other_user_id}/{message_id}` | Edit / soft-delete your own message |
| POST | `/messages/{other_user_id}/read` | Mark the conversation as read |

### Servers

| Method | Path | Purpose |
|---|---|---|
| GET, POST | `/server` | Servers you belong to / create one |
| GET | `/server/discover` | Servers you have not joined (`search`, `limit`, `offset`) |
| GET, PATCH, DELETE | `/server/{id}` | View / edit / delete (owner only for edit and delete) |
| POST | `/server/{id}/join`, `/server/{id}/leave` | Join or leave (the owner cannot leave) |
| GET | `/server/{id}/members` | Members with their ratings |
| GET, POST | `/server/task/{server_id}` | List / create group tasks |
| PATCH, DELETE | `/server/task/{server_id}/{task_id}` | Edit / delete a group task |
| POST | `/server/task/{server_id}/{task_id}/complete`, `/incomplete` | Mark complete / undo |
| GET, POST | `/server/messages/{server_id}` | Group chat history / send |
| PATCH, DELETE | `/server/messages/{server_id}/{message_id}` | Edit / soft-delete your own message |

### Ratings and notifications

| Method | Path | Purpose |
|---|---|---|
| PUT, DELETE | `/ratings/{server_id}/{rated_id}` | Rate a fellow member (replaces your earlier rating) / withdraw it |
| GET | `/ratings/given?server_id=` | Ratings you gave, to prefill the stars |
| GET | `/ratings/received` | Ratings you received, with comments |
| GET | `/notifications` | Feed (`limit`, `before_id`, `unread_only`) |
| GET | `/notifications/unread-count` | Badge number |
| POST | `/notifications/read-all`, `/notifications/{id}/read` | Mark as read |
| DELETE | `/notifications`, `/notifications/{id}` | Clear all / delete one |

A user's average rating and rating count are part of the user objects (`average_rating`, `rating_count`).

### Permissions in a server

| | Owner | Member |
|---|---|---|
| Edit or delete the server | yes | no |
| Create, edit, delete or un-complete group tasks | yes | no |
| View group tasks and mark them complete | yes | yes |
| Send group messages, edit or delete your own | yes | yes |
| Rate other members (and be rated) | yes | yes |
| Leave the server | no (delete it instead) | yes |

Users who are not in a server get `404` for everything in it, as if it did not exist. Members who lack the right to do something get `403`.

## Real-time

Connect once per device to `ws://localhost:8000/ws` with `Authorization: Bearer <token>` (or `?token=<token>`, which ends up in access logs). Send the text `ping` now and then and the server answers `pong`.

The app still sends data through the REST endpoints, which validate it and return errors. The server then pushes events to everyone else involved. Every message has the shape `{"type": ..., "data": ...}`:

| Type | Data |
|---|---|
| `message`, `message_edited` | the message |
| `message_deleted` | `{id}` |
| `read` | `{reader_id}` |
| `group_message`, `group_message_edited` | the message, with `server_id` |
| `group_message_deleted` | `{id, server_id}` |
| `notification` | the notification, same shape as in `GET /notifications` |
| `notification_read`, `notification_deleted` | `{id}` |
| `notifications_read_all`, `notifications_cleared` | `{}` |

The last four keep the notification badge in sync across all of a user's devices.

Notifications are created when someone joins or leaves your server, when the owner adds a group task, when a member completes one, and when a server you belong to is deleted.

## Conventions

- **Errors** are JSON like `{"detail": "Email is already registered", "code": "email_taken"}`. Codes include `invalid_credentials`, `unauthorized`, `not_found`, `user_not_found`, `bad_request`, `forbidden`, `invalid_code`, `email_taken`, `username_taken`, `file_too_large` and `storage_unavailable`. Request validation errors use FastAPI's standard `422` format
- **Paging** uses `limit` plus `before_id` (the id of the oldest item you already have)
- **Dates** are ISO 8601. Deadlines must include a timezone (`Z` or `+08:00`)
- **Deleting** a message or a group task is a soft delete
- Repeating an action is safe wherever it makes sense (join, mark complete, task upsert, delete)

## Known limitations

- No push notifications while the app is closed. The `fcm_token` column exists but is not used yet
- No automated test suite in the repository yet
