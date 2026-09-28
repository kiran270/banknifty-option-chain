# ⚠️ SECURITY WARNING

## session.json Contains Sensitive Data

The `data/session.json` file contains:
- Authentication cookies
- Access tokens (JWT tokens with expiry)
- Session identifiers
- User credentials

## Risks of Committing to Git

✅ **If repository is PRIVATE:**
- Acceptable for personal/team use
- Ensure only trusted collaborators have access
- Tokens will expire eventually and need refresh

❌ **If repository is PUBLIC:**
- **DO NOT commit session.json**
- Anyone can use your GoCharting session
- Could lead to account compromise

## Current Configuration

This repo is configured to **include** session.json in Git for deployment convenience.

**The repository MUST be kept PRIVATE on GitHub.**

## Best Practices

1. **Keep repo private** on GitHub/GitLab
2. **Rotate session** periodically by running `python login.py`
3. **Never share** the repository URL publicly
4. **Use environment variables** for truly sensitive production secrets

## Alternative: Environment Variables

For production, you can pass session as environment variable:

```bash
# In Coolify, set:
SESSION_JSON={"cookies":[...],...}
```

Then modify `collector.py` to read from env:
```python
import os
session_data = os.getenv('SESSION_JSON')
if session_data:
    SESSION_FILE.write_text(session_data)
```

But for simplicity, we're using the file-based approach with a PRIVATE repo.
