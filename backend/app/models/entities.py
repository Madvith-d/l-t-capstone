import enum
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import VectorType


def uid() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(UTC)


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    display_name: Mapped[str] = mapped_column(String(120), default="Student")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    conversations = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    study_plans = relationship("StudyPlan", back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[str | None] = mapped_column(String(100), index=True)
    department: Mapped[str | None] = mapped_column(String(100), index=True)
    academic_year: Mapped[str | None] = mapped_column(String(20), index=True)
    source: Mapped[str] = mapped_column(String(500))
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="ready")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    page_number: Mapped[int | None] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(255))
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    embedding: Mapped[list[float]] = mapped_column(VectorType(384))
    document = relationship("Document", back_populates="chunks")


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), default="New conversation")
    summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole))
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    conversation = relationship("Conversation", back_populates="messages")


class StudyPlan(Base):
    __tablename__ = "study_plans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), default="Study plan")
    exam_date: Mapped[date] = mapped_column(Date)
    available_hours_per_day: Mapped[float] = mapped_column(Float)
    subjects: Mapped[list] = mapped_column(JSON)
    constraints: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    user = relationship("User", back_populates="study_plans")
    sessions = relationship(
        "StudySession",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="StudySession.session_date",
    )


class StudySession(Base):
    __tablename__ = "study_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    plan_id: Mapped[str] = mapped_column(
        ForeignKey("study_plans.id", ondelete="CASCADE"), index=True
    )
    session_date: Mapped[date] = mapped_column(Date, index=True)
    subject: Mapped[str] = mapped_column(String(120))
    topic: Mapped[str] = mapped_column(String(255))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    preferred_time: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), default="planned")
    plan = relationship("StudyPlan", back_populates="sessions")
