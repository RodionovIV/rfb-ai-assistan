FROM python:3.10-slim

WORKDIR /app

# Установка uv
RUN pip install uv

# Копируем файлы зависимостей
COPY pyproject.toml ./

# Сначала создаем lockfile, потом синхронизируем
RUN uv lock && uv sync --frozen

# Копируем исходный код
COPY . .

# Создаем .env с минимальными настройками
RUN echo "APP_HOST=0.0.0.0" > .env && echo "APP_PORT=8000" >> .env

EXPOSE 8000

CMD ["uv", "run", "app.py"]
