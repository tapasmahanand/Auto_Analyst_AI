"""Deterministic dataset inspection (no LLM involved).

Loads CSV / Excel / JSON / TXT / PDF files, detects tabular structure where
possible, and produces the metadata required by the spec: file type, row and
column counts, column names, dtypes, missing values, duplicates, column
categories (numeric / categorical / date) and basic statistics.
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json", ".txt", ".pdf"}

_EXT_TO_TYPE = {
    ".csv": "csv",
    ".xlsx": "excel",
    ".xls": "excel",
    ".json": "json",
    ".txt": "txt",
    ".pdf": "pdf",
}

MAX_PREVIEW_ROWS = 5
MAX_UNIQUE_FOR_CATEGORICAL = 1000


def file_type_for(filename: str) -> str | None:
    return _EXT_TO_TYPE.get(Path(filename).suffix.lower())


def _json_safe(obj):
    """Convert pandas/numpy values into JSON-serializable python values."""
    return json.loads(
        json.dumps(obj, default=_json_default, ensure_ascii=False)
    )


def _json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if value is pd.NaT:
        return None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return str(value)


def _records(df: pd.DataFrame, n: int) -> list[dict]:
    head = df.head(n)
    return json.loads(head.to_json(orient="records", date_format="iso"))


def load_dataframe(path: Path, file_type: str) -> pd.DataFrame | None:
    """Try to load the file as a table. Returns None when not tabular."""
    try:
        if file_type == "csv":
            return pd.read_csv(path, sep=None, engine="python", encoding_errors="replace")
        if file_type == "excel":
            return pd.read_excel(path)
        if file_type == "json":
            return _load_json(path)
        if file_type == "txt":
            return _load_txt(path)
        if file_type == "pdf":
            return _load_pdf_tables(path)
    except Exception:
        return None
    return None


def _load_json(path: Path) -> pd.DataFrame | None:
    with open(path, encoding="utf-8", errors="replace") as f:
        data = json.load(f)
    if isinstance(data, list):
        return pd.json_normalize(data)
    if isinstance(data, dict):
        # A dict of equal-length lists reads as columns; otherwise normalize.
        try:
            return pd.DataFrame(data)
        except ValueError:
            return pd.json_normalize(data)
    return None


def _load_txt(path: Path) -> pd.DataFrame | None:
    import csv

    sample = path.read_text(encoding="utf-8", errors="replace")[:8192]
    try:
        # Only accept real tabular delimiters; prose must not sniff as a table.
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
    except csv.Error:
        return None
    df = pd.read_csv(
        path, sep=dialect.delimiter, engine="python", encoding_errors="replace"
    )
    if df.shape[1] <= 1:
        return None
    return df


def _load_pdf_tables(path: Path) -> pd.DataFrame | None:
    import pdfplumber

    tables: list[pd.DataFrame] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:50]:
            for raw in page.extract_tables() or []:
                if raw and len(raw) > 1:
                    header, *rows = raw
                    if header and all(h is not None for h in header):
                        tables.append(pd.DataFrame(rows, columns=header))
    if not tables:
        return None
    df = max(tables, key=len)
    # Values come out of pdfplumber as strings; recover numerics where possible.
    for col in df.columns:
        cleaned = df[col].astype(str).str.replace(",", "", regex=False)
        converted = pd.to_numeric(cleaned, errors="coerce")
        if converted.notna().mean() >= 0.8:
            df[col] = converted
    return df


def _extract_text(path: Path, file_type: str) -> str:
    if file_type == "pdf":
        import pdfplumber

        parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:50]:
                parts.append(page.extract_text() or "")
        return "\n".join(parts)
    return path.read_text(encoding="utf-8", errors="replace")


def _detect_date_columns(df: pd.DataFrame) -> list[str]:
    date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for col in df.columns:
            is_texty = pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col])
            if col in date_cols or not is_texty:
                continue
            sample = df[col].dropna().astype(str).head(50)
            if sample.empty:
                continue
            # Purely numeric strings ("2024", "15") are too ambiguous to call dates.
            if sample.str.fullmatch(r"[\d.]+").all():
                continue
            parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
            if parsed.notna().mean() >= 0.8:
                date_cols.append(col)
    return date_cols


def inspect_dataset(path: Path, file_type: str) -> dict:
    df = load_dataframe(path, file_type)
    meta: dict = {
        "file_type": file_type,
        "size_bytes": path.stat().st_size,
        "is_tabular": df is not None,
    }

    if df is None:
        text = _extract_text(path, file_type)
        lines = text.splitlines()
        meta.update(
            {
                "row_count": len(lines),
                "column_count": 0,
                "text_characters": len(text),
                "text_words": len(text.split()),
                "text_preview": text[:2000],
                "note": "File is not tabular; treated as a text document.",
            }
        )
        return meta

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    date_cols = _detect_date_columns(df)
    categorical_cols = [
        c
        for c in df.columns
        if c not in numeric_cols
        and c not in date_cols
        and df[c].nunique(dropna=True) <= MAX_UNIQUE_FOR_CATEGORICAL
    ]

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        describe = df.describe(include="all")
    basic_statistics = _json_safe(
        {col: describe[col].dropna().to_dict() for col in describe.columns}
    )

    meta.update(
        {
            "row_count": int(len(df)),
            "column_count": int(df.shape[1]),
            "column_names": [str(c) for c in df.columns],
            "dtypes": {str(c): str(t) for c, t in df.dtypes.items()},
            "missing_values": {str(c): int(df[c].isna().sum()) for c in df.columns},
            "total_missing_values": int(df.isna().sum().sum()),
            "duplicate_rows": int(df.duplicated().sum()),
            "numeric_columns": [str(c) for c in numeric_cols],
            "categorical_columns": [str(c) for c in categorical_cols],
            "date_columns": [str(c) for c in date_cols],
            "basic_statistics": basic_statistics,
            "sample_rows": _records(df, MAX_PREVIEW_ROWS),
        }
    )
    return meta
