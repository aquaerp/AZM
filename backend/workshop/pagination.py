from rest_framework.pagination import PageNumberPagination


class OptionalPageNumberPagination(PageNumberPagination):
    """Paginate large lists when the caller explicitly requests a page."""

    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 500

    def paginate_queryset(self, queryset, request, view=None):
        if "page" not in request.query_params and self.page_size_query_param not in request.query_params:
            return None
        return super().paginate_queryset(queryset, request, view)
