from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AnalysisRun, Artifact

router = APIRouter(prefix="/api", tags=["reports"])

_MEDIA_TYPES = {
    "md": "text/markdown",
    "html": "text/html",
    "pdf": "application/pdf",
}


@router.get("/analyses/{run_id}/report")
def download_report(
    run_id: str,
    format: str = Query("html", pattern="^(md|html|pdf)$"),
    db: Session = Depends(get_db),
) -> FileResponse:
    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    artifact = (
        db.query(Artifact)
        .filter(
            Artifact.run_id == run_id,
            Artifact.kind == "report",
            Artifact.name == f"report.{format}",
        )
        .first()
    )
    if artifact is None or not Path(artifact.path).exists():
        detail = (
            "PDF report is unavailable (WeasyPrint system libraries not installed); "
            "download the HTML report instead."
            if format == "pdf"
            else "Report not generated yet."
        )
        raise HTTPException(status_code=404, detail=detail)

    stem = Path(run.dataset.filename).stem if run.dataset else "analysis"
    return FileResponse(
        artifact.path,
        media_type=_MEDIA_TYPES[format],
        filename=f"autoanalyst_report_{stem}.{format}",
    )
