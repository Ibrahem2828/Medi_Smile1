from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.utils.translation import gettext_lazy as _
from django.conf import settings

import logging
import traceback

logger = logging.getLogger(__name__)


# ============================================================
# Custom API Exception Handler
# ============================================================

def custom_exception_handler(exc, context):
    """
    Global exception handler for Medismile APIs.

    أهدافه:
    - توحيد شكل الأخطاء
    - إخفاء التفاصيل الحساسة
    - تسهيل التعامل مع الأخطاء من Frontend / Mobile
    """

    # ---------------------------------------------
    # Call DRF default handler first
    # ---------------------------------------------
    response = exception_handler(exc, context)

    # ---------------------------------------------
    # If DRF handled the exception
    # ---------------------------------------------
    if response is not None:
        data = {
            "status": "error",
            "message": _get_error_message(response),
            "errors": response.data,
        }

        response.data = data
        return response

    # ---------------------------------------------
    # Unhandled exceptions (500)
    # ---------------------------------------------
    logger.exception("Unhandled exception occurred", exc_info=exc)

    expose_details = bool(getattr(settings, "EXPOSE_ERROR_DETAILS", False))
    details = None
    if expose_details:
        details = {
            "type": exc.__class__.__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }

    return Response(
        {
            "status": "error",
            "message": _("حدث خطأ غير متوقع. يرجى المحاولة لاحقًا."),
            "errors": details,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# ============================================================
# Helper functions
# ============================================================

def _get_error_message(response):
    """
    Extract a human-readable error message from DRF response.
    """
    if isinstance(response.data, dict):
        if "detail" in response.data:
            return response.data.get("detail")
        if "error" in response.data:
            return response.data.get("error")

    return _("طلب غير صالح.")


# ============================================================
# Custom Business Exceptions (optional, extensible)
# ============================================================

class BusinessLogicException(Exception):
    """
    Base exception for business rule violations.
    """
    default_message = _("حدث خطأ في منطق العمل.")

    def __init__(self, message=None):
        self.message = message or self.default_message
        super().__init__(self.message)


class PermissionViolation(BusinessLogicException):
    default_message = _("ليس لديك الصلاحية لتنفيذ هذا الإجراء.")


class InvalidOperation(BusinessLogicException):
    default_message = _("لا يمكن تنفيذ هذا الإجراء في الحالة الحالية.")
