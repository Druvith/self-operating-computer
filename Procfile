web: python -m uvicorn api.main:app --reload
worker: celery -A api.worker worker --loglevel=info
