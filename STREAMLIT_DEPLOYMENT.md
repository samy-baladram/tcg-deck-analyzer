# Streamlit Cloud Deployment Guide

## Prerequisites
- GitHub account (free)
- Streamlit Community Cloud account (free)
- Your code pushed to GitHub

## Deployment Steps

### 1. Push Your Code to GitHub
```bash
cd /workspaces/tcg-deck-analyzer
git add .
git commit -m "Prepare for Streamlit Cloud deployment"
git push origin main
```

### 2. Create a Streamlit Community Cloud Account
1. Go to https://streamlit.io/cloud
2. Click **"Start for free"**
3. Sign in with GitHub
4. Authorize Streamlit to access your repositories

### 3. Deploy Your App
1. Go to https://share.streamlit.io
2. Click **"New app"** button
3. Fill in the deployment form:
   - **Repository**: `samy-baladram/tcg-deck-analyzer`
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. Click **"Deploy!"**

Streamlit will:
- ✅ Install all packages from `requirements.txt`
- ✅ Load your `.streamlit/config.toml` settings
- ✅ Launch your app automatically
- ✅ Give you a public URL (e.g., `https://tcg-deck-analyzer.streamlit.app`)

### 4. Automatic Updates
**The best part**: Every time you push to GitHub, your app updates automatically! No manual redeployment needed.

### 5. Important Configuration
- **Secrets**: `secrets.toml` values go in Streamlit Cloud's secrets management panel
  - In Streamlit Cloud app settings, add any environment variables there
- **Cache**: The `cached_data/` folder will persist between reloads
- **Data Limits**: Free tier has 4GB app data storage

## After Deployment

Your app will have a share button to get the public URL. You can:
- Share the link with anyone
- It runs 24/7 (as long as Streamlit keeps the service running)
- Access it from your phone, tablet, anywhere

## Costs
- **Free tier**: Always free for community usage, limited computational resources
- **Professional tier**: $5-15/month for more power and custom domains

See https://streamlit.io/cloud for pricing details.
