from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter

import httpx

ROOT = Path(__file__).resolve().parents[1]


def timed(label: str, action):
    started = perf_counter()
    result = action()
    return result, round(perf_counter() - started, 3)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SIH 26103 end-to-end demonstration flow.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--report", type=Path, default=ROOT / "DATA" / "Projects_Report.csv")
    parser.add_argument("--source-as-of-date", default="2026-09-01")
    parser.add_argument("--skip-training", action="store_true")
    args = parser.parse_args()

    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not password:
        raise SystemExit("Set ADMIN_PASSWORD in the environment before running the demo.")

    timings: dict[str, float] = {}
    with httpx.Client(base_url=args.base_url, timeout=30) as client:
        health, timings["health_seconds"] = timed("health", lambda: client.get("/api/health"))
        health.raise_for_status()
        login, timings["login_seconds"] = timed("login", lambda: client.post("/api/auth/login", json={"username": username, "password": password}))
        login.raise_for_status()
        client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

        with args.report.open("rb") as report:
            upload, timings["import_seconds"] = timed(
                "import",
                lambda: client.post(
                    "/api/projects/upload",
                    data={"source_as_of_date": args.source_as_of_date},
                    files={"file": (args.report.name, report, "text/csv")},
                ),
            )
        upload.raise_for_status()
        dataset_id = upload.json()["dataset_id"]
        quality, timings["quality_seconds"] = timed("quality", lambda: client.get(f"/api/datasets/{dataset_id}/quality?limit=1"))
        quality.raise_for_status()

        if not args.skip_training:
            training_started = perf_counter()
            subprocess.run(
                [sys.executable, "-m", "ml.training.train", "--dataset-id", str(dataset_id), "--analysis-date", args.source_as_of_date, "--seed", "42"],
                cwd=ROOT,
                check=True,
            )
            timings["training_seconds"] = round(perf_counter() - training_started, 3)
            scoring_started = perf_counter()
            subprocess.run(
                [sys.executable, "-m", "ml.training.score", "--dataset-id", str(dataset_id), "--analysis-date", args.source_as_of_date],
                cwd=ROOT,
                check=True,
            )
            timings["scoring_seconds"] = round(perf_counter() - scoring_started, 3)

        summary, timings["dashboard_seconds"] = timed("dashboard", lambda: client.get(f"/api/dashboard/summary?dataset_id={dataset_id}"))
        summary.raise_for_status()
        projects, timings["projects_seconds"] = timed("projects", lambda: client.get(f"/api/projects?dataset_id={dataset_id}&limit=1"))
        projects.raise_for_status()
        first_project = projects.json()["items"][0]
        project_id = first_project["project_id"]
        detail, timings["detail_seconds"] = timed("detail", lambda: client.get(f"/api/risk/projects/{project_id}"))
        detail.raise_for_status()
        explanation, timings["explanation_seconds"] = timed("explanation", lambda: client.get(f"/api/risk/projects/{project_id}/explanation"))
        explanation.raise_for_status()
        benchmark, timings["benchmark_seconds"] = timed("benchmark", lambda: client.get(f"/api/analytics/benchmarks?project_id={project_id}"))
        benchmark.raise_for_status()
        assistant, timings["assistant_seconds"] = timed("assistant", lambda: client.post("/api/assistant/query", json={"question": "Which projects have the highest stored risk?", "dataset_id": dataset_id}))
        assistant.raise_for_status()

    print(json.dumps({
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "cpu_count": os.cpu_count()},
        "dataset_id": dataset_id,
        "project_code": first_project["project_code"],
        "timings_seconds": timings,
        "results": {
            "quality_issue_count": quality.json()["issue_count"],
            "dashboard": summary.json(),
            "risk_detail": detail.json(),
            "explanation_count": len(explanation.json()["explanations"]),
            "benchmark": benchmark.json(),
            "assistant": assistant.json(),
        },
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
