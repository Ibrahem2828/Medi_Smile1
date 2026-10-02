"""Rate-limit keys that are safe to use before a user is authenticated."""
from __future__ import annotations

import hashlib

from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    """Limit login attempts by both source IP and requested account.

    IP-only limits make a shared university network easy to exhaust, while an
    account-only limit enables distributed guessing. The key is hashed so the
    cache never stores a raw email address.
    """

    scope = "login"

    def get_cache_key(self, request, view):
        payload = getattr(request, "data", {}) or {}
        identifier = str(payload.get("email") or payload.get("username") or "").strip().lower()
        fingerprint = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:24]
        return self.cache_format % {
            "scope": self.scope,
            "ident": f"{self.get_ident(request)}:{fingerprint}",
        }
