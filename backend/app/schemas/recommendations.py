from pydantic import BaseModel


class RecommendationItem(BaseModel):
    priority: int
    action: str
    rationale: str
    evidence: str


class RecommendationsResponse(BaseModel):
    project_id: int
    project_code: str
    methodology: str
    items: list[RecommendationItem]
    limitations: list[str]
