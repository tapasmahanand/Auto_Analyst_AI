import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import Dataset
from ..services import inspection

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

CHUNK_SIZE = 1024 * 1024


def serialize_dataset(dataset: Dataset, include_metadata: bool = True) -> dict:
    payload = {
        "id": dataset.id,
        "filename": dataset.filename,
        "file_type": dataset.file_type,
        "size_bytes": dataset.size_bytes,
        "created_at": dataset.created_at.isoformat(),
    }
    if include_metadata:
        payload["metadata"] = json.loads(dataset.metadata_json or "{}")
    return payload


@router.post("", status_code=201)
async def upload_dataset(file: UploadFile, db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    file_type = inspection.file_type_for(file.filename or "")
    if file_type is None:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Allowed: CSV, Excel, JSON, TXT, PDF.",
        )

    suffix = "." + (file.filename or "").rsplit(".", 1)[-1].lower()
    stored_path = settings.uploads_dir / f"{uuid.uuid4().hex}{suffix}"
    max_bytes = settings.max_upload_mb * 1024 * 1024
    size = 0
    with open(stored_path, "wb") as out:
        while chunk := await file.read(CHUNK_SIZE):
            size += len(chunk)
            if size > max_bytes:
                out.close()
                stored_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds the {settings.max_upload_mb} MB upload limit.",
                )
            out.write(chunk)
    if size == 0:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        metadata = inspection.inspect_dataset(stored_path, file_type)
    except Exception as exc:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=422, detail=f"Could not inspect the file: {exc}"
        ) from exc

    dataset = Dataset(
        filename=file.filename or stored_path.name,
        stored_path=str(stored_path),
        file_type=file_type,
        size_bytes=size,
        metadata_json=json.dumps(metadata, default=str),
    )
    db.add(dataset)
    db.commit()
    return serialize_dataset(dataset)


@router.get("")
def list_datasets(db: Session = Depends(get_db)) -> list[dict]:
    datasets = db.query(Dataset).order_by(desc(Dataset.created_at)).limit(50).all()
    return [serialize_dataset(d, include_metadata=False) for d in datasets]


@router.get("/{dataset_id}")
def get_dataset(dataset_id: str, db: Session = Depends(get_db)) -> dict:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return serialize_dataset(dataset)
