from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    """
    Paginación estándar para todas las vistas de listado.
    Permite personalizar el tamaño de página a través del parámetro 'page_size'.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
class SmallResultsSetPagination(PageNumberPagination):
    """
    Paginación para conjuntos de datos más pequeños.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50
    
class LargeResultsSetPagination(PageNumberPagination):
    """
    Paginación para conjuntos de datos más grandes.
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200 