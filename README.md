# job-tracker-api

I'm job hunting and was keeping track of applications in a spreadsheet, so I turned it into a small
backend project to practice building an API. It's a learning project built with FastAPI, SQLAlchemy and JWT login.

You can add applications, move them through stages (wishlist, applied, screening, interview, offer...),
and get simple stats like response rate and interview rate.

## Running it

```bash
pip install -r requirements-dev.txt
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
uvicorn app.main:app --reload
# docs at http://127.0.0.1:8000/docs
python -m pytest
```

## Endpoints

| Method | Path | What it does |
|--------|------|--------------|
| POST | `/auth/register` | create an account |
| POST | `/auth/login` | log in, returns a token |
| GET | `/auth/me` | current user |
| POST / GET | `/applications` | add an application / list them (filter by status, search) |
| GET / PATCH / DELETE | `/applications/{id}` | read, update, delete one |
| POST | `/applications/{id}/status` | change status |
| GET | `/stats` | counts by status, response rate, interview rate |

## Status rules

```
wishlist -> applied -> screening -> interview -> offer -> accepted
any active stage -> rejected or withdrawn
```

You can't skip stages (wishlist straight to offer returns an error). The rules are in `app/domain.py`,
kept separate from the API code so they're easy to test.

## Notes

- Each user only sees their own applications. Asking for someone else's id returns 404.
- Passwords are hashed with salted PBKDF2 (Python standard library).
- Tests run against an in-memory SQLite database.

## Not done yet

- I haven't built or run the Dockerfile yet.
- Tables are created on startup; a real setup should use Alembic migrations.
- Only tested on SQLite, not Postgres.
- No rate limiting or refresh tokens.
