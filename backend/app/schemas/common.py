from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class GenericMessageResponse(BaseModel):
    success: bool = True
    message: str
    detail: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    page_size: int = 20
    pages: int = 1
