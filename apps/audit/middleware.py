# apps/audit/middleware.py
from django.utils.deprecation import MiddlewareMixin

from .models import AuditAction
from .services import log_audit_event


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware creates audit logs for meaningful state-changing operations.

    - Logs authenticated user actions only
    - Skips 4xx/5xx
    - Avoid noisy GET/HEAD/OPTIONS by default
    - Must NEVER break request lifecycle
    """

    SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

    def process_request(self, request):
        request._audit_context = {
            "ip_address": self.get_client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            "method": request.method,
            "path": request.path,
        }
        return None

    def process_response(self, request, response):
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            return response

        if response.status_code >= 400:
            return response

        ctx = getattr(request, "_audit_context", {})
        method = ctx.get("method", request.method)
        path = ctx.get("path", request.path)

        action = self.resolve_action(method, path)
        if not action:
            return response

        # University scope: unified approach (matches the whole project)
        university = getattr(user, "university", None)
        if university is None and getattr(user, "university_id", None):
            # If only FK id exists, Django can still fetch lazily if needed
            university = user.university

        try:
            log_audit_event(
                user=user,
                university=university,
                action=action,
                description=f"{method} {path}",
                metadata={
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                },
                ip_address=ctx.get("ip_address"),
                user_agent=ctx.get("user_agent"),
            )
        except Exception:
            # Audit must never break application behavior
            pass

        return response

    # =====================================================
    # Helpers
    # =====================================================

    def resolve_action(self, method: str, path: str):
        # Authentication
        if path.endswith("/login/") and method == "POST":
            return AuditAction.LOGIN
        if path.endswith("/logout/") and method == "POST":
            return AuditAction.LOGOUT

        # Custom endpoints
        if path.endswith("/submit/") and method == "POST":
            return AuditAction.SUBMIT
        if path.endswith("/finalize/") and method == "POST":
            return AuditAction.FINALIZE
        if "/confirm/" in path:
            return AuditAction.CONFIRM
        if "/cancel/" in path:
            return AuditAction.CANCEL
        if "/complete/" in path:
            return AuditAction.COMPLETE

        # File actions
        if "/download/" in path:
            return AuditAction.DOWNLOAD
        if method == "POST" and "/attachments/" in path:
            return AuditAction.UPLOAD

        # CRUD-ish actions by method
        if method == "POST":
            return AuditAction.CREATE
        if method in ("PUT", "PATCH"):
            return AuditAction.UPDATE
        if method == "DELETE":
            return AuditAction.DELETE

        # Avoid GET noise
        if method in self.SAFE_METHODS:
            return None

        return AuditAction.OTHER

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
