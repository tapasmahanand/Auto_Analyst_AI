import json

import matplotlib
import pandas as pd
import pytest

matplotlib.use("Agg")

from app.services.inspection import file_type_for, inspect_dataset

REQUIRED_TABULAR_KEYS = {
    "file_type",
    "row_count",
    "column_count",
    "column_names",
    "dtypes",
    "missing_values",
    "duplicate_rows",
    "numeric_columns",
    "categorical_columns",
    "date_columns",
    "basic_statistics",
}


@pytest.fixture
def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_date": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-03"],
            "region": ["North", "South", "North", "North"],
            "revenue": [100.5, 200.0, None, 150.0],
        }
    )


def test_file_type_detection():
    assert file_type_for("a.CSV") == "csv"
    assert file_type_for("a.xlsx") == "excel"
    assert file_type_for("a.json") == "json"
    assert file_type_for("a.txt") == "txt"
    assert file_type_for("a.pdf") == "pdf"
    assert file_type_for("a.exe") is None


def test_inspect_csv(tmp_path, frame):
    path = tmp_path / "data.csv"
    frame.to_csv(path, index=False)
    meta = inspect_dataset(path, "csv")
    assert REQUIRED_TABULAR_KEYS <= meta.keys()
    assert meta["row_count"] == 4
    assert meta["column_count"] == 3
    assert meta["column_names"] == ["order_date", "region", "revenue"]
    assert meta["missing_values"]["revenue"] == 1
    assert meta["numeric_columns"] == ["revenue"]
    assert "region" in meta["categorical_columns"]
    assert meta["date_columns"] == ["order_date"]
    json.dumps(meta)  # must be JSON-serializable


def test_inspect_excel(tmp_path, frame):
    path = tmp_path / "data.xlsx"
    frame.to_excel(path, index=False)
    meta = inspect_dataset(path, "excel")
    assert meta["row_count"] == 4
    assert meta["numeric_columns"] == ["revenue"]


def test_inspect_json_records(tmp_path, frame):
    path = tmp_path / "data.json"
    path.write_text(frame.to_json(orient="records"))
    meta = inspect_dataset(path, "json")
    assert meta["is_tabular"] is True
    assert meta["row_count"] == 4
    assert meta["column_count"] == 3


def test_inspect_tabular_txt(tmp_path, frame):
    path = tmp_path / "data.txt"
    frame.to_csv(path, index=False, sep="\t")
    meta = inspect_dataset(path, "txt")
    assert meta["is_tabular"] is True
    assert meta["column_count"] == 3


def test_inspect_free_text_txt(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("Quarterly review notes.\nRevenue grew nicely.\nNo table here.")
    meta = inspect_dataset(path, "txt")
    assert meta["is_tabular"] is False
    assert meta["row_count"] == 3
    assert meta["text_words"] > 0
    assert "preview" in json.dumps(meta) or meta["text_preview"]


def test_inspect_pdf_text(tmp_path):
    import matplotlib.pyplot as plt

    path = tmp_path / "doc.pdf"
    fig = plt.figure(figsize=(6, 4))
    fig.text(0.1, 0.5, "Annual report narrative text without tables.")
    fig.savefig(path, format="pdf")
    plt.close(fig)

    meta = inspect_dataset(path, "pdf")
    assert meta["file_type"] == "pdf"
    assert meta["is_tabular"] is False
    assert meta["text_characters"] > 0
