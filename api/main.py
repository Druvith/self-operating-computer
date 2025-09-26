from fastapi import FastAPI
import threading
import queue
import uuid
import sys
import os
from contextlib import asynccontextmanager
from .models import TestRequest, JobResponse, TestResult

# Add the project root to the Python path to allow imports from 'operate'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from operate.operate import run_automated_test

# In-memory storage for job queue and results
job_queue = queue.Queue()
job_results = {}
shutdown_event = threading.Event()

def worker():
    """The worker thread that processes jobs from the queue sequentially."""
    while not shutdown_event.is_set():
        try:
            # Wait for a job with a timeout to allow checking the shutdown event
            job_id, objective = job_queue.get(timeout=1)
            print(f"[Worker] Picked up job {job_id}: {objective}")
            job_results[job_id] = {"status": "RUNNING", "result": None}
            try:
                summary = run_automated_test(model="gemini-flash-latest", objective=objective)
                job_results[job_id] = {"status": "SUCCESS", "result": summary}
                print(f"[Worker] Job {job_id} completed successfully.")
            except Exception as e:
                error_message = str(e)
                job_results[job_id] = {"status": "FAILURE", "result": error_message}
                print(f"[Worker] Job {job_id} failed: {error_message}")
            finally:
                job_queue.task_done()
        except queue.Empty:
            # This is expected when the queue is empty, just continue the loop
            continue

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the startup and shutdown of the application."""
    # Start the worker thread
    worker_thread = threading.Thread(target=worker)
    worker_thread.start()
    print("Worker thread started.")
    yield
    # Cleanup: Signal the worker to shut down and wait for it
    print("Shutting down worker thread...")
    shutdown_event.set()
    worker_thread.join() # Wait for the worker thread to finish
    print("Worker thread shut down gracefully.")

app = FastAPI(lifespan=lifespan)

@app.post("/api/tests", response_model=JobResponse)
def create_test(request: TestRequest):
    """Queues a new test to be run by the worker."""
    job_id = str(uuid.uuid4())
    job_queue.put((job_id, request.objective))
    job_results[job_id] = {"status": "QUEUED", "result": None}
    return {"job_id": job_id, "status": "queued"}

@app.get("/api/tests/{job_id}", response_model=TestResult)
def get_test_result(job_id: str):
    """Retrieves the status and result of a submitted test."""
    result = job_results.get(job_id, {})
    status = result.get("status", "NOT_FOUND")
    
    if status == "NOT_FOUND":
        return {"job_id": job_id, "status": "NOT_FOUND", "result": "No job with that ID was found."}
        
    return {
        "job_id": job_id,
        "status": status,
        "result": result.get("result")
    }

@app.get("/")
def read_root():
    return {"message": "Self-Operating Computer API is running."}
