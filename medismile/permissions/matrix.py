from __future__ import annotations

"""
Central permission matrix (resource -> action -> policy).

Each policy includes:
- roles: allowed role names
- ownership_required: bool (view supplies checker)
- university_scope_required: bool (view supplies checker)
- state_required: bool (view supplies checker)
"""

PERMISSION_MATRIX: dict[str, dict[str, dict]] = {
    # Messaging (case-scoped chat)
    "messaging.room": {
        "view": {
            "roles": {
                "tech_support",
                "university_admin",
                "supervisor",
                "student",
                "patient",
            },
            "ownership_required": True,
            "university_scope_required": False,
            "state_required": False,
        },
        "create": {
            "roles": {
                "student",
                "patient",
            },
            "ownership_required": True,
            "university_scope_required": False,
            "state_required": True,
        },
    },
    "messaging.message": {
        "view": {
            "roles": {
                "tech_support",
                "university_admin",
                "supervisor",
                "student",
                "patient",
            },
            "ownership_required": True,
            "university_scope_required": True,
            "state_required": False,
        },
        "send": {
            "roles": {
                "student",
                "patient",
            },
            "ownership_required": True,
            "university_scope_required": False,
            "state_required": True,
        },
    },
    # Notifications (read only for recipient / scoped)
    "notifications.notification": {
        "view": {
            "roles": {
                "patient",
                "student",
                "supervisor",
                "university_admin",
                "tech_support",
            },
            "ownership_required": True,
            "university_scope_required": True,
            "state_required": False,
        },
        "create": {
            "roles": {
                "student",
                "supervisor",
                "university_admin",
                "tech_support",
                "patient",  # limited types enforced in serializer
            },
            "ownership_required": False,
            "university_scope_required": False,
            "state_required": False,
        },
        "update": {
            "roles": {
                "patient",
                "student",
                "supervisor",
                "university_admin",
                "tech_support",
            },
            "ownership_required": True,
            "university_scope_required": True,
            "state_required": False,
        },
    },
    # Accounts / me endpoints (self only)
    "accounts.me": {
        "view": {
            "roles": {
                "patient",
                "student",
                "supervisor",
                "university_admin",
                "tech_support",
            },
            "ownership_required": True,
            "university_scope_required": False,
            "state_required": False,
        },
        "update": {
            "roles": {
                "patient",
                "student",
                "supervisor",
                "university_admin",
                "tech_support",
            },
            "ownership_required": True,
            "university_scope_required": False,
            "state_required": False,
        },
    },
}


def get_policy(resource: str, action: str) -> dict | None:
    resource_policies = PERMISSION_MATRIX.get(resource)
    if not resource_policies:
        return None
    return resource_policies.get(action)
