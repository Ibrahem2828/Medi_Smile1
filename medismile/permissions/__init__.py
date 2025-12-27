# Centralized permission utilities for MediSmile.
# Expose matrix/checker/DRF integration.

from .matrix import PERMISSION_MATRIX, get_policy
from .checker import has_access, PermissionDecision
from .drf import MatrixPermission

__all__ = [
    "PERMISSION_MATRIX",
    "get_policy",
    "has_access",
    "PermissionDecision",
    "MatrixPermission",
]
