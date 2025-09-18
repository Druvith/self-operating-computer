from celery import Celery
import sys
import os
import logging

# Add the project root to the Python path to allow imports from 'operate'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('worker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

from operate.operate import run_automated_test
from operate.exceptions import *

celery = Celery(
    __name__,
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

@celery.task
def run_operate_task(objective: str):
    """
    The real Celery task that runs the self-operating computer logic.
    """
    logger.info(f"[Worker] Received objective: {objective}")
    try:
        summary = run_automated_test(model="gemini-2.5-flash", objective=objective)
        logger.info(f"[Worker] Objective '{objective}' completed successfully.")
        return {"status": "SUCCESS", "result": summary}
    except Exception as e:
        logger.error(f"[Worker] Objective '{objective}' failed with error: {e}")
        # Return a serializable error message
        return {"status": "FAILURE", "result": str(e)}
