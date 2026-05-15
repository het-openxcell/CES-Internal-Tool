from pydantic import BaseModel


class NLQueryRequest(BaseModel):
    query: str


class TimeLogSource(BaseModel):
    ddr_id: str | None = None
    date: str | None = None
    well_name: str | None = None
    surface_location: str | None = None
    text: str | None = None
    score: float | None = None


class NLQueryResponse(BaseModel):
    answer: str
    sources: list[TimeLogSource]
    expanded_queries: list[str]
