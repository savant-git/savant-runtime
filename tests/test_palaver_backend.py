import importlib
import os
import unittest
from unittest import mock


class PalaverBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.environment = mock.patch.dict(
            os.environ,
            {
                "PALAVER_API_TOKEN": "test-token",
                "PALAVER_ALLOWED_ORIGINS": "https://allowed.example",
            },
            clear=True,
        )
        cls.environment.start()
        cls.backend = importlib.import_module("palaver_voice_backend")
        cls.client = cls.backend.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.environment.stop()

    def auth(self):
        return {"Authorization": "Bearer test-token"}

    def test_health_is_minimal_and_public(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"ok": True})

    def test_message_requires_authentication(self):
        response = self.client.post("/api/palaver", json={"text": "hello"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], "unauthorized")

    def test_offline_message_has_deterministic_fallback(self):
        response = self.client.post(
            "/api/palaver", json={"text": "palver"}, headers=self.auth()
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["corrected"], "palaver")
        self.assertNotIn("API error", body["reply"])

    def test_rejects_non_object_and_non_string_json(self):
        array = self.client.post("/api/palaver", json=[], headers=self.auth())
        number = self.client.post(
            "/api/palaver", json={"text": 42}, headers=self.auth()
        )
        self.assertEqual(array.status_code, 400)
        self.assertEqual(number.status_code, 400)

    def test_rejects_wrong_content_type(self):
        response = self.client.post(
            "/api/palaver", data="hello", headers=self.auth()
        )
        self.assertEqual(response.status_code, 415)

    def test_cors_allows_only_configured_origin(self):
        allowed = self.client.get(
            "/api/health", headers={"Origin": "https://allowed.example"}
        )
        denied = self.client.get(
            "/api/health", headers={"Origin": "https://denied.example"}
        )
        self.assertEqual(
            allowed.headers.get("Access-Control-Allow-Origin"),
            "https://allowed.example",
        )
        self.assertIsNone(denied.headers.get("Access-Control-Allow-Origin"))


if __name__ == "__main__":
    unittest.main()
