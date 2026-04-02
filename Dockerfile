FROM mcr.microsoft.com/playwright/python:v1.43.0-jammy

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Установка браузеров Playwright (Chromium)
RUN playwright install chromium

# Копируем остальной код
COPY . .

# Команда для запуска бота
CMD ["python", "main.py"]
