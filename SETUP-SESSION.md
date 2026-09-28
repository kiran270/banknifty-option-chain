# GoCharting Session Setup Guide

## Problem
Chrome can't run interactively inside the Docker container for initial login.

## Solution
Create the session locally, then upload it to the container.

---

## Step 1: Create Session Locally (Windows)

1. **Install Python dependencies:**
   ```bash
   cd banknifty-python-backend
   pip install -r requirements.txt
   ```

2. **Run login script locally:**
   ```bash
   python login.py
   ```

3. **Login to GoCharting** in the Chrome window that opens

4. **Press Enter** in terminal when done

5. **Session saved to:** `data/session.json`

---

## Step 2: Upload Session to Container

From your local machine:

```bash
# Copy session.json to server
scp data/session.json ubuntu@52.5.107.23:~/session.json
```

Then on the server:

```bash
# Copy into container
docker cp ~/session.json b9aa54167cb2:/app/data/session.json

# Verify it exists
docker exec b9aa54167cb2 ls -la /app/data/session.json

# Check permissions
docker exec b9aa54167cb2 chmod 644 /app/data/session.json
```

---

## Step 3: Test Data Collection

```bash
curl -X POST \
  -H "X-API-Key: bnf_live_prod_f8d2k3m9x7p5q1w4" \
  -H "Content-Type: application/json" \
  -d '{
    "center": 50000,
    "expiry": "30JAN",
    "step": 100
  }' \
  http://52.5.107.23/api/collect
```

---

## Alternative: Use Existing Session

If you already have a GoCharting session from another project:

```bash
# Find your existing session
# It's usually in: gc-delta-fetch/.gc-profile/ or similar

# Copy to banknifty-python-backend
cp path/to/existing/session.json banknifty-python-backend/data/session.json

# Then upload to server (follow Step 2)
```

---

## Troubleshooting

**Session expires:**
- Re-run `python login.py` locally and upload again

**Chrome won't start locally:**
- Make sure Chrome/Chromium is installed
- Try running without headless mode

**Permission denied in container:**
```bash
docker exec b9aa54167cb2 chmod 777 /app/data
docker exec b9aa54167cb2 chmod 644 /app/data/session.json
```
