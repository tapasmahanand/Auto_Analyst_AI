"""Agent orchestration: plan -> generate code -> execute -> correct -> review
-> insights -> report. Runs as a background task; progress is persisted to
SQLite so the API/SSE endpoints can stream it to the frontend.
"""

import json
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from .. import prompts
from ..config import get_settings
from ..db import SessionLocal
from ..models import AnalysisRun, AnalysisStep, Artifact
from . import executor
from .llm import LLMClient, LLMError
from .report import generate_reports


def run_analysis(run_id: str) -> None:
    db = SessionLocal()
    try:
        _run(db, run_id)
    except Exception as exc:  # last-resort guard so a run never hangs in "running"
        db.rollback()
        run = db.get(AnalysisRun, run_id)
        if run is not None:
            run.status = "failed"
            run.error = f"{exc}\n{traceback.format_exc(limit=5)}"
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


def _run(db: Session, run_id: str) -> None:
    settings = get_settings()
    run = db.get(AnalysisRun, run_id)
    if run is None:
        return
    dataset = run.dataset
    metadata = json.loads(dataset.metadata_json or "{}")
    metadata_str = json.dumps(metadata, indent=1)[:6000]

    try:
        llm = LLMClient()
    except LLMError as exc:
        _fail(db, run, str(exc))
        return

    # --- 1. Plan ---------------------------------------------------------
    run.status = "planning"
    db.commit()

    plan = llm.chat_json(
        prompts.PLANNER_SYSTEM.format(max_steps=settings.max_plan_steps),
        prompts.PLANNER_USER.format(prompt=run.prompt, metadata=metadata_str),
    )
    steps_spec = (plan.get("steps") or [])[: settings.max_plan_steps]
    if not steps_spec:
        _fail(db, run, "The planner did not produce any analysis steps.")
        return

    run.plan_json = json.dumps({"steps": steps_spec})
    steps: list[AnalysisStep] = []
    for i, spec in enumerate(steps_spec):
        step = AnalysisStep(
            run_id=run.id,
            index=i,
            goal=str(spec.get("goal", f"Step {i + 1}")),
            method=str(spec.get("method", "")),
        )
        db.add(step)
        steps.append(step)
    run.status = "running"
    db.commit()

    # --- 2. Execute steps with correction loop ---------------------------
    run_dir = settings.runs_dir / run.id
    run_dir.mkdir(parents=True, exist_ok=True)
    data_filename = f"data{Path(dataset.stored_path).suffix.lower()}"

    codegen_system = prompts.CODEGEN_SYSTEM.format(
        data_filename=data_filename,
        result_start=executor.RESULT_START,
        result_end=executor.RESULT_END,
        timeout=settings.exec_timeout_seconds,
    )

    prior_results: list[dict] = []
    failures: list[str] = []

    for step in steps:
        step.status = "running"
        db.commit()

        exec_dir = run_dir / f"step_{step.index}"
        exec_dir.mkdir(exist_ok=True)
        shutil.copyfile(dataset.stored_path, exec_dir / data_filename)

        code = llm.chat_code(
            codegen_system,
            prompts.CODEGEN_USER.format(
                goal=step.goal,
                method=step.method,
                prompt=run.prompt,
                metadata=metadata_str,
                prior_results=json.dumps(prior_results, default=str)[:4000],
            ),
        )

        last_error = ""
        result = None
        for attempt in range(1, settings.max_code_retries + 2):
            step.attempts = attempt
            _save_code_artifact(db, run, step, code, attempt)
            db.commit()

            result = executor.run_code(
                code,
                exec_dir,
                timeout_seconds=settings.exec_timeout_seconds,
                memory_mb=settings.exec_memory_mb,
            )
            if result.ok:
                break

            last_error = "\n".join(
                filter(None, [result.error, result.stderr[-3000:], result.stdout[-1000:]])
            )
            if attempt > settings.max_code_retries:
                break
            step.status = "retrying"
            db.commit()
            code = llm.chat_code(
                codegen_system,
                prompts.FIXER_USER.format(
                    goal=step.goal, method=step.method, code=code, error=last_error
                ),
            )
            step.status = "running"
            db.commit()

        if result is not None and result.ok:
            step.status = "completed"
            step.result_json = json.dumps(result.result or {"stdout": result.stdout[-2000:]})
            for chart in result.charts:
                _save_chart_artifact(db, run, step, chart, run_dir)
            prior_results.append(
                {"step": step.index + 1, "goal": step.goal, "results": result.result}
            )
        else:
            step.status = "failed"
            step.error = last_error[:4000]
            failures.append(f"Step {step.index + 1} ({step.goal}): {last_error[:300]}")
        db.commit()

    if not prior_results:
        _fail(db, run, "All analysis steps failed. " + " | ".join(failures)[:2000])
        return

    # --- 3. Review -------------------------------------------------------
    run.status = "reviewing"
    db.commit()
    review = llm.chat_json(
        prompts.REVIEWER_SYSTEM,
        prompts.REVIEWER_USER.format(
            prompt=run.prompt,
            results=json.dumps(prior_results, default=str)[:8000],
            failures="; ".join(failures) or "none",
        ),
    )
    run.review_json = json.dumps(review)
    db.commit()

    # --- 4. Insights -----------------------------------------------------
    insights = llm.chat_json(
        prompts.INSIGHTS_SYSTEM,
        prompts.INSIGHTS_USER.format(
            prompt=run.prompt,
            metadata=metadata_str,
            results=json.dumps(prior_results, default=str)[:8000],
            review=json.dumps(review),
        ),
    )
    run.insights_json = json.dumps(insights)

    # --- 5. Report -------------------------------------------------------
    run.status = "reporting"
    db.commit()
    generate_reports(db, run)

    run.status = "completed"
    run.completed_at = datetime.now(timezone.utc)
    db.commit()


def _fail(db: Session, run: AnalysisRun, message: str) -> None:
    run.status = "failed"
    run.error = message
    run.completed_at = datetime.now(timezone.utc)
    db.commit()


def _save_code_artifact(
    db: Session, run: AnalysisRun, step: AnalysisStep, code: str, attempt: int
) -> None:
    settings = get_settings()
    code_dir = settings.runs_dir / run.id / "code"
    code_dir.mkdir(parents=True, exist_ok=True)
    name = f"step{step.index + 1}_attempt{attempt}.py"
    path = code_dir / name
    path.write_text(code, encoding="utf-8")
    db.add(
        Artifact(run_id=run.id, step_id=step.id, kind="code", name=name, path=str(path))
    )


def _save_chart_artifact(
    db: Session, run: AnalysisRun, step: AnalysisStep, chart: Path, run_dir: Path
) -> None:
    charts_dir = run_dir / "charts"
    charts_dir.mkdir(exist_ok=True)
    name = f"step{step.index + 1}_{chart.name}"
    dest = charts_dir / name
    shutil.copyfile(chart, dest)
    db.add(
        Artifact(run_id=run.id, step_id=step.id, kind="chart", name=name, path=str(dest))
    )
