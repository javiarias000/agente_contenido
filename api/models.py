from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import JSON, Column, Field, SQLModel


class Brand(SQLModel, table=True):
    __tablename__ = "brands"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    slug: str = Field(unique=True, index=True)
    url: str | None = None
    colors: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    typography: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    tone_of_voice: str | None = None
    target_audience: str | None = None
    brand_values: list[str] | None = Field(default=None, sa_column=Column(JSON))
    style_notes: str | None = None
    content_suggestions: list[str] | None = Field(default=None, sa_column=Column(JSON))
    character_anchor: str | None = None
    preferred_voice_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PipelineRun(SQLModel, table=True):
    __tablename__ = "pipeline_runs"

    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(unique=True, index=True)
    pipeline_type: str  # ugc | avatar_reel | static_ads | carousel
    brand_id: int | None = Field(default=None, foreign_key="brands.id")
    status: str = "pending"  # pending | running | paused | completed | failed
    mode: str = "interactive"  # interactive | headless
    input_config: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    current_step: str | None = None
    steps_total: int | None = None
    steps_completed: int = 0
    error_message: str | None = None
    output_dir: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PipelineStep(SQLModel, table=True):
    __tablename__ = "pipeline_steps"

    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(index=True)
    step_name: str
    step_index: int
    status: str = "pending"  # pending | running | paused | completed | failed | skipped
    input_data: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    output_data: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    user_feedback: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None


class OutputAsset(SQLModel, table=True):
    __tablename__ = "output_assets"

    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(index=True)
    step_name: str | None = None
    asset_type: str  # script | image | audio | video | subtitle | ad | slide
    file_path: str
    file_size: int | None = None
    mime_type: str | None = None
    asset_metadata: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    brand_id: int | None = Field(default=None, foreign_key="brands.id")
    deleted: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
