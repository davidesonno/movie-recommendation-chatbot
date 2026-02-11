from typing import Optional, List

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class AgentRunRequest(BaseModel):
    user_id: Optional[int] = None
    history: List[dict] = Field(default_factory=list)


class AgentRunResponse(BaseModel):
    assistant_message: str


def get_agent_handler(request: Request):
	handler = getattr(request.app.state, "agent_handler", None)
	if handler is None:
		raise HTTPException(status_code=500, detail="Agent handler not initialized")
	return handler


@router.post("/agent", response_model=AgentRunResponse)
def run_agent(req: AgentRunRequest, request: Request):
    handler = get_agent_handler(request)
    response = handler.process_message(
        req.user_id,
        req.history,
    )
    return AgentRunResponse(assistant_message=response)
