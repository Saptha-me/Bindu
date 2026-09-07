from fastapi import APIRouter
from pydantic import BaseModel
from .orchestrator import InterviewOrchestrator

router = APIRouter(prefix="/agents/interview", tags=["AI Interview Agent"])


class InterviewRequest(BaseModel):
    resume: str
    role: str
    rounds: int = 5


@router.post("/start")
def start_interview(req: InterviewRequest):
    orchestrator = InterviewOrchestrator(
        resume=req.resume,
        role=req.role,
        rounds=req.rounds
    )

    result = orchestrator.run()
    return {"result": result}