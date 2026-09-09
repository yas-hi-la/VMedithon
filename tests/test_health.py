import json
from http.client import HTTPConnection
import threading
import unittest

from backend.api.server import create_server
from backend.config.settings import Settings


class HealthEndpointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = create_server(Settings(host="127.0.0.1", port=0))
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()

    def request(self, path: str) -> tuple[int, dict[str, str]]:
        connection = HTTPConnection("127.0.0.1", self.port)
        connection.request("GET", path)
        response = connection.getresponse()
        payload = json.loads(response.read())
        connection.close()
        return response.status, payload

    def test_health_endpoint_returns_ok(self) -> None:
        status, payload = self.request("/health")

        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})

    def test_unknown_route_returns_not_found(self) -> None:
        status, payload = self.request("/unknown")

        self.assertEqual(status, 404)
        self.assertEqual(payload, {"error": "Not Found"})


if __name__ == "__main__":
    unittest.main()
