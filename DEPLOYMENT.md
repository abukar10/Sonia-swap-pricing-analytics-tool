# Streamlit App Deployment Guide

This guide covers multiple deployment options for your GBP SONIA Interest Rate Swap Pricing Analytics Tool.

## Option 1: Streamlit Cloud (Recommended - Free & Easiest)

Streamlit Cloud is the official hosting platform for Streamlit apps. It's free and integrates seamlessly with GitHub.

### Prerequisites:
- Your code is already on GitHub ✅
- A GitHub account ✅

### Steps:

1. **Sign up for Streamlit Cloud**
   - Go to https://share.streamlit.io/
   - Click "Sign in" and authorize with your GitHub account

2. **Deploy your app**
   - Click "New app" button
   - Select your repository: `abukar10/Sonia-swap-pricing-analytics-tool`
   - Select branch: `main`
   - Main file path: `app.py`
   - Click "Deploy!"

3. **Wait for deployment**
   - Streamlit Cloud will automatically:
     - Install dependencies from `requirements.txt`
     - Run your app
     - Provide you with a public URL (e.g., `https://sonia-swap-pricing-analytics-tool.streamlit.app`)

4. **Your app is live!**
   - Share the URL with anyone
   - Updates are automatic when you push to GitHub

### Configuration:
- No additional configuration needed for basic apps
- Your app will automatically update when you push changes to GitHub

---

## Option 2: Heroku

### Prerequisites:
- Heroku account (free tier available)
- Heroku CLI installed

### Steps:

1. **Install Heroku CLI**
   - Download from: https://devcenter.heroku.com/articles/heroku-cli

2. **Create required files** (already created):
   - `requirements.txt` ✅
   - `Procfile` (needs to be created)

3. **Login to Heroku**
   ```bash
   heroku login
   ```

4. **Create Heroku app**
   ```bash
   heroku create your-app-name
   ```

5. **Deploy**
   ```bash
   git push heroku main
   ```

6. **Open your app**
   ```bash
   heroku open
   ```

---

## Option 3: Docker + Cloud Platform

Deploy using Docker containers on platforms like:
- AWS ECS/Fargate
- Google Cloud Run
- Azure Container Instances
- DigitalOcean App Platform

### Dockerfile (if needed):
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

---

## Option 4: Local Network Deployment

Run on your local machine and share via local network:

```bash
streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

Then access from other devices on the same network using your machine's IP address.

---

## Recommended: Streamlit Cloud

For your use case, **Streamlit Cloud is the best option** because:
- ✅ Free
- ✅ Easy setup (just connect GitHub)
- ✅ Automatic updates
- ✅ No server management
- ✅ Public URL for sharing
- ✅ Secure (HTTPS by default)

---

## Troubleshooting

### If deployment fails:
1. Check `requirements.txt` has all dependencies
2. Ensure `app.py` is in the root directory
3. Check Streamlit Cloud logs for errors
4. Verify all data files are included in the repository

### Common issues:
- **Import errors**: Make sure all Python packages are in `requirements.txt`
- **File not found**: Ensure data files are committed to Git
- **Port issues**: Streamlit Cloud handles this automatically

---

## Next Steps After Deployment

1. Customize your app URL (Streamlit Cloud allows this)
2. Add authentication if needed (Streamlit Cloud Pro)
3. Monitor usage and performance
4. Set up custom domain (optional)

