# Naftelia - Railway + Supabase Deployment Guide

## 🚀 Quick Start (3 Steps)

### Step 1: Set up Supabase Database (5 min)

1. **Create Supabase account & project:**
   - Go to [supabase.com](https://supabase.com)
   - Click "New Project"
   - Choose organization, set name, password, region
   - Wait 2-3 minutes for setup

2. **Get your database credentials:**
   - In Supabase dashboard → **Settings** → **Database**
   - Copy the **Connection string** (PostgreSQL format)
   - Looks like: `postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres`
   - Save this for later! ↴

3. **Initialize database schema:**
   - Go to **SQL Editor** → **New query**
   - Run this query:

```sql
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  auth0_sub TEXT NOT NULL UNIQUE,
  email TEXT,
  full_name TEXT,
  home_port TEXT,
  preferred_units TEXT DEFAULT 'metric',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vessels (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL,
  name TEXT,
  vessel_type TEXT NOT NULL,
  length_m REAL,
  draft_m REAL,
  cruising_speed_kn REAL,
  safety_margin TEXT DEFAULT 'balanced',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS voyage_plans (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL,
  vessel_id INTEGER,
  origin_label TEXT,
  origin_lat REAL NOT NULL,
  origin_lon REAL NOT NULL,
  destination_label TEXT,
  destination_lat REAL NOT NULL,
  destination_lon REAL NOT NULL,
  departure_time TEXT,
  status TEXT DEFAULT 'planned',
  noaa_snapshot_json TEXT NOT NULL,
  gemini_plan_json TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (vessel_id) REFERENCES vessels(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS route_waypoints (
  id SERIAL PRIMARY KEY,
  voyage_id INTEGER NOT NULL,
  sequence INTEGER NOT NULL,
  label TEXT,
  latitude REAL NOT NULL,
  longitude REAL NOT NULL,
  instruction TEXT,
  caution_level TEXT DEFAULT 'normal',
  FOREIGN KEY (voyage_id) REFERENCES voyage_plans(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS offline_packs (
  id SERIAL PRIMARY KEY,
  voyage_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  pack_json TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (voyage_id) REFERENCES voyage_plans(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

---

### Step 2: Deploy to Railway (3 min)

1. **Push code to GitHub:**
   ```bash
   git add .
   git commit -m "Add Railway deployment config"
   git push origin main
   ```

2. **Create Railway project:**
   - Go to [railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Authorize Railway and select your repository
   - Click "Deploy"

3. **Set environment variables in Railway:**
   - Go to your project → **Variables** tab
   - Add these variables:

   ```env
   FLASK_ENV=production
   DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres
   SECRET_KEY=[run: python -c "import secrets; print(secrets.token_hex(32))"]
   CORS_ORIGINS=https://your-app-name.up.railway.app
   AUTH0_DOMAIN=your-tenant.us.auth0.com
   AUTH0_CLIENT_ID=your-spa-client-id
   AUTH0_AUDIENCE=https://api.naftelia.local
   GEMINI_API_KEY=your-gemini-api-key
   GEMINI_MODEL=gemini-2.5-flash
   ```

   - Replace `your-app-name` with your Railway app name (shown in dashboard)
   - Keep other values from your current `.env` file

4. **Deploy:**
   - Railway will automatically detect `Procfile` and build
   - Once deployed, you'll see a public URL like: `https://naftelia-prod.up.railway.app`
   - Your app is live! 🎉

---

### Step 3: Test Your App

- **Health check:** Visit `https://your-app-url.up.railway.app/api/health`
- **App:** Visit `https://your-app-url.up.railway.app`
- **Check logs:** Railway dashboard → Deployments tab

---

## 📊 Architecture

```
Frontend (Vite)
    ↓
Flask Backend
    ↓
PostgreSQL (Supabase)
```

- **Frontend:** Built by Vite, served by Flask
- **Backend:** Python Flask running on Railway
- **Database:** PostgreSQL on Supabase

---

## 🔄 Updating Your App

1. Make code changes locally
2. Push to GitHub:
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```
3. Railway auto-redeploys (watch logs in dashboard)

---

## 🚨 Troubleshooting

### Build fails
- **Check logs:** Railway dashboard → Deployments → build logs
- **Verify Procfile exists** in repo root
- **Verify `gunicorn` in `requirements.txt`**

### Database connection error
- **Verify DATABASE_URL:** Copy exact connection string from Supabase
- **Check credentials:** Make sure password has special characters properly escaped
- **Test locally:**
  ```bash
  export FLASK_ENV=production
  export DATABASE_URL="your-connection-string"
  cd backend && python -c "from services.db import init_db; init_db()"
  ```

### Frontend can't reach API
- **Verify CORS_ORIGINS:** Should match your Railway domain exactly
- **Check browser console:** Look for CORS errors
- **Test API endpoint:** `curl https://your-app-url.up.railway.app/api/health`

### Images/styles not loading
- **Verify frontend build:** Check if `frontend/dist/` folder was created
- **Check static file serving:** Make sure app.py serves static files correctly

---

## 📝 Environment Variables Reference

| Variable | Development | Production |
|----------|-------------|------------|
| `FLASK_ENV` | `development` | `production` |
| `DATABASE_URL` | Not set (uses SQLite) | `postgresql://...` from Supabase |
| `SECRET_KEY` | Dev key (not secure) | Random generated key |
| `CORS_ORIGINS` | `http://127.0.0.1:5173` | Your Railway URL |
| `HOST` | `127.0.0.1` | Not used (gunicorn handles) |
| `PORT` | `5000` | Set by Railway |

---

## 💡 Tips

- **Database migrations:** Supabase SQL Editor lets you run migrations anytime
- **Monitor performance:** Supabase dashboard shows query stats
- **Scaling:** Upgrade Supabase plan for more connections/storage
- **Backups:** Supabase auto-backs up daily
- **Custom domain:** Railway supports custom domains (pro feature)

---

## 🔗 Quick Links

- [Railway Dashboard](https://railway.app/dashboard)
- [Supabase Dashboard](https://app.supabase.com)
- [Railway Docs](https://docs.railway.app)
- [Supabase Docs](https://supabase.com/docs)

---

**Deployed by:** Railway + Supabase  
**Last updated:** May 2, 2026
