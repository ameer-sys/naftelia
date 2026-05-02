# ✅ Deployment Setup Complete!

Your Naftelia app is now ready for deployment to Railway + Supabase. Here's what was configured:

## 📦 What Changed

### Backend Updates
- ✅ `requirements.txt` - Added `psycopg2-binary` (PostgreSQL driver) and `gunicorn` (production server)
- ✅ `services/db.py` - Now supports BOTH SQLite (development) and PostgreSQL (production)
- ✅ `app.py` - Updated to properly serve static files in production
- ✅ `backend/.env.example` - Added PostgreSQL connection string example

### New Files
- ✅ `Procfile` - Railway configuration (tells it how to run your app)
- ✅ `build.sh` / `build.bat` - Build scripts for local testing
- ✅ `DEPLOYMENT.md` - Complete step-by-step deployment guide
- ✅ `SETUP_SUMMARY.md` - This file!

## 🚀 Next Steps (TL;DR)

### 1. Create Supabase Database (5 min)
```
1. Go to https://supabase.com → Create project
2. Go to Settings → Database → Copy connection string
3. Go to SQL Editor → Run the SQL from DEPLOYMENT.md
```

### 2. Push to GitHub
```bash
git add .
git commit -m "Add Railway + Supabase deployment setup"
git push
```

### 3. Deploy on Railway (3 min)
```
1. Go to https://railway.app → New Project → Deploy from GitHub
2. Select your repo
3. Add environment variables (see DEPLOYMENT.md)
4. Done! Your app is live 🎉
```

## 🔍 How Database Selection Works

Your app now **automatically picks** the right database:

- **Local development** (FLASK_ENV=development): Uses SQLite ✅ No setup needed
- **Production** (FLASK_ENV=production): Uses PostgreSQL ✅ Via Supabase

No code changes needed - just set environment variables!

## 📝 Key Files to Know

| File | Purpose |
|------|---------|
| [Procfile](./Procfile) | Tells Railway how to run your app |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Complete deployment guide (READ THIS!) |
| [backend/services/db.py](./backend/services/db.py) | Database logic (SQLite + PostgreSQL) |
| [backend/requirements.txt](./backend/requirements.txt) | Python dependencies |

## ⚠️ Important Notes

1. **Don't commit `.env`** - It has your secrets!
   - The file is already in `.gitignore`
   - Only commit `.env.example`

2. **Environment variables** are set in Railway dashboard, not `.env`
   - Each environment has its own variables

3. **Database migration:**
   - Old SQLite data stays local
   - Production uses fresh PostgreSQL database
   - Set up both environments separately

## 💡 Pro Tips

- Test locally with PostgreSQL before deploying:
  ```bash
  export FLASK_ENV=production
  export DATABASE_URL="postgresql://..."
  cd backend && python app.py
  ```

- Watch Railway logs while deploying
- Use Supabase dashboard to check data and run queries
- Health check: `GET /api/health` returns `{"ok": true, ...}`

## 🆘 Stuck?

1. **Read:** [DEPLOYMENT.md](./DEPLOYMENT.md) has detailed troubleshooting
2. **Check:** Railway logs (Dashboard → Deployments)
3. **Test locally:** `python backend/app.py` with right env vars
4. **Debug:** Use browser DevTools to check API calls

## 📞 Support Links

- [Railway Docs](https://docs.railway.app)
- [Supabase Docs](https://supabase.com/docs)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [Flask Docs](https://flask.palletsprojects.com/)

---

**Ready to deploy?** Start with Step 1 in [DEPLOYMENT.md](./DEPLOYMENT.md)!
