web: python -m uvicorn api.main:app --reload --timeout-graceful-shutdown 2
worker: celery -A api.worker worker --loglevel=info --logfile=celery.log
