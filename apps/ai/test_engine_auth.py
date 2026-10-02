from unittest import mock

from django.test import SimpleTestCase, override_settings

from apps.ai.integrations import engine
from apps.ai.integrations.endpoints import get_ai_engines_config
from apps.ai.integrations.engine import AIEngineConfig


class EngineAuthTokenTests(SimpleTestCase):
    def test_no_token_sends_no_authorization_header(self):
        self.assertEqual(AIEngineConfig(base_url="http://x").request_headers(), {})

    def test_token_is_sent_as_bearer_and_hidden_from_repr(self):
        config = AIEngineConfig(base_url="http://x", auth_token="s3cret")
        self.assertEqual(config.request_headers(), {"Authorization": "Bearer s3cret"})
        self.assertNotIn("s3cret", repr(config))

    def test_post_json_forwards_headers(self):
        response = mock.Mock(status_code=200)
        response.json.return_value = {"ok": True}
        config = AIEngineConfig(base_url="http://x/analyze", auth_token="tok")
        with mock.patch.object(engine.requests, "post", return_value=response) as post:
            engine._post_json(config=config, path=None, payload={"a": 1})
        self.assertEqual(post.call_args.kwargs["headers"], {"Authorization": "Bearer tok"})

    @override_settings(
        AI_SYMPTOMS_URL="http://nlp.test",
        AI_VISION_URL="http://vision.test",
        AI_FUSION_URL="http://fusion.test",
        AI_VISION_AUTH_TOKEN="hf-read",
        AI_SYMPTOMS_AUTH_TOKEN="",
        AI_FUSION_AUTH_TOKEN="",
    )
    def test_settings_tokens_are_wired_per_engine(self):
        cfg = get_ai_engines_config()
        self.assertEqual(cfg.vision.auth_token, "hf-read")
        self.assertEqual(cfg.symptoms.auth_token, "")
        self.assertEqual(cfg.fusion.auth_token, "")
