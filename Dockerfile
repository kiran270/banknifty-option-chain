FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BNF_PROFILE_DIR=/app/data/chrome-profile \
    BNF_SESSION_FILE=/app/data/session.json \
    BNF_DB_PATH=/app/data/banknifty.db \
    BNF_FETCH_TIMEOUT=15 \
    BNF_CONCURRENCY=5 \
    BNF_HEADLESS=true \
    API_HOST=0.0.0.0 \
    API_PORT=5050 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 \
    libasound2 libatspi2.0-0 libwayland-client0 \
    fonts-liberation ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

COPY . .
RUN mkdir -p /app/data/chrome-profile && chmod -R 777 /app/data

EXPOSE 5050

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5050/api/health')" || exit 1

CMD ["python", "app.py"]
