from datetime import datetime

from pydantic import BaseModel, HttpUrl


class SiteCreateSchema(BaseModel):
    name: str
    url: HttpUrl


class SiteResponseSchema(BaseModel):
    id: int
    name: str
    url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CheckResponseSchema(BaseModel):
    id: int
    site_id: int
    is_available: bool
    status_code: int | None
    response_time_ms: float | None
    checked_at: datetime

    model_config = {"from_attributes": True}


class RunChecksResponseSchema(BaseModel):
    total: int
    available: int
    unavailable: int
    results: list[CheckResponseSchema]