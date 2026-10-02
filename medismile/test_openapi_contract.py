# medismile/test_openapi_contract.py
"""
The committed OpenAPI document (docs/api/openapi.yaml) is the API contract the
mobile app and other clients are checked against. These tests fail when the
code and the committed document drift apart.

To refresh the document after an intentional API change:

    python manage.py spectacular --file docs/api/openapi.yaml --validate
"""
from pathlib import Path

import yaml
from django.conf import settings
from django.test import SimpleTestCase
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.validation import validate_schema

SPEC_PATH = Path(settings.BASE_DIR) / "docs" / "api" / "openapi.yaml"

# Paths the mobile app depends on for its core flows. Removing or renaming
# any of these is a breaking change for released apps.
MOBILE_CRITICAL_OPERATIONS = {
    ("/api/accounts/login/patient/", "post"),
    ("/api/accounts/login/student/", "post"),
    ("/api/accounts/login/supervisor/", "post"),
    ("/api/accounts/register/patient/", "post"),
    ("/api/ai/images/", "post"),
    ("/api/ai/diagnose/", "post"),
    ("/api/ai/my-analysis/", "get"),
    ("/api/cases/ai/create/", "post"),
    ("/api/cases/", "get"),
    ("/api/cases/{id}/", "get"),
    ("/api/cases/{case_id}/request-assignment/", "post"),
    ("/api/cases/{case_id}/supervisor-decision/", "post"),
    ("/api/cases/{case_id}/assignment-decision/", "post"),
    ("/api/messaging/threads/", "get"),
    ("/api/messaging/threads/{room_id}/messages/", "get"),
    ("/api/messaging/threads/{room_id}/messages/", "post"),
    ("/api/notifications/", "get"),
    ("/api/notifications/{id}/", "patch"),
    ("/api/notifications/create/", "post"),
    ("/api/appointments/", "get"),
    ("/api/appointments/{id}/complete/", "post"),
    ("/api/appointments/{id}/cancel/", "post"),
    ("/api/universities/", "get"),
}


def _generate():
    return SchemaGenerator().get_schema(request=None, public=True)


def _normalize(document):
    # Round-trip through YAML so both sides use identical scalar types.
    return yaml.safe_load(yaml.safe_dump(document, sort_keys=True, allow_unicode=True))


class OpenAPIContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.generated = _generate()
        cls.committed = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))

    def test_committed_spec_is_valid_openapi(self):
        validate_schema(self.committed)

    def test_committed_spec_matches_code(self):
        generated_paths = set(self.generated["paths"])
        committed_paths = set(self.committed["paths"])
        self.assertEqual(
            sorted(generated_paths - committed_paths),
            [],
            "Endpoints exist in code but not in docs/api/openapi.yaml — regenerate the spec.",
        )
        self.assertEqual(
            sorted(committed_paths - generated_paths),
            [],
            "docs/api/openapi.yaml documents endpoints that no longer exist — regenerate the spec.",
        )
        self.assertEqual(
            _normalize(self.generated),
            _normalize(self.committed),
            "docs/api/openapi.yaml is out of date — run: "
            "python manage.py spectacular --file docs/api/openapi.yaml --validate",
        )

    def test_mobile_critical_operations_are_documented(self):
        missing = [
            f"{method.upper()} {path}"
            for path, method in sorted(MOBILE_CRITICAL_OPERATIONS)
            if method not in self.committed["paths"].get(path, {})
        ]
        self.assertEqual(missing, [], "Mobile-critical operations missing from the contract.")
