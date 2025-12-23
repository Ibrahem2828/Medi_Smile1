# apps/audit/middleware.py

from django.utils.deprecation import MiddlewareMixin
from django.contrib.contenttypes.models import ContentType

from .models import AuditLog, AuditAction


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware responsible for creating audit logs for critical user actions.

    Philosophy:
    - Log authenticated user actions only
    - Focus on meaningful state-changing operations
    - Keep logs immutable and structured
    """

    SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

    def process_request(self, request):
        """
        Capture request metadata early.
        """
        request._audit_context = {
            "ip_address": self.get_client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            "method": request.method,
            "path": request.path,
        }
        return None

    def process_response(self, request, response):
        """
        Create audit log entry after response is processed.
        """
        user = getattr(request, "user", None)

        # Log authenticated users only
        if not user or not user.is_authenticated:
            return response

        # Skip unsuccessful responses
        if response.status_code >= 400:
            return response

        method = request.method
        path = request.path

        action = self.resolve_action(method, path)
        if not action:
            return response

        description = self.build_description(method, path)

        # Resolve university scope (if available)
        university = None
        if hasattr(user, "student_profile") and user.student_profile.university:
            university = user.student_profile.university
        elif hasattr(user, "supervisor_profile") and user.supervisor_profile.university:
            university = user.supervisor_profile.university
        elif hasattr(user, "universityadmin_profile") and user.universityadmin_profile.university:
            university = user.universityadmin_profile.university

        context = getattr(request, "_audit_context", {})

        # Create immutable audit log
        try:
            AuditLog.objects.create(
                user=user,
                university=university,
                action=action,
                description=description,
                ip_address=context.get("ip_address"),
                user_agent=context.get("user_agent"),
                metadata={
                    "method": context.get("method"),
                    "path": context.get("path"),
                    "status_code": response.status_code,
                },
            )
        except Exception:
            # Audit must NEVER break the request lifecycle
            pass

        return response

    # =====================================================
    # Helpers
    # =====================================================

    def resolve_action(self, method: str, path: str):
        """
        Determine audit action based on HTTP method and endpoint.
        """

        # Authentication
        if path.endswith("/login/") and method == "POST":
            return AuditAction.LOGIN
        if path.endswith("/logout/") and method == "POST":
            return AuditAction.LOGOUT

        # Create
        if method == "POST":
            if "/evaluations/" in path:
                return AuditAction.CREATE
            if "/cases/" in path:
                return AuditAction.CREATE
            if "/appointments/" in path:
                return AuditAction.CREATE
            if "/attachments/" in path:
                return AuditAction.UPLOAD
            if "/community/" in path:
                return AuditAction.CREATE
            if "/support/" in path:
                return AuditAction.CREATE

        # Update
        if method in ("PUT", "PATCH"):
            if "/evaluations/" in path:
                return AuditAction.UPDATE
            if "/cases/" in path:
                return AuditAction.UPDATE
            if "/appointments/" in path:
                return AuditAction.UPDATE
            if "/community/" in path:
                return AuditAction.UPDATE

        # Delete
        if method == "DELETE":
            if "/attachments/" in path:
                return AuditAction.DELETE
            if "/community/" in path:
                return AuditAction.DELETE

        # Custom actions
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

        # Downloads
        if "/download/" in path:
            return AuditAction.DOWNLOAD

        # Avoid logging noisy GET requests
        if method in self.SAFE_METHODS:
            return None

        return AuditAction.OTHER

    def build_description(self, method: str, path: str) -> str:
        """
        Human-readable description.
        """
        return f"{method} {path}"

    def get_client_ip(self, request):
        """
        Extract client IP address considering proxies.
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
