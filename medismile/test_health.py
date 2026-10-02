from django.test import TestCase


class HealthEndpointTests(TestCase):
    def test_liveness_does_not_require_dependencies(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_readiness_requires_a_usable_database(self):
        response = self.client.get("/readyz/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")
