import re

from django.conf import settings
from django.test import SimpleTestCase, override_settings

PROD_ORIGIN = "https://website.medismile.xn--mgbaab0cxheq.tech"

CORS_TEST_SETTINGS = dict(
    SECURE_SSL_REDIRECT=False,
    CORS_ALLOW_ALL_ORIGINS=False,
    CORS_ALLOWED_ORIGINS=[PROD_ORIGIN],
    CORS_ALLOWED_ORIGIN_REGEXES=[settings.LOCALHOST_ORIGIN_REGEX],
)


class LocalhostRegexTests(SimpleTestCase):
    def test_accepts_only_real_localhost_origins(self):
        pattern = re.compile(settings.LOCALHOST_ORIGIN_REGEX)
        accepted = [
            "http://localhost", "http://localhost:3000", "http://localhost:5173", "https://localhost:8443",
            "http://127.0.0.1:5500", "http://127.0.0.1", "http://[::1]:4200",
        ]
        rejected = [
            "http://localhost.evil.com", "http://localhostevil", "http://evil.com/localhost",
            "http://localhost:3000.evil.com", "http://127.0.0.1.evil.com", "http://127.0.0.10:3000",
            "ftp://localhost", "null", "https://example.com", "http://localhost:99999999",
        ]
        for origin in accepted:
            with self.subTest(origin=origin):
                self.assertIsNotNone(pattern.match(origin))
        for origin in rejected:
            with self.subTest(origin=origin):
                self.assertIsNone(pattern.match(origin))


@override_settings(**CORS_TEST_SETTINGS)
class PreflightTests(SimpleTestCase):
    def preflight(self, origin, path="/api/accounts/login/patient/", headers="authorization,content-type", method="POST"):
        return self.client.options(
            path,
            HTTP_ORIGIN=origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD=method,
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS=headers,
        )

    def test_localhost_front_end_can_call_the_api(self):
        for origin in ("http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:4200"):
            with self.subTest(origin=origin):
                response = self.preflight(origin)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Access-Control-Allow-Origin"], origin)
                allowed = response["Access-Control-Allow-Headers"].lower()
                self.assertIn("authorization", allowed)
                self.assertIn("content-type", allowed)
                self.assertIn("accept-language", allowed)

    def test_all_rest_verbs_are_allowed(self):
        methods = self.preflight("http://localhost:3000", method="PATCH")["Access-Control-Allow-Methods"]
        for verb in ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
            self.assertIn(verb, methods)

    def test_preflight_is_cached(self):
        self.assertEqual(self.preflight("http://localhost:3000")["Access-Control-Max-Age"], "86400")

    def test_production_website_is_still_allowed(self):
        self.assertEqual(self.preflight(PROD_ORIGIN)["Access-Control-Allow-Origin"], PROD_ORIGIN)

    def test_unknown_and_look_alike_origins_get_no_cors_headers(self):
        for origin in ("https://evil.example", "http://localhost.evil.com", "null"):
            with self.subTest(origin=origin):
                self.assertNotIn("Access-Control-Allow-Origin", self.preflight(origin))

    def test_credentials_are_not_enabled(self):
        self.assertNotIn("Access-Control-Allow-Credentials", self.preflight("http://localhost:3000"))

    def test_actual_responses_carry_cors_headers_and_expose_downloads(self):
        response = self.client.get("/health/", HTTP_ORIGIN="http://localhost:5173")
        self.assertEqual(response["Access-Control-Allow-Origin"], "http://localhost:5173")
        self.assertIn("Content-Disposition", response["Access-Control-Expose-Headers"])

    def test_error_responses_also_carry_cors_headers(self):
        response = self.client.get("/definitely-not-a-route/", HTTP_ORIGIN="http://localhost:3000")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response["Access-Control-Allow-Origin"], "http://localhost:3000")

    @override_settings(CORS_ALLOWED_ORIGIN_REGEXES=[])
    def test_localhost_can_be_switched_off_for_production(self):
        self.assertNotIn("Access-Control-Allow-Origin", self.preflight("http://localhost:3000"))
        self.assertEqual(self.preflight(PROD_ORIGIN)["Access-Control-Allow-Origin"], PROD_ORIGIN)
