"""Final report rendering: Markdown + HTML always, PDF when WeasyPrint's
system libraries are available (graceful degradation otherwise).
"""

import base64
import json
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import AnalysisRun, Artifact

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def build_context(run: AnalysisRun) -> dict:
    dataset = run.dataset
    metadata = json.loads(dataset.metadata_json or "{}")
    insights = json.loads(run.insights_json or "{}")
    review = json.loads(run.review_json or "{}")

    charts = []
    for artifact in run.artifacts:
        if artifact.kind != "chart":
            continue
        path = Path(artifact.path)
        if path.exists():
            charts.append(
                {
                    "name": artifact.name,
                    "b64": base64.b64encode(path.read_bytes()).decode("ascii"),
                }
            )

    steps = [
        {
            "goal": step.goal,
            "method": step.method,
            "status": step.status,
            "attempts": step.attempts,
            "result": json.loads(step.result_json) if step.result_json else None,
        }
        for step in run.steps
    ]

    return {
        "title": insights.get("title") or f"Analysis of {dataset.filename}",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "prompt": run.prompt,
        "dataset": {
            "filename": dataset.filename,
            "file_type": dataset.file_type,
            "row_count": metadata.get("row_count"),
            "column_count": metadata.get("column_count"),
            "column_names": metadata.get("column_names") or [],
            "total_missing_values": metadata.get("total_missing_values"),
            "duplicate_rows": metadata.get("duplicate_rows"),
            "numeric_columns": metadata.get("numeric_columns") or [],
            "categorical_columns": metadata.get("categorical_columns") or [],
            "date_columns": metadata.get("date_columns") or [],
        },
        "steps": steps,
        "executive_summary": insights.get("executive_summary", ""),
        "key_findings": insights.get("key_findings") or [],
        "recommendations": insights.get("recommendations") or [],
        "limitations": (insights.get("limitations") or [])
        + (review.get("limitations") or []),
        "review": review,
        "charts": charts,
    }


def generate_reports(db: Session, run: AnalysisRun) -> dict[str, Path]:
    """Render all report formats and register them as artifacts."""
    settings = get_settings()
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    env = _environment()
    context = build_context(run)
    written: dict[str, Path] = {}

    md_path = settings.reports_dir / f"{run.id}.md"
    md_path.write_text(
        env.get_template("report.md.j2").render(**context), encoding="utf-8"
    )
    written["md"] = md_path

    html_path = settings.reports_dir / f"{run.id}.html"
    html = env.get_template("report.html.j2").render(**context)
    html_path.write_text(html, encoding="utf-8")
    written["html"] = html_path

    try:
        from weasyprint import HTML  # noqa: PLC0415 — optional system dependency

        pdf_path = settings.reports_dir / f"{run.id}.pdf"
        HTML(string=html).write_pdf(str(pdf_path))
        written["pdf"] = pdf_path
    except Exception:
        # PDF is best-effort: WeasyPrint needs system libraries (pango).
        # Markdown + HTML are always produced, which satisfies the spec.
        pass

    for fmt, path in written.items():
        db.add(
            Artifact(
                run_id=run.id,
                kind="report",
                name=f"report.{fmt}",
                path=str(path),
            )
        )
    db.commit()
    return written
