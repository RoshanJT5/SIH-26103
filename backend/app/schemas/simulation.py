from decimal import Decimal
from pydantic import BaseModel


class SimulationInput(BaseModel):
    project_id: int
    revised_cost_cr: Decimal | None = None
    expenditure_cr: Decimal | None = None
    physical_progress_pct: Decimal | None = None
    schedule_revision_days: int | None = None


class SimulationResult(BaseModel):
    project_id: int
    project_code: str
    original_overall_score: Decimal | None
    original_band: str | None
    simulated_overall_score: Decimal | None
    simulated_band: str | None
    delta: Decimal | None
    assumptions: list[str]
    note: str = "Read-only simulation: never persists."
