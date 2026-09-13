import argparse
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from backend.app.core.config import PROJECT_ROOT
from backend.app.db.session import SessionLocal
from ml.training.pipeline import train_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Train snapshot cost/time risk models.")
    parser.add_argument("--dataset-id", type=int, required=True)
    parser.add_argument("--analysis-date", type=date.fromisoformat)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--artifact-dir", type=Path, default=PROJECT_ROOT / "artifacts" / "models")
    args = parser.parse_args()

    with SessionLocal() as session:
        results = train_dataset(
            session,
            dataset_id=args.dataset_id,
            analysis_date=args.analysis_date,
            artifact_root=args.artifact_dir,
            seed=args.seed,
        )
    print(json.dumps([asdict(result) for result in results], indent=2))


if __name__ == "__main__":
    main()
