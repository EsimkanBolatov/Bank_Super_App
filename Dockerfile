# 1. Берем легкий образ Python
FROM python:3.12-slim

# 2. Отключаем кэширование питона (чтобы логи были видны сразу)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Рабочая папка внутри контейнера
WORKDIR /app

# 4. Устанавливаем системные зависимости (нужны для сборки некоторых либ)
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# 5. Копируем файл зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Копируем весь код проекта
COPY . .

# 7. Открываем порт 8000
EXPOSE 8000

# 8. Команда запуска (применит миграции и запустит сервер)
# Используем shell-скрипт, чтобы сначала накатить миграции
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]