from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class BasePaginationRequest(BaseModel):
    """Base class for pagination requests."""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(30, ge=1, description="Items per page")
    orderby: str = Field("create_time", description="Field to sort by")
    desc: bool = Field(True, description="Sort in descending order")


class BasePaginationResponse(BaseModel):
    """Base class for pagination responses."""
    total: int = Field(..., description="Total count of items")
