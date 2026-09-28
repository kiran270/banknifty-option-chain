# Coolify Deployment Guide

## Quick Deploy

1. **Add New Resource** in Coolify
   - Choose "Docker Image" or "Dockerfile"
   - Connect your Git repository

2. **Environment Variables** (Add in Coolify):
   ```
   API_KEY=your-secret-api-key-here
   BNF_FETCH_TIMEOUT=15
   BNF_CONCURRENCY=5
   BNF_HEADLESS=true
   ```

3. **Port Configuration**:
   - Container Port: `5050`
   - Public Port: Your choice (or auto)

4. **Volume Mount** (Recommended):
   - Mount `/app/data` to persist database and session data

5. **Deploy** and wait for health check to pass

## First Time Setup

After deployment, you need to create a GoCharting session:

1. SSH into your container or run locally:
   ```bash
   docker exec -it <container-name> python login.py
   ```

2. Follow the prompts to login to GoCharting

3. Session will be saved to `/app/data/session.json`

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/collect` - Collect option chain data
- `GET /api/option-chain/latest` - Get latest data
- `GET /api/runs` - List collection runs
- `GET /api/runs/:id` - Get specific run details

All endpoints (except health) require `X-API-Key` header.

## Example API Call

```bash
curl -X POST https://your-domain.com/api/collect \
  -H "X-API-Key: your-secret-api-key" \
  -H "Content-Type: application/json" \
  -d '{"center": 50000, "expiry": "24JAN", "step": 100}'
```
