from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str
    assistant_enabled: bool

