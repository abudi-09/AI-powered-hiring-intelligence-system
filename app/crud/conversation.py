from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import ConversationSession, ConversationMessage


async def create_session(
    db: AsyncSession, user_id: uuid.UUID, title: str | None = None
) -> ConversationSession:
    """Create a new conversation session."""
    session = ConversationSession(user_id=user_id, title=title, context={})
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(
    db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID
) -> ConversationSession | None:
    """Get conversation session by ID."""
    result = await db.execute(
        select(ConversationSession)
        .options(selectinload(ConversationSession.messages))
        .where(
            ConversationSession.id == session_id,
            ConversationSession.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_user_sessions(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 50
) -> Sequence[ConversationSession]:
    """List all sessions for a user."""
    result = await db.execute(
        select(ConversationSession)
        .where(ConversationSession.user_id == user_id)
        .order_by(ConversationSession.updated_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def update_session_context(
    db: AsyncSession, session_id: uuid.UUID, context: dict
) -> None:
    """Update session context."""
    result = await db.execute(
        select(ConversationSession).where(ConversationSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session:
        session.context = context
        await db.commit()


async def delete_session(
    db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Delete a conversation session."""
    result = await db.execute(
        delete(ConversationSession).where(
            ConversationSession.id == session_id,
            ConversationSession.user_id == user_id,
        )
    )
    await db.commit()
    return result.rowcount > 0


async def create_message(
    db: AsyncSession,
    session_id: uuid.UUID,
    role: str,
    content: str,
    intent: str | None = None,
    entities: dict | None = None,
    confidence: float | None = None,
    sources: list[str] | None = None,
) -> ConversationMessage:
    """Create a new conversation message."""
    message = ConversationMessage(
        session_id=session_id,
        role=role,
        content=content,
        intent=intent,
        entities=entities,
        confidence=confidence,
        sources=sources,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def get_session_messages(
    db: AsyncSession, session_id: uuid.UUID
) -> Sequence[ConversationMessage]:
    """Get all messages for a session."""
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session_id)
        .order_by(ConversationMessage.created_at.asc())
    )
    return result.scalars().all()
