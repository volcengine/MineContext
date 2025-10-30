"""
Initial core schema

Revision ID: 20251020_000001
Revises: 
Create Date: 2025-10-20 00:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251020_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # documents
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("doc_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=128), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),  # JSON as TEXT for SQLite
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])
    op.create_index("ix_documents_source", "documents", ["source"])

    # chunks
    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_chunk_doc_index"),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    op.create_index("ix_chunks_created_at", "chunks", ["created_at"])

    # embeddings
    op.create_table(
        "embeddings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chunk_id", sa.Integer(), sa.ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("vector", sa.Text(), nullable=True),  # JSON as TEXT for SQLite
        sa.Column("dim", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("chunk_id", "model", name="uq_embedding_chunk_model"),
    )
    op.create_index("ix_embeddings_chunk_model", "embeddings", ["chunk_id", "model"])

    # entities
    op.create_table(
        "entities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(length=128), nullable=True),
        sa.Column("value", sa.String(length=512), nullable=False),
        sa.Column("start_pos", sa.Integer(), nullable=True),
        sa.Column("end_pos", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
    )
    op.create_index("ix_entities_document_id", "entities", ["document_id"])
    op.create_index("ix_entities_type_value", "entities", ["type", "value"])

    # events
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_events_created_at", "events", ["created_at"])
    op.create_index("ix_events_event_type", "events", ["event_type"])

    # jobs
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_type", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.UniqueConstraint("dedupe_key", name="uq_jobs_dedupe_key"),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_priority", "jobs", ["priority"])
    op.create_index("ix_jobs_scheduled_at", "jobs", ["scheduled_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_scheduled_at", table_name="jobs")
    op.drop_index("ix_jobs_priority", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_table("jobs")

    op.drop_index("ix_events_event_type", table_name="events")
    op.drop_index("ix_events_created_at", table_name="events")
    op.drop_table("events")

    op.drop_index("ix_entities_type_value", table_name="entities")
    op.drop_index("ix_entities_document_id", table_name="entities")
    op.drop_table("entities")

    op.drop_index("ix_embeddings_chunk_model", table_name="embeddings")
    op.drop_table("embeddings")

    op.drop_index("ix_chunks_created_at", table_name="chunks")
    op.drop_index("ix_chunks_document_id", table_name="chunks")
    op.drop_table("chunks")

    op.drop_index("ix_documents_source", table_name="documents")
    op.drop_index("ix_documents_content_hash", table_name="documents")
    op.drop_table("documents")
