# Deployment Guide — Render + PostgreSQL

This guide explains how to deploy this project to Render in under 5 minutes using the included `render.yaml` blueprint.

## 🚀 One-Click Deployment (Recommended)

Render uses **Blueprints** to automatically set up your database and web service with the correct environment variables.

### Step 1: Push to GitHub
1. Create a new repository on GitHub.
2. Copy the contents of this folder (`BlockchainDemo_ReadyForDeploy`) into that repository.
3. Commit and push:
   ```bash
   git init
   git add .
   git commit -m "Initial commit for Blockchain Demo"
   git remote add origin YOUR_REPO_URL
   git push -u origin main
   ```

### Step 2: Connect to Render
1. Log in to [Render.com](https://dashboard.render.com).
2. Click **"New"** (top right) → **"Blueprint"**.
3. Connect your GitHub repository.
4. Render will automatically detect the `render.yaml` file.
5. Click **"Apply"**.

### What happens next?
- **Database**: Render will automatically create a private PostgreSQL database named `blockchain-demo-db`.
- **Web Service**: Render will build the Python app, install dependencies, and start the Gunicorn server.
- **Connection**: The `DATABASE_URL` from the new database is automatically injected into the web service. No manual copy-pasting required!

---

## 🛠 Manual Database Setup (Alternative)

If you prefer to set things up manually:

1. **Create Database**: Create a "New PostgreSQL" on Render.
2. **Copy internal URL**: Copy the **Internal Database URL**.
3. **Create Web Service**: Create a "New Web Service" and connect your repo.
4. **Environment Variables**: Add these in the "Environment" tab:
   - `DATABASE_URL`: (Paste your Internal Database URL here)
   - `FLASK_ENV`: `production`
   - `SECRET_KEY`: (Any long random string)
   - `JWT_SECRET_KEY`: (Any long random string)
   - `AUTH_USERS`: `{"alice":"password123","admin":"admin123"}`

---

## 🧪 Post-Deployment Testing
1. Once the status is "Live", go to `https://your-app.onrender.com/api/health`.
2. You should see `{"database": "connected", "status": "ok"}`.
3. Visit `https://your-app.onrender.com/apidocs/` to start testing with Swagger!
