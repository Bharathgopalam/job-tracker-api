# Job Tracker API

A REST API for tracking job applications, built with **FastAPI**, **SQLAlchemy 2.0** and **JWT
authentication**. It enforces a realistic application workflow (you cannot jump from `wishlist`
straight to `offer`), keeps every user's data private, and reports pipeline statistics.

## Run it

```bash
pip install -r requirements-dev.txt
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
uvicorn app.main:app --reload
# interactive docs: http://127.0.0.1:8000/docs
python -m pytest
```

Quick tour with curl:

```bash
curl -X POST localhost:8000/auth/register -H 'Content-Type: application/json' \
     -d '{"email":"me@example.com","password":"supersecret1"}'
TOKEN=$(curl -s -X POST localhost:8000/auth/login -d 'username=me@example.com&password=supersecret1' \
        | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -X POST localhost:8000/applications -H "Authorization: Bearer $TOKEN" \
     -H 'Content-Type: application/json' -d '{"company":"Acme","role":"Data Engineer"}'
curl -X POST localhost:8000/applications/1/status -H "Authorization: Bearer $TOKEN" \
     -H 'Content-Type: application/json' -d '{"status":"applied"}'
curl localhost:8000/stats -H "Authorization: Bearer $TOKEN"
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create an account (email is normalized, duplicates return 409) |
| POST | `/auth/login` | OAuth2 password flow, returns a JWT |
| GET | `/auth/me` | Current user |
| POST | `/applications` | Create an application (starts as `wishlist`) |
| GET | `/applications` | List with `status`, `q` (search), `limit`, `offset` |
| GET / PATCH / DELETE | `/applications/{id}` | Read, partially update, delete |
| POST | `/applications/{id}/status` | Move through the workflow (invalid moves return 409) |
| GET | `/stats` | Counts by status, response rate, interview rate |
| GET | `/health` | Liveness check |

## Status workflow

```
wishlist -> applied -> screening -> interview -> offer -> accepted
              |            |            |          |
              +------------+------------+----------+--> rejected / withdrawn  (final)
```

The rules live in `app/domain.py` as plain Python with no framework code, so they are easy to test.

## Design decisions

- **Layered structure.** Routers handle HTTP, `domain.py` holds business rules, `models.py` the
  database, `schemas.py` validation and serialization.
- **Ownership by construction.** Every query filters on the current user's id, and other users' ids return
  404, not 403, so ids cannot be probed.
- **Passwords:** salted PBKDF2-HMAC-SHA256 (310k iterations) from the standard library, compared in
  constant time. Login does the same work whether or not the email exists, and returns identical errors.
- **No default secret.** Missing `SECRET_KEY` produces an ephemeral random key and a warning, never a
  hard-coded fallback.
- **Search escapes `%` and `_`** so user input is a literal, not a wildcard.
- **Tests use an in-memory database** and override the DB dependency, so they are fast and isolated.

## Docker

```bash
docker build -t job-tracker-api .
docker run -e SECRET_KEY=... -p 8000:8000 job-tracker-api
```

## Honest limitations

- The `Dockerfile` has not been built or run yet. Test it before relying on it.
- The schema is created with `create_all`. A real deployment should use Alembic migrations.
- No rate limiting, refresh tokens, or email verification.
- Tested against SQLite only. SQLAlchemy makes Postgres a one-line `DATABASE_URL` change (plus a driver),
  but that path is untested here.

## Ideas to extend it

1. Add Alembic migrations and switch to Postgres with docker-compose.
2. Add refresh tokens and a logout/revoke list.
3. Add an `interviews` table (one-to-many) with dates and notes.
4. Add rate limiting on `/auth/login`.
5. Add structured logging and a request-id middleware.
6. Build a small frontend, or feed `/stats` into a dashboard.
