# -*- coding: utf-8 -*-

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    BLOB,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(512))
    content: Mapped[Optional[str]] = mapped_column(Text)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))
    source: Mapped[Optional[str]] = mapped_column(String(128))
    metadata: Mapped[Optional[dict]] = mapped_column(JSON().with_variant(Text, "sqlite"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    chunks: Mapped[list[Chunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    entities: Mapped[list[Entity]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_documents_content_hash", "content_hash"),
        Index("ix_documents_source", "source"),
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON().with_variant(Text, "sqlite"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    document: Mapped[Document] = relationship(back_populates="chunks")
    embeddings: Mapped[list[Embedding]] = relationship(
        back_populates="chunk", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_chunk_doc_index"),
        Index("ix_chunks_document_id", "document_id"),
        Index("ix_chunks_created_at", "created_at"),
    )


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_id: Mapped[int] = mapped_column(ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    # Store vector as JSON text on SQLite for simplicity. Use BLOB on other backends.
    vector: Mapped[bytes | str] = mapped_column(Text)
    dim: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    chunk: Mapped[Chunk] = relationship(back_populates="embeddings")

    __table_args__ = (
        UniqueConstraint("chunk_id", "model", name="uq_embedding_chunk_model"),
        Index("ix_embeddings_chunk_model", "chunk_id", "model"),
    )


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[Optional[str]] = mapped_column(String(128))
    value: Mapped[str] = mapped_column(String(512))
    start_pos: Mapped[Optional[int]] = mapped_column(Integer)
    end_pos: Mapped[Optional[int]] = mapped_column(Integer)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON().with_variant(Text, "sqlite"))

    document: Mapped[Document] = relationship(back_populates="entities")

    __table_args__ = (
        Index("ix_entities_document_id", "document_id"),
        Index("ix_entities_type_value", "type", "value"),
    )


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSON().with_variant(Text, "sqlite"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_events_created_at", "created_at"),
        Index("ix_events_event_type", "event_type"),
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    payload: Mapped[Optional[dict]] = mapped_column(JSON().with_variant(Text, "sqlite"))
    result: Mapped[Optional[dict]] = mapped_column(JSON().with_variant(Text, "sqlite"))
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dedupe_key: Mapped[Optional[str]] = mapped_column(String(255))

    __table_args__ = (
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_priority", "priority"),
        Index("ix_jobs_scheduled_at", "scheduled_at"),
        UniqueConstraint("dedupe_key", name="uq_jobs_dedupe_key"),
        CheckConstraint("attempts >= 0", name="ck_jobs_attempts_nonnegative"),
    )


# Expose metadata for Alembic
metadata = Base.metadata
