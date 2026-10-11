FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Run as a non-root user; the SQLite file (if used) lives in /app/data.
RUN useradd --create-home appuser && mkdir -p /app/data && chown -R appuser /app
USER appuser

ENV DATABASE_URL=sqlite:////app/data/jobtracker.db
EXPOSE 8000

# SECRET_KEY must be provided at runtime: docker run -e SECRET_KEY=... -p 8000:8000 <image>
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
