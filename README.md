# BankNifty Option Chain Collector

Python backend service for collecting BankNifty option chain data from GoCharting using Selenium.

## Features

- Collects option chain data for BANKNIFTY
- Fetches OHLC, volume, cumulative delta, buy/sell volumes
- Concurrent data collection using multiple browser tabs
- REST API with authentication
- SQLite database for storage
- Docker-ready for easy deployment

## Quick Start with Docker

```bash
docker compose up -d
```

## Environment Variables

See `.env.docker.example` for all configuration options.

Key variables:
- `API_KEY` - API authentication key
- `BNF_HEADLESS` - Run Chrome in headless mode (true/false)
- `BNF_FETCH_TIMEOUT` - Timeout for data fetching (seconds)
- `BNF_CONCURRENCY` - Number of concurrent tabs (1-10)

## API Endpoints

All endpoints except `/api/health` require `X-API-Key` header.

- `GET /api/health` - Health check
- `POST /api/collect` - Collect option chain data
  ```json
  {
    "center": 50000,
    "expiry": "24JAN",
    "step": 100
  }
  ```
- `GET /api/option-chain/latest` - Get latest collected data
- `GET /api/runs` - List collection runs
- `GET /api/runs/:id` - Get specific run details

## First Time Setup

1. Run the login script to create GoCharting session:
   ```bash
   python login.py
   ```

2. Login to GoCharting in the browser window

3. Press Enter to save the session

## Deployment on Coolify

See `README.coolify.md` for deployment instructions.
