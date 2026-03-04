from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db, get_current_user, role_required
from app.crud import conversation as conversation_crud
from app.models.user import User, UserRole
from app.schemas.conversation import (
    ChatQueryRequest,
    ChatQueryResponse,
    ConversationSessionRead,
    ConversationSessionDetail,
)
from app.services.intent_detector import IntentDetector
from app.services.query_planner import QueryPlanner
from app.services.conversation_orchestrator import ConversationOrchestrator

router = APIRouter(prefix="/chat", tags=["chat"])

AllowedRoleDep = role_required(
    UserRole.Admin, UserRole.Recruiter, UserRole.HiringManager
)


@router.post("/query", response_model=ChatQueryResponse)
async def process_chat_query(
    request: ChatQueryRequest,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: User = Depends(AllowedRoleDep),
):
    """Process conversational query and return AI response."""
    session_id = request.session_id

    if not session_id:
        session = await conversation_crud.create_session(
            db, current_user.id, title=request.query[:50]
        )
        session_id = session.id
    else:
        session = await conversation_crud.get_session(db, session_id, current_user.id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

    await conversation_crud.create_message(
        db=db,
        session_id=session_id,
        role="user",
        content=request.query,
    )

    detector = IntentDetector()
    intent_result = detector.detect(request.query, session.context or {})

    planner = QueryPlanner()
    plan = planner.plan(intent_result["intent"], intent_result["entities"])

    orchestrator = ConversationOrchestrator(db)
    collected_data = await orchestrator.execute_plan(plan)

    if "message" in collected_data:
        response_data = collected_data
    else:
        response_data = await orchestrator.compose_response(collected_data, request.query)

    response_data["intent"] = intent_result["intent"]
    response_data["entities"] = intent_result.get("entities", {})

    await conversation_crud.create_message(
        db=db,
        session_id=session_id,
        role="assistant",
        content=response_data["message"],
        intent=intent_result["intent"],
        entities=intent_result.get("entities"),
        confidence=response_data.get("confidence"),
        sources=response_data.get("sources"),
    )

    new_context = {
        "last_intent": intent_result["intent"],
        "last_entity_type": intent_result["entities"].get("entity_type"),
        "last_entity_id": intent_result["entities"].get("entity_id"),
    }
    await conversation_crud.update_session_context(db, session_id, new_context)

    return ChatQueryResponse(
        session_id=session_id,
        message=response_data["message"],
        bullets=response_data.get("bullets", []),
        confidence=response_data.get("confidence", 0.0),
        sources=response_data.get("sources", []),
        intent=intent_result["intent"],
        entities=intent_result.get("entities", {}),
    )


@router.get("/sessions", response_model=list[ConversationSessionRead])
async def list_sessions(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: User = Depends(get_current_user),
):
    """List all conversation sessions for current user."""
    sessions = await conversation_crud.list_user_sessions(db, current_user.id)
    return [
        ConversationSessionRead(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            context=session.context,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=message_count,
        )
        for session, message_count in sessions
    ]


@router.get("/session/{session_id}", response_model=ConversationSessionDetail)
async def get_session_detail(
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: User = Depends(get_current_user),
):
    """Get detailed conversation session with all messages."""
    session = await conversation_crud.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return ConversationSessionDetail.model_validate(session)


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: User = Depends(get_current_user),
):
    """Delete a conversation session."""
    deleted = await conversation_crud.delete_session(db, session_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted successfully"}
