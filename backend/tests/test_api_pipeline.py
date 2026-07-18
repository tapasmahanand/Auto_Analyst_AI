"""End-to-end API test with the LLM mocked: upload -> analyze -> report."""

import json
import textwrap

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import pipeline
from app.services.executor import RESULT_END, RESULT_START

WORKING_SCRIPT = textwrap.dedent(
    f"""
    import matplotlib
    matplotlib.use("Agg")
    import json
    import matplotlib.pyplot as plt
    import pandas as pd

    df = pd.read_csv("data.csv")
    by_region = df.groupby("region")["revenue"].sum().sort_values(ascending=False)

    plt.figure(figsize=(6, 4))
    by_region.plot(kind="bar", title="Revenue by region")
    plt.ylabel("Revenue")
    plt.savefig("charts/revenue_by_region.png", dpi=100, bbox_inches="tight")
    plt.close()

    result = {{"revenue_by_region": by_region.round(2).to_dict()}}
    print("{RESULT_START}")
    print(json.dumps(result))
    print("{RESULT_END}")
    """
)


class FakeLLM:
    """Stands in for LLMClient; routes on the system prompt content."""

    def __init__(self, *args, **kwargs):
        pass

    def chat_json(self, system: str, user: str, **kwargs) -> dict:
        if "planning" in system:
            return {
                "steps": [
                    {
                        "goal": "Total revenue by region",
                        "method": "Group-by aggregation with a bar chart",
                    }
                ]
            }
        if "reviewing" in system:
            return {
                "assessment": "Results answer the request.",
                "gaps": [],
                "limitations": ["Single-metric analysis."],
            }
        return {
            "title": "Revenue by Region",
            "executive_summary": "North leads on revenue.",
            "key_findings": [
                {"finding": "North has the highest revenue", "supporting_numbers": "see table"}
            ],
            "recommendations": ["Investigate South underperformance."],
            "limitations": ["Sample data only."],
        }

    def chat_code(self, system: str, user: str) -> str:
        return WORKING_SCRIPT


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(pipeline, "LLMClient", FakeLLM)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def dataset_id(client, tmp_path) -> str:
    csv = tmp_path / "sales.csv"
    csv.write_text(
        "region,revenue\nNorth,100\nSouth,50\nNorth,120\nEast,80\n"
    )
    with open(csv, "rb") as f:
        response = client.post("/api/datasets", files={"file": ("sales.csv", f, "text/csv")})
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["metadata"]["row_count"] == 4
    return payload["id"]


def test_upload_rejects_unsupported_type(client):
    response = client.post(
        "/api/datasets", files={"file": ("evil.exe", b"MZ", "application/octet-stream")}
    )
    assert response.status_code == 400


def test_full_analysis_flow(client, dataset_id):
    # TestClient runs background tasks synchronously after the response,
    # so the run is finished once the POST returns.
    response = client.post(
        "/api/analyses", json={"dataset_id": dataset_id, "prompt": "Which region earns the most?"}
    )
    assert response.status_code == 201
    run_id = response.json()["id"]

    run = client.get(f"/api/analyses/{run_id}").json()
    assert run["status"] == "completed", run.get("error")
    assert run["plan"]["steps"][0]["goal"] == "Total revenue by region"
    assert run["steps"][0]["status"] == "completed"
    assert run["steps"][0]["result"]["revenue_by_region"]["North"] == 220
    assert len(run["charts"]) == 1
    assert set(run["reports"]) >= {"md", "html"}

    # Chart artifact is downloadable
    chart = client.get(run["charts"][0]["url"])
    assert chart.status_code == 200
    assert chart.headers["content-type"] == "image/png"

    # Reports download in both guaranteed formats
    md = client.get(f"/api/analyses/{run_id}/report", params={"format": "md"})
    assert md.status_code == 200
    assert "Revenue by Region" in md.text

    html = client.get(f"/api/analyses/{run_id}/report", params={"format": "html"})
    assert html.status_code == 200
    assert "data:image/png;base64," in html.text

    # History endpoint lists the run
    history = client.get("/api/analyses").json()
    assert any(item["id"] == run_id for item in history)


def test_analysis_missing_dataset_404(client):
    response = client.post(
        "/api/analyses", json={"dataset_id": "nope", "prompt": "anything at all"}
    )
    assert response.status_code == 404
