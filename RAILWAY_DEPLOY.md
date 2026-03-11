# Railway Deployment Guide - TraderAI Pro

## Architecture

This project deploys as **3 separate Railway services**:

| Service | Directory | Port | Description |
|---------|-----------|------|-------------|
| Backend API | `backend/` | Dynamic (`$PORT`) | FastAPI + Python 3.11 |
| Frontend | `frontend/` | Dynamic (`$PORT`) | React + Vite + Nginx |
| Streamlit Dashboard | Root (`/`) | Dynamic (`$PORT`) | Standalone demo dashboard |

## Quick Deploy (Streamlit Only)

The fastest way to get a live URL — deploys the self-contained Streamlit dashboard:

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click **"New Project"** → **"Deploy from GitHub Repo"**
3. Select `AITraderIQ` repository
4. Railway auto-detects `railway.toml` at root → deploys the Streamlit app
5. Click **"Generate Domain"** in Settings to get a public URL

## Full Stack Deploy (Backend + Frontend)

### Step 1: Create a New Railway Project

1. Go to [railway.app](https://railway.app) → **New Project** → **Empty Project**

### Step 2: Deploy the Backend

1. Click **"New Service"** → **"GitHub Repo"** → select `AITraderIQ`
2. Go to **Settings** → set **Root Directory** to `backend`
3. Railway auto-detects `backend/railway.toml`
4. Add environment variables in **Variables** tab:
   ```
   DEMO_MODE=true
   GROQ_API_KEY=<your-key>          # optional
   JWT_SECRET_KEY=<random-string>    # use a strong random value
   CORS_ORIGINS=https://<frontend-domain>.up.railway.app
   ```
5. Click **"Generate Domain"** to get the backend URL

### Step 3: Deploy the Frontend

1. Click **"New Service"** → **"GitHub Repo"** → select `AITraderIQ`
2. Go to **Settings** → set **Root Directory** to `frontend`
3. Railway auto-detects `frontend/railway.toml`
4. Add environment variables:
   ```
   BACKEND_URL=https://<backend-domain>.up.railway.app
   VITE_API_BASE_URL=https://<backend-domain>.up.railway.app
   ```
5. Click **"Generate Domain"** to get the frontend URL

### Step 4: Update Backend CORS

Go back to the backend service and update:
```
CORS_ORIGINS=https://<frontend-domain>.up.railway.app
```

## Environment Variables Reference

### Backend
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | Auto | 8000 | Set by Railway automatically |
| `DEMO_MODE` | No | `true` | Enable simulated data |
| `GROQ_API_KEY` | No | - | Groq API key for AI features |
| `JWT_SECRET_KEY` | Yes | - | Auth token signing key |
| `CORS_ORIGINS` | Yes | - | Frontend URL(s), comma-separated |
| `DATABASE_URL` | No | SQLite | Database connection string |

### Frontend
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | Auto | 80 | Set by Railway automatically |
| `BACKEND_URL` | Yes | - | Backend service URL for nginx proxy |
| `VITE_API_BASE_URL` | No | `""` | API URL baked into frontend build |

## Cost

Railway offers a **free trial** ($5 credit) and a **Hobby plan** at $5/month with 8 GB RAM and 8 vCPU. The Streamlit-only deploy uses minimal resources (~256 MB RAM).
