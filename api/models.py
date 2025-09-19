from pydantic import BaseModel
from typing import Any

class TestRequest(BaseModel):
    objective: str

class JobResponse(BaseModel):
    job_id: str
    status: str

class TestResult(BaseModel):
    job_id: str
    status: str
    result: Any = None # Can be a string (summary/error) or a dict