# Push to Git Repository

## Step 1: Create a new repository on GitHub

1. Go to https://github.com/new
2. Name it: `banknifty-option-chain`
3. Keep it **Private** (recommended for trading apps)
4. Don't initialize with README (we already have one)
5. Click "Create repository"

## Step 2: Push your code

Run these commands in the `banknifty-python-backend` folder:

```bash
# Replace YOUR_USERNAME with your GitHub username
git remote add origin https://github.com/YOUR_USERNAME/banknifty-option-chain.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Step 3: Use in Coolify

1. Go to http://52.5.107.23:8000/
2. Click "New Resource" → "Application"
3. Choose "Public Repository" or connect your GitHub account
4. Paste repository URL: `https://github.com/YOUR_USERNAME/banknifty-option-chain.git`
5. Set branch: `main`
6. Add environment variables:
   ```
   API_KEY=bnf_live_prod_f8d2k3m9x7p5q1w4
   ```
7. Set port: `5050`
8. Deploy!

## Alternative: GitLab or other Git hosting

If using GitLab or another service:
```bash
git remote add origin YOUR_GIT_URL
git branch -M main
git push -u origin main
```

Then use the same URL in Coolify.
