from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    status_code: int = 200
    status: str = "success"
    message: str
    data: T
