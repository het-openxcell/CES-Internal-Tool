from pydantic import BaseModel, Field


class PaginationModel(BaseModel):
    current_page: int
    total_pages: int
    items_per_page: int
    total_items: int


class MessageModel(BaseModel):
    title: str
    description: str


class DataModel(BaseModel):
    details: dict | list | None = None
    pagination: PaginationModel | None = None


class ResponseModel(BaseModel):
    success: bool
    message: MessageModel
    data: DataModel = Field(default_factory=DataModel, exclude=False)
    error_code: int
    call_hierarchy: str | None = None
