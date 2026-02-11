# src/api/routers/chat.py

from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
import requests
from requests.exceptions import JSONDecodeError
from src.api.routers.auth import get_current_user
from src.services.rate_limiter import check_user_rate_limit

router = APIRouter()

# ----------------------------
# Request / Response Models
# ----------------------------

class ChatRequest(BaseModel):
    conversation_id: Optional[int] = None
    content: str
    role: Optional[str] = "user"

class ChatResponse(BaseModel):
    conversation_id: int
    assistant_message: str

class MessageResponse(BaseModel):
    id: int
    user_id: int
    conversation_id: int
    role: str
    content: str
    created_at: str

class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str]
    created_at: str
    last_message_at: Optional[str]

class RenameConversationRequest(BaseModel):
    title: str

class RenameConversationResponse(BaseModel):
    conversation_id: int
    title: str

class DeleteConversationRequest(BaseModel):
    pass  # No fields needed, user_id comes from token

class DeleteConversationResponse(BaseModel):
    conversation_id: int
    detail: str

# ----------------------------
# Helpers
# ----------------------------

def get_db(request: Request):
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return db

# ----------------------------
# Routes
# ----------------------------

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request, user_id: int = Depends(get_current_user)):
    """
    Handle sending a message. Creates a new conversation if conversation_id is None.
    Returns the assistant's placeholder response.
    """
    # Check rate limit
    check_user_rate_limit(request, user_id)

    CONVERSATION_MAX_LENGTH = 10

    db = get_db(request)

    try:
        conversation_id = db.insert_message(
            user_id=user_id,
            conversation_id=req.conversation_id,
            role=req.role,
            content=req.content
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    conversation_history = db.list_conversation_messages(user_id=user_id, conversation_id=conversation_id, limit=CONVERSATION_MAX_LENGTH)
    filtered_history = []
    for msg in conversation_history:
        if isinstance(msg, dict):
            role = msg.get("role")
            content = msg.get("content")
        else:
            role = getattr(msg, "role", None)
            content = getattr(msg, "content", None)
        if role is not None and content is not None:
            filtered_history.append({"role": role, "content": content})

    agent_payload = {
        "user_id": user_id,
        "history": filtered_history
    }
    agent_http_response = requests.post(
        request.app.state.config.get("agent").get("ENDPOINT"), 
        json=agent_payload
    )

    if not agent_http_response.ok:
        raise HTTPException(status_code=502, detail="Agent service error")

    try:
        agent_response = agent_http_response.json().get("assistant_message", "[No response]")
    except JSONDecodeError:
        raise HTTPException(status_code=502, detail="Agent returned non-JSON response")

    db.insert_message(
        user_id=user_id,
        conversation_id=conversation_id,
        role="assistant",
        content=agent_response
    )

    return ChatResponse(conversation_id=conversation_id, assistant_message=agent_response)

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
def list_conversation_messages(conversation_id: int, request: Request, limit: int = 10, user_id: int = Depends(get_current_user)):
    """
    List messages of a specific conversation, most recent first.
    User is authenticated via JWT token.
    """
    # Check rate limit
    check_user_rate_limit(request, user_id)
    
    db = get_db(request)
    messages = db.list_conversation_messages(user_id=user_id, conversation_id=conversation_id, limit=limit)
    return messages

@router.get("/conversations", response_model=List[ConversationResponse])
def list_conversations(request: Request, user_id: int = Depends(get_current_user)):
    """
    List all conversations for the user.
    User is authenticated via JWT token.
    """
    # Check rate limit
    check_user_rate_limit(request, user_id)
    
    db = get_db(request)
    return db.list_conversations(user_id=user_id)

@router.patch("/conversations/{conversation_id}", response_model=RenameConversationResponse)
def rename_conversation(conversation_id: int, request: Request, body: RenameConversationRequest, user_id: int = Depends(get_current_user)):
    """
    Update conversation title.
    User is authenticated via JWT token.
    """
    # Check rate limit
    check_user_rate_limit(request, user_id)
    
    db = get_db(request)
    if not body.title:
        raise HTTPException(status_code=400, detail="Title is required")
    db.update_conversation_title(user_id=user_id, conversation_id=conversation_id, title=body.title)
    return {"conversation_id": conversation_id, "title": body.title}

@router.delete("/conversations/{conversation_id}", response_model=DeleteConversationResponse)
def delete_conversation(conversation_id: int, request: Request, user_id: int = Depends(get_current_user)):
    """
    Delete a conversation and all its messages.
    User is authenticated via JWT token.
    """
    # Check rate limit
    check_user_rate_limit(request, user_id)
    
    db = get_db(request)
    db.delete_conversation(user_id=user_id, conversation_id=conversation_id)
    return {"conversation_id": conversation_id, "detail": "Conversation deleted successfully"}
