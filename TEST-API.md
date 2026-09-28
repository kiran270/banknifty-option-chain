# API Testing Guide

## Base URL
```
http://52.5.107.23
```

## API Key
```
bnf_live_prod_f8d2k3m9x7p5q1w4
```

---

## 1. Health Check (No Auth Required)

```bash
curl http://52.5.107.23/api/health
```

**Expected Response:**
```json
{"ok": true}
```

---

## 2. List Collection Runs

```bash
curl -H "X-API-Key: bnf_live_prod_f8d2k3m9x7p5q1w4" \
  http://52.5.107.23/api/runs
```

---

## 3. Get Latest Option Chain

```bash
curl -H "X-API-Key: bnf_live_prod_f8d2k3m9x7p5q1w4" \
  http://52.5.107.23/api/option-chain/latest
```

---

## 4. Collect Option Chain Data

**⚠️ WARNING:** This will use real Chrome session and collect data from GoCharting.

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

**Parameters:**
- `center`: Strike price center (e.g., 50000)
- `expiry`: Expiry date in format "DDMMM" (e.g., "30JAN", "06FEB")
- `step`: Strike price step (usually 100)

---

## 5. Get Specific Run Details

```bash
# Replace <run_id> with actual ID from runs list
curl -H "X-API-Key: bnf_live_prod_f8d2k3m9x7p5q1w4" \
  http://52.5.107.23/api/runs/<run_id>
```

---

## Next Steps

1. **Setup GoCharting Session** (Required before collecting data):
   - SSH into Coolify server
   - Run: `docker exec -it <container-name> python login.py`
   - Login to GoCharting when prompted
   - Session will be saved automatically

2. **Test Data Collection**:
   - Use endpoint #4 above with current BANKNIFTY center and expiry
   - Check status with endpoint #2
   - View results with endpoint #3

---

## Troubleshooting

- **401 Unauthorized**: Check API key in headers
- **409 Conflict**: Collection already running, wait for it to complete
- **Error in response**: Check container logs or verify GoCharting session exists

---

## Status: ✅ DEPLOYED & VERIFIED

- Health check: ✅ Working
- Authentication: ✅ Working  
- Database: ✅ Initialized
- Ready for data collection after GoCharting login
