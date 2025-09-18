from fastapi import FastAPI
from celery.result import AsyncResult
from .worker import run_operate_task, celery
from .models import TestRequest, JobResponse, TestResult

app = FastAPI()

@app.post("/api/tests", response_model=JobResponse)
def create_test(request: TestRequest):
    """Queues a new test to be run by the worker."""
    task = run_operate_task.delay(request.objective)
    return {"job_id": task.id, "status": "queued"}

@app.get("/api/tests/{job_id}", response_model=TestResult)
def get_test_result(job_id: str):
    """Retrieves the status and result of a submitted test."""
    task_result = AsyncResult(job_id, app=celery)
    
    result_data = task_result.result or None
    
    # Ensure the result is JSON serializable
    if result_data and not isinstance(result_data, (dict, list, str, int, float, bool)):
        result_data = str(result_data) # Convert non-serializable types to string

    return {
        "job_id": job_id,
        "status": task_result.status,
        "result": result_data
    }

@app.get("/")
def read_root():
    return {"message": "Self-Operating Computer API is running."}