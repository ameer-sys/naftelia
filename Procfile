web: cd backend && gunicorn -w 4 -b 0.0.0.0:$PORT app:app
release: cd backend && python -c "from services.db import init_db; init_db()"
