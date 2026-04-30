# Naftelia

Naftelia is a web app for sailors, fishers, yacht captains, and vessel operators who need affordable voyage intelligence before leaving dock.

The app combines:

- Auth0 authentication
- NOAA weather and marine observations
- Gemini route reasoning
- Leaflet maps
- SQLite persistence
- 24-hour offline voyage packs

Pro subscriptions are marked as "coming soon" and payment is intentionally not implemented yet.

## Project Structure

```text
frontend/
  index.html
  src/
    app.js
    api.js
    styles.css
  package.json
  vite.config.js

backend/
  app.py
  services/
    auth0.py
    db.py
    gemini.py
    noaa.py
  instance/
  requirements.txt
  .env.example
```

## Core Functionalities

- Real Auth0 login and signup redirect flow.
- User profile storage in Naftelia after Auth0 authentication.
- Vessel profile storage.
- NOAA/NWS point forecast lookup for origin and destination.
- NOAA CO-OPS station observations for wind, water temperature, air temperature, pressure, visibility, and tide predictions.
- Gemini voyage planning based on the NOAA snapshot and user-entered origin/destination.
- Saved voyage plans with route waypoints.
- Offline pack generation, valid for 24 hours, stored locally in the browser and persisted in SQLite.
- Professional responsive UI across landing, auth, dashboard, planner, route, offline, settings, developers, privacy, and terms pages.

## Run Frontend

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Run Backend

Create your environment file:

```powershell
Copy-Item backend\.env.example backend\.env
```

Install Python dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Start the backend:

```powershell
cd backend
..\.venv\Scripts\python.exe app.py
```

## Required Environment Variables

Set these in `backend/.env`:

```text
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_CLIENT_ID=your-spa-client-id
AUTH0_AUDIENCE=https://api.naftelia.local
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
```

For local development only, you may temporarily set:

```text
NAFTELIA_DEMO_AUTH=true
```

For a real demo with judges, keep:

```text
NAFTELIA_DEMO_AUTH=false
```

## Auth0 Setup

Create an Auth0 Single Page Application:

- Allowed Callback URLs: `http://127.0.0.1:5173`
- Allowed Logout URLs: `http://127.0.0.1:5173`
- Allowed Web Origins: `http://127.0.0.1:5173`

Create an Auth0 API:

- Identifier should match `AUTH0_AUDIENCE`.
- The frontend requests access tokens for this audience.
- The backend validates JWTs using the Auth0 JWKS endpoint.

## NOAA Notes

Naftelia uses official NOAA endpoints:

- NOAA/NWS point forecast: `https://api.weather.gov/points/{lat},{lon}`
- NOAA/NWS alerts: `https://api.weather.gov/alerts/active`
- NOAA CO-OPS Data API: `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter`

NOAA/NWS point forecasts mainly cover the United States and territories. For Canada or other regions, the backend returns a clear unavailable message while still allowing Gemini fallback planning. A future production release should add Environment Canada, Copernicus Marine, or Open-Meteo as regional providers.

## Important API Endpoints

- `GET /api/health`
- `GET /api/config`
- `GET /api/me`
- `PUT /api/me`
- `GET /api/vessels`
- `POST /api/vessels`
- `POST /api/noaa/conditions`
- `POST /api/voyages/plan`
- `GET /api/voyages`
- `GET /api/voyages/<id>`
- `POST /api/voyages/<id>/offline-pack`

## Safety Positioning

Naftelia is decision support. It must not claim to guarantee safe passage. Captains should always check official marine warnings, local regulations, vessel readiness, and use their own judgment before departure.
