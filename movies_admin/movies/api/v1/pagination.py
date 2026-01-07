from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class MoviePagination(PageNumberPagination):
    page_size = 50

    def get_previous_page_number(self):
        if not self.page.has_previous():
            return None
        return self.page.previous_page_number()

    def get_next_page_number(self):
        if not self.page.has_next():
            return None
        return self.page.next_page_number()

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "prev": self.get_previous_page_number(),
                "next": self.get_next_page_number(),
                "results": data,
            }
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "required": ["count", "total_pages", "prev", "next", "results"],
            "properties": {
                "count": {"type": "integer", "example": 123},
                "total_pages": {"type": "integer", "example": 5},
                "prev": {"type": "integer", "nullable": True, "example": 2},
                "next": {"type": "integer", "nullable": True, "example": 4},
                "results": schema,
            },
        }
