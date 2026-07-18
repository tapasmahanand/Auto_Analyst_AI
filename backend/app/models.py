import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(Text)
    stored_path: Mapped[str] = mapped_column(Text)
    file_type: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(Integer)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    runs: Mapped[list["AnalysisRun"]] = relationship(back_populates="dataset")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"))
    prompt: Mapped[str] = mapped_column(Text)
    # pending -> planning -> running -> reviewing -> reporting -> completed | failed
    status: Mapped[str] = mapped_column(Text, default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    insights_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    dataset: Mapped[Dataset] = relationship(back_populates="runs")
    steps: Mapped[list["AnalysisStep"]] = relationship(
        back_populates="run", order_by="AnalysisStep.index"
    )
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="run")


class AnalysisStep(Base):
    __tablename__ = "analysis_steps"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"))
    index: Mapped[int] = mapped_column(Integer)
    goal: Mapped[str] = mapped_column(Text)
    method: Mapped[str] = mapped_column(Text, default="")
    # pending -> running -> retrying -> completed | failed
    status: Mapped[str] = mapped_column(Text, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped[AnalysisRun] = relationship(back_populates="steps")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="step")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"))
    step_id: Mapped[str | None] = mapped_column(
        ForeignKey("analysis_steps.id"), nullable=True
    )
    # code | chart | result | report
    kind: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    run: Mapped[AnalysisRun] = relationship(back_populates="artifacts")
    step: Mapped[AnalysisStep | None] = relationship(back_populates="artifacts")
