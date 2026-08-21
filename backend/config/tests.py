import json
from unittest.mock import MagicMock, patch

import redis
from django.db.utils import OperationalError
from django.test import RequestFactory, SimpleTestCase

from .health import healthz


class HealthzViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get("/healthz/")

    def test_returns_200_when_database_and_redis_are_reachable(self):
        with patch("config.health.connections") as mock_connections, patch("config.health.redis") as mock_redis:
            mock_connections.__getitem__.return_value.cursor.return_value.execute = MagicMock()
            mock_redis.Redis.from_url.return_value.ping.return_value = True

            response = healthz(self.request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"status": "ok", "checks": {"database": "ok", "redis": "ok"}})

    def test_returns_503_when_database_is_unreachable(self):
        with patch("config.health.connections") as mock_connections, patch("config.health.redis") as mock_redis:
            mock_connections.__getitem__.return_value.cursor.side_effect = OperationalError("db down")
            mock_redis.Redis.from_url.return_value.ping.return_value = True

            response = healthz(self.request)

        self.assertEqual(response.status_code, 503)
        body = json.loads(response.content)
        self.assertEqual(body["status"], "error")
        self.assertIn("db down", body["checks"]["database"])
        self.assertEqual(body["checks"]["redis"], "ok")

    def test_returns_503_when_redis_is_unreachable(self):
        with patch("config.health.connections") as mock_connections, patch("config.health.redis") as mock_redis:
            mock_connections.__getitem__.return_value.cursor.return_value.execute = MagicMock()
            mock_redis.RedisError = redis.RedisError
            mock_redis.Redis.from_url.return_value.ping.side_effect = redis.RedisError("redis down")

            response = healthz(self.request)

        self.assertEqual(response.status_code, 503)
        body = json.loads(response.content)
        self.assertEqual(body["status"], "error")
        self.assertEqual(body["checks"]["database"], "ok")
        self.assertIn("redis down", body["checks"]["redis"])

    def test_returns_503_when_both_are_unreachable(self):
        with patch("config.health.connections") as mock_connections, patch("config.health.redis") as mock_redis:
            mock_connections.__getitem__.return_value.cursor.side_effect = OperationalError("db down")
            mock_redis.RedisError = redis.RedisError
            mock_redis.Redis.from_url.return_value.ping.side_effect = redis.RedisError("redis down")

            response = healthz(self.request)

        self.assertEqual(response.status_code, 503)
        body = json.loads(response.content)
        self.assertEqual(body["status"], "error")
        self.assertIn("db down", body["checks"]["database"])
        self.assertIn("redis down", body["checks"]["redis"])
