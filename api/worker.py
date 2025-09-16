from celery import Celery
import time

# Create a Celery instance that connects to the same Redis broker as the FastAPI app
celery = Celery(
    __name__,
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

@celery.task
def run_operate_task(objective: str):
    """A placeholder task that simulates running a test."""
    print(f"[Worker] Received objective: {objective}")
    # Simulate a long-running task
    time.sleep(10)
    print(f"[Worker] Finished processing objective: {objective}")
    return {"status": "completed", "result": f"Successfully completed: {objective}"}
