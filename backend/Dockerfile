FROM python:3.13-slim

WORKDIR /app

COPY . /app

# Установка uv
RUN pip install uv && uv sync

# Создаем .env с минимальными настройками
RUN echo "APP_HOST=0.0.0.0" > .env && echo "APP_PORT=8000" >> .env

EXPOSE 8000

CMD ["uv", "run", "app.py"]
