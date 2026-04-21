"""
RAGFlow API Python Client

A comprehensive Python client for interacting with the RAGFlow API.

Modules:
    - User: User authentication and management
    - Dataset: Dataset/knowledge base operations
    - Document: Document upload, parsing, and chunk management
    - Search: Search app creation and retrieval operations
    - Tenant: Team/tenant invitation and management

Exceptions:
    - RagflowAPIError: Base exception for all API errors
    - UnauthorizedError: Authentication failures (HTTP 401)
    - ForbiddenError: Access forbidden (HTTP 403)
    - NotFoundError: Resource not found (HTTP 404)
    - BadRequestError: Invalid request (HTTP 400)
    - ValidationError: Request data validation failures
    - ServerError: Server-side errors (HTTP 5xx)
    - TimeoutError: Request timeout errors

Example:
    >>> from ragflow_api import RagflowAPI
    >>> api = RagflowAPI("http://localhost:9380")
    >>> token = await api.user.get_token("user@example.com", "password")
"""

from .base import (
    BadRequestError,
    ForbiddenError,
    NotFoundError,
    RagflowAPIBase,
    RagflowAPIError,
    ServerError,
    TimeoutError,
    UnauthorizedError,
    ValidationError,
)
from .Dataset.dataset_api import DatasetRagflowAPI
from .Document.document_api import DocumentRagflowAPI
from .ragflow_api import RagflowAPI
from .Search.search_api import SearchRagflowAPI
from .Tenant.tenant_api import TenantRagflowAPI
from .User.user_api import UserRagflowAPI

__all__ = [
    # Unified API
    "RagflowAPI",
    # Base classes and exceptions
    "RagflowAPIBase",
    "RagflowAPIError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "BadRequestError",
    "ValidationError",
    "ServerError",
    "TimeoutError",
    # API modules
    "UserRagflowAPI",
    "DatasetRagflowAPI",
    "DocumentRagflowAPI",
    "SearchRagflowAPI",
    "TenantRagflowAPI",
]

__version__ = "1.0.0"
