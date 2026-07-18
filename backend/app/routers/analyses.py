import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..db import SessionLocal, get_db
from ..models import AnalysisRun, Artifact, Dataset
from ..schemas import AnalysisCreate
from ..services import pipeline

router = APIRouter(prefix="/api", tags=["analyses"])

SSE_MAX_SECONDS = 1800

_MEDIA_TYPES = {
    ".png": "image/png",
    ".py": "text/plain",
    ".md": "text/markdown",
    ".html": "text/html",
    ".pdf": "application/pdf",
}


def serialize_run(run: AnalysisRun, full: bool = True) -> dict:
    payload = {
        "id": run.id,
        "dataset_id": run.dataset_id,
        "dataset_filename": run.dataset.filename if run.dataset else None,
        "prompt": run.prompt,
        "status": run.status,
        "error": run.error,
        "created_at": run.created_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }
    if not full:
        return payload

    payload["plan"] = json.loads(run.plan_json) if run.plan_json else None
    payload["review"] = json.loads(run.review_json) if run.review_json else None
    payload["insights"] = json.loads(run.insights_json) if run.insights_json else None
    payload["steps"] = [
        {
            "id": step.id,
            "index": step.index,
            "goal": step.goal,
            "method": step.method,
            "status": step.status,
            "attempts": step.attempts,
            "error": step.error,
            "result": json.loads(step.result_json) if step.result_json else None,
            "charts": [
                {"id": a.id, "name": a.name, "url": f"/api/artifacts/{a.id}"}
                for a in step.artifacts
                if a.kind == "chart"
            ],
        }
        for step in run.steps
    ]
    payload["charts"] = [
        {"id": a.id, "name": a.name, "url": f"/api/artifacts/{a.id}"}
        for a in run.artifacts
        if a.kind == "chart"
    ]
    payload["reports"] = sorted(
        a.name.rsplit(".", 1)[-1] for a in run.artifacts if a.kind == "report"
    )
    return payload


@router.post("/analyses", status_code=201)
def create_analysis(
    body: AnalysisCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> dict:
    dataset = db.get(Dataset, body.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    run = AnalysisRun(dataset_id=dataset.id, prompt=body.prompt.strip())
    db.add(run)
    db.commit()
    background_tasks.add_task(pipeline.run_analysis, run.id)
    return serialize_run(run, full=False)


@router.get("/analyses")
def list_analyses(db: Session = Depends(get_db)) -> list[dict]:
    runs = (
        db.query(AnalysisRun).order_by(desc(AnalysisRun.created_at)).limit(50).all()
    )
    return [serialize_run(r, full=False) for r in runs]


@router.get("/analyses/{run_id}")
def get_analysis(run_id: str, db: Session = Depends(get_db)) -> dict:
    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return serialize_run(run)


@router.get("/analyses/{run_id}/events")
async def analysis_events(run_id: str) -> StreamingResponse:
    async def event_stream():
        for _ in range(SSE_MAX_SECONDS):
            db = SessionLocal()
            try:
                run = db.get(AnalysisRun, run_id)
                payload = serialize_run(run) if run else None
            finally:
                db.close()
            if payload is None:
                yield 'data: {"error": "not_found"}\n\n'
                return
            yield f"data: {json.dumps(payload, default=str)}\n\n"
            if payload["status"] in ("completed", "failed"):
                return
            await asyncio.sleep(1.0)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/artifacts/{artifact_id}")
def get_artifact(artifact_id: str, db: Session = Depends(get_db)) -> FileResponse:
    artifact = db.get(Artifact, artifact_id)
    if artifact is None or not Path(artifact.path).exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    media_type = _MEDIA_TYPES.get(Path(artifact.path).suffix.lower(), "application/octet-stream")
    return FileResponse(artifact.path, media_type=media_type, filename=artifact.name)
