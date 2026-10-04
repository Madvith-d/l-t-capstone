from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Intent(str, Enum):
    ACADEMIC_QA = "ACADEMIC_QA"
    DOCUMENT_SEARCH = "DOCUMENT_SEARCH"
    STUDY_PLAN = "STUDY_PLAN"
    STUDY_PLAN_MODIFICATION = "STUDY_PLAN_MODIFICATION"
    CALCULATION = "CALCULATION"
    CALENDAR_ACTION = "CALENDAR_ACTION"
    MULTI_STEP = "MULTI_STEP"
    GENERAL_CONVERSATION = "GENERAL_CONVERSATION"
    UNKNOWN = "UNKNOWN"


class Source(BaseModel):
    document_id: str
    title: str
    page: int | None = None
    section: str | None = None
    category: str | None = None
    department: str | None = None
    academic_year: str | None = None
    source: str
    score: float | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None
    user_id: str | None = None
    plan_id: str | None = None
    plan_request: dict | None = None
    filters: dict[str, str] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    conversation_id: str
    intent: Intent
    answer: str
    sources: list[Source] = Field(default_factory=list)
    confidence: float = 0
    tool_results: list[dict] = Field(default_factory=list)
    graph_route: list[str] = Field(default_factory=list)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    role: str
    content: str
    sources: list = Field(default_factory=list)
    created_at: datetime


class ConversationCreate(BaseModel):
    user_id: str | None = None
    title: str = Field("New conversation", min_length=1, max_length=255)


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    summary: str | None
    created_at: datetime
    updated_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    summary: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = Field(default_factory=list)


class SubjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    topics: list[str] = Field(min_length=1)
    difficulty: int = Field(3, ge=1, le=5)


class PlanCreate(BaseModel):
    user_id: str | None = None
    title: str = "Study plan"
    subjects: list[SubjectInput] = Field(min_length=1)
    exam_date: date
    available_hours_per_day: float = Field(gt=0, le=16)
    start_date: date | None = None
    preferred_times: list[str] = Field(default_factory=list)


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str | None = None
    session_date: date
    subject: str
    topic: str
    duration_minutes: int = Field(gt=0)
    preferred_time: str | None = None
    status: str = "planned"


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    exam_date: date
    available_hours_per_day: float
    subjects: list
    constraints: dict
    version: int
    sessions: list[SessionOut]


class PlanPatch(BaseModel):
    instruction: str = Field(min_length=3, max_length=1000)


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    category: str | None
    department: str | None
    academic_year: str | None
    source: str
    status: str
    created_at: datetime


class IngestMetadata(BaseModel):
    title: str | None = None
    category: str | None = None
    department: str | None = None
    academic_year: str | None = None
    section: str | None = None
