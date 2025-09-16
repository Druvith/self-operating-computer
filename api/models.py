from pydantic import BaseModel

class TestRequest(BaseModel):
    objective: str

class JobResponse(BaseModel):
    job_id: str
    status: str
