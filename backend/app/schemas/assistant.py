from typing import Literal

from pydantic import BaseModel, Field


AssistantIntent = Literal[
    "rank_projects",
    "explain_project",
    "summarize_group",
    "compare_peers",
    "find_deteriorating_projects",
    "list_early_warnings",
    "show_priority",
    "show_cost_drivers",
]


class AssistantQueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    dataset_id: int | None = Field(default=None, ge=1)


class AssistantSource(BaseModel):
    source_type: str
    source_id: str
    label: str


class AssistantQueryResponse(BaseModel):
    answer: str
    intent: AssistantIntent
    sources: list[AssistantSource]
    dataset_id: int | None
    model: str | None
    provider_status: Literal["groq", "fallback", "disabled"]
    caveats: list[str]
