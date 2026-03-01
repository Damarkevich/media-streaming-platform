from typing import Annotated

from fastapi import Query


class PaginationParams:
    """Pagination parameters for API endpoints."""

    def __init__(
        self,
        page_size: Annotated[
            int, Query(description="Pagination page size", ge=1, le=100)
        ] = 10,
        page_number: Annotated[
            int, Query(description="Pagination page number", ge=0)
        ] = 0,
    ):
        self.page_size = page_size
        self.page_number = page_number
