from datetime import datetime

from pydantic import BaseModel


class UpdateItem(BaseModel):
    id: int
    category: str
    title: str
    summary: str
    content: str
    published_at: datetime
    updated_at: datetime
    status: str
    related_dataset_id: int | None = None
    meta: dict | None = None


class UpdateListResponse(BaseModel):
    items: list[UpdateItem]
    total: int
    limit: int
    offset: int
