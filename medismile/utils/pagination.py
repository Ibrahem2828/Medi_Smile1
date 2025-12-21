from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination for Medismile APIs.

    Features:
    - Consistent response format
    - Client-controlled page size (within limits)
    - Clear metadata for frontend & mobile apps
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        """
        Customize paginated response format.
        """
        return Response(
            {
                "status": "success",
                "message": _("تم جلب البيانات بنجاح."),
                "pagination": {
                    "count": self.page.paginator.count,
                    "page": self.page.number,
                    "page_size": self.get_page_size(self.request),
                    "total_pages": self.page.paginator.num_pages,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
                "data": data,
            }
        )
