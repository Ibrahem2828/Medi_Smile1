# medismile/openapi.py
"""
Shared OpenAPI response components for views that build their responses by
hand (APIView / @api_view). They exist only to document the contract in
docs/api/openapi.yaml; runtime behaviour does not depend on them.
"""
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, inline_serializer
from rest_framework import serializers

# ------------------------------------------------------------------
# Generic envelopes
# ------------------------------------------------------------------
ErrorEnvelope = inline_serializer(
    name="ErrorEnvelope",
    fields={
        "status": serializers.CharField(default="error"),
        "message": serializers.CharField(),
        "errors": serializers.JSONField(allow_null=True, required=False),
    },
)

DetailMessage = inline_serializer(
    name="DetailMessage",
    fields={"detail": serializers.CharField()},
)


def success_envelope(name: str, data_field: serializers.Field) -> serializers.Serializer:
    return inline_serializer(
        name=name,
        fields={
            "status": serializers.CharField(default="success"),
            "message": serializers.CharField(required=False),
            "data": data_field,
        },
    )


GenericSuccess = success_envelope("GenericSuccess", serializers.JSONField(allow_null=True))

# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------
LoginUser = inline_serializer(
    name="LoginUser",
    fields={
        "id": serializers.UUIDField(),
        "email": serializers.EmailField(),
        "username": serializers.CharField(),
        "first_name": serializers.CharField(),
        "last_name": serializers.CharField(),
        "role": serializers.ChoiceField(
            choices=["patient", "student", "supervisor", "university_admin", "tech_support"]
        ),
        "role_id": serializers.UUIDField(allow_null=True),
        "fcm_token": serializers.CharField(allow_null=True),
        "is_active": serializers.BooleanField(),
        "created_at": serializers.DateTimeField(),
        "updated_at": serializers.DateTimeField(),
    },
)

LoginResponse = inline_serializer(
    name="LoginResponse",
    fields={
        "detail": serializers.CharField(),
        "tokens": inline_serializer(
            name="JWTPair",
            fields={"refresh": serializers.CharField(), "access": serializers.CharField()},
        ),
        "user": LoginUser,
    },
)

# ------------------------------------------------------------------
# AI
# ------------------------------------------------------------------
MyAnalysisResponse = inline_serializer(
    name="MyAnalysisResponse",
    fields={
        "case_id": serializers.UUIDField(),
        "status": serializers.CharField(),
        "ai_summary": serializers.JSONField(),
        "patient_report": serializers.JSONField(),
        "last_updated": serializers.DateTimeField(),
    },
)

ProcessingResponse = inline_serializer(
    name="ProcessingResponse",
    fields={"status": serializers.CharField(default="processing"), "message": serializers.CharField()},
)

AIEnginesHealth = inline_serializer(
    name="AIEnginesHealth",
    fields={"engines": serializers.JSONField()},
)

def exclude_slashless_aliases(endpoints):
    """
    drf-spectacular preprocessing hook: drop compatibility aliases registered
    without a trailing slash (e.g. ``me/university-selection``) so each
    operation appears once, under its canonical path.
    """
    return [
        (path, path_regex, method, callback)
        for (path, path_regex, method, callback) in endpoints
        if path.endswith("/")
    ]


BINARY_IMAGE = OpenApiResponse(
    response=OpenApiTypes.BINARY,
    description="The stored (sanitised) image bytes; Content-Type is image/jpeg, image/png or image/webp.",
)
