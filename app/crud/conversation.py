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
) -> Sequence[tuple[ConversationSession, int]]:
    """List all sessions for a user with message counts."""
    result = await db.execute(
        select(
            ConversationSession,
            func.count(ConversationMessage.id).label("message_count"),
        )
        .outerjoin(
            ConversationMessage,
            ConversationMessage.session_id == ConversationSession.id,
        )
        .where(ConversationSession.user_id == user_id)
        .group_by(ConversationSession.id)
        .order_by(ConversationSession.updated_at.desc())
        .limit(limit)
    )
    return [(session, int(message_count)) for session, message_count in result.all()]


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
