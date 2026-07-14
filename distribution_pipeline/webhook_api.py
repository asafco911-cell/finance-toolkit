import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "security"))

from fastapi import FastAPI, BackgroundTasks, Depends
from pydantic import BaseModel

from pipeline import run_distribution
from auth import verify_api_key

app = FastAPI()


class DistributionRequest(BaseModel):
    question: str
    to_number: str | None = None


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/distribute", dependencies=[Depends(verify_api_key)])
def distribute(request: DistributionRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        run_distribution,
        request.question,
        request.to_number
    )

    return {
        "status": "accepted",
        "message": "Analysis started. The result will be sent via WhatsApp."
    }