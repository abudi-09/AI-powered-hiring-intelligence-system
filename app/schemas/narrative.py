from __future__ import annotations

import uuid
from enum import Enum

from pydantic import BaseModel, Field
class NarrativeTone(str, Enum):
    professional = "professional"
    executive = "executive"
    neutral = "neutral"
    technical = "technical"


class NarrativeRequest(BaseModel):
    recommendation_id: uuid.UUID
    tone: NarrativeTone = NarrativeTone.professional
    include_bullets: bool = True


class BatchNarrativeRequest(BaseModel):
    recommendation_ids: list[uuid.UUID] = Field(max_items=50)
    tone: NarrativeTone = NarrativeTone.professional
    include_bullets: bool = True


class NarrativeRead(BaseModel):
    recommendation_id: uuid.UUID
    narrative_text: str
    summary_bullets: list[str]
    tone_used: str
    confidence: float
    version: str


class BatchNarrativeRead(BaseModel):
    narratives: list[NarrativeRead]
    total: int = 0

    def __init__(self, narratives: list[NarrativeRead], **kwargs):
        super().__init__(narratives=narratives, total=len(narratives), **kwargs)
