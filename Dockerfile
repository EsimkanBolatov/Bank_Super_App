FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Устанавливаем зависимости и явно выводим, где установился alembic
RUN pip install --no-cache-dir -r requirements.txt && \
    which alembic || echo "WARNING: Alembic executable not found in PATH"

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "/usr/local/bin/alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]