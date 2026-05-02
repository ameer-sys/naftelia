# 🚀 Railway + Supabase Deployment Checklist

Use this checklist to ensure your deployment goes smoothly.

## Phase 1: Local Testing (Optional but Recommended)

- [ ] Pull latest code: `git pull`
- [ ] Test backend locally: `cd backend && python app.py`
- [ ] Frontend loads at: `http://localhost:5000`
- [ ] API health check works: `GET http://localhost:5000/api/health`
- [ ] Can create vessels and voyages without errors
- [ ] No Python import errors in terminal

## Phase 2: Supabase Setup (5 minutes)

- [ ] Create Supabase account at https://supabase.com
- [ ] Create new project
- [ ] Wait for database to initialize (2-3 min)
- [ ] Copy connection string from Settings → Database
- [ ] Go to SQL Editor
- [ ] Create new query and paste SQL schema from DEPLOYMENT.md
- [ ] Run query successfully
- [ ] Tables appear in Table Editor: users, vessels, voyage_plans, route_waypoints, offline_packs

## Phase 3: GitHub Setup

- [ ] All code committed locally: `git status` shows clean
- [ ] `.env` is in `.gitignore` (check `.gitignore` file)
- [ ] `.env.example` is in repo (don't commit `.env` with real secrets!)
- [ ] Push to GitHub: `git push origin main`
- [ ] Verify files on GitHub:
  - `Procfile` exists at root
  - `backend/requirements.txt` has `psycopg2-binary` and `gunicorn`
  - `backend/services/db.py` supports PostgreSQL
  - `DEPLOYMENT.md` exists

## Phase 4: Railway Deployment

- [ ] Create Railway account at https://railway.app
- [ ] New Project → Deploy from GitHub repo
- [ ] Select your repository
- [ ] Click Deploy (Railway starts building)
- [ ] Wait for build to complete (watch logs)
- [ ] Go to Variables tab and add:
  - [ ] `FLASK_ENV` = `production`
  - [ ] `DATABASE_URL` = Your Supabase connection string
  - [ ] `SECRET_KEY` = Generated random key (use `python -c "import secrets; print(secrets.token_hex(32))"`)
  - [ ] `CORS_ORIGINS` = Your Railway domain (e.g., `https://naftelia-prod.up.railway.app`)
  - [ ] `AUTH0_DOMAIN` = Your Auth0 domain
  - [ ] `AUTH0_CLIENT_ID` = Your Auth0 client ID
  - [ ] `AUTH0_AUDIENCE` = Your Auth0 audience
  - [ ] `GEMINI_API_KEY` = Your Gemini API key
  - [ ] `GEMINI_MODEL` = `gemini-2.5-flash`

## Phase 5: Verification

- [ ] Railway shows deployment as "Running"
- [ ] Check logs for errors (Deployments tab)
- [ ] App URL is provided: `https://your-app.up.railway.app`
- [ ] Health check passes: `curl https://your-app.up.railway.app/api/health`
- [ ] Frontend loads at: `https://your-app.up.railway.app`
- [ ] API calls work: Try creating a vessel or voyage
- [ ] Database queries work: Data persists after refresh

## Phase 6: Final Checks

- [ ] Custom domain configured (optional, if needed)
- [ ] Email notifications enabled (optional, for deployments)
- [ ] Database backups enabled in Supabase (check Settings)
- [ ] Monitor tab shows healthy app (CPU, memory, etc.)
- [ ] README updated with deployment info

## Troubleshooting Checklist

If something fails, check:

### Build Failed
- [ ] Check Railway build logs for errors
- [ ] Verify `Procfile` exists in repo root
- [ ] Verify `gunicorn` in `requirements.txt`
- [ ] Verify no syntax errors in Python files

### App Running but Errors in Logs
- [ ] Check environment variables are set correctly
- [ ] Verify `DATABASE_URL` format: `postgresql://user:pass@host:5432/db`
- [ ] Try local test with same `DATABASE_URL`

### Database Connection Error
- [ ] Verify `DATABASE_URL` in Railway matches Supabase exactly
- [ ] Check Supabase is running (go to dashboard)
- [ ] Try connecting to Supabase from local machine first
- [ ] Look for credential escaping issues (special chars in password)

### Frontend Can't Reach API
- [ ] Check `CORS_ORIGINS` matches Railway domain exactly
- [ ] Test API endpoint directly: `curl https://your-app.up.railway.app/api/health`
- [ ] Check browser console for CORS errors
- [ ] Verify API base URL in frontend code (if hardcoded)

### Static Files Not Loading
- [ ] Verify frontend build succeeded (check logs)
- [ ] Verify `frontend/dist/` folder exists
- [ ] Check app.py serves static files correctly
- [ ] Try clearing browser cache (Ctrl+Shift+Delete)

## After Deployment

- [ ] Set up monitoring alerts (optional)
- [ ] Document your production domain
- [ ] Share deployment URL with team
- [ ] Keep `.env` file local (never commit secrets)
- [ ] Update README with production URL
- [ ] Test all features in production

## Rollback Plan

If something breaks in production:

1. **Revert code:** `git revert HEAD && git push`
2. **Railway redeploys automatically** (or manually trigger redeploy)
3. **Restore database:** Supabase has automatic backups

## Support Resources

- Railway Logs: Dashboard → Deployments → Click build
- Supabase Dashboard: https://app.supabase.com
- Error Messages: Read carefully, they usually point to the issue
- DEPLOYMENT.md: Full guide with examples
- GitHub Issues: Search for similar problems

---

**Status: ✅ Ready to Deploy!**

Start with Phase 1 (optional local testing) or Phase 2 (Supabase setup).

Questions? See DEPLOYMENT.md for detailed step-by-step instructions.
