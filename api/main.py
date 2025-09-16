from fastapi import FastAPI
from .worker import run_operate_task
from .models import TestRequest, JobResponse

app = FastAPI()

@app.post("/api/tests", response_model=JobResponse)
def create_test(request: TestRequest):
    """Queues a new test to be run by the worker."""
    task = run_operate_task.delay(request.objective)
    return {"job_id": task.id, "status": "queued"}

@app.get("/")
def read_root():
    return {"message": "Self-Operating Computer API is running."}
