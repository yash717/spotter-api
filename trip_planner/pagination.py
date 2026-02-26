"""
Custom pagination with results + pagination object (count, page, page_size, next, previous, has_next, has_prev).
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class SpotterPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "results": data,
                "pagination": {
                    "count": self.page.paginator.count,
                    "page": self.page.number,
                    "page_size": self.get_page_size(self.request),
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                    "has_next": self.page.has_next(),
                    "has_prev": self.page.has_previous(),
                },
            }
        )
