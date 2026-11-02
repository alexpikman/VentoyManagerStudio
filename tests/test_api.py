import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from backend.server import AppHandler


class ApiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_health_endpoint(self):
        with urlopen(f"{self.base_url}/api/health", timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["version"], "0.1.0")

    def test_system_endpoint(self):
        with urlopen(f"{self.base_url}/api/system", timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
        self.assertIn("platform", payload)
        self.assertIn("python", payload)
        self.assertIn("supported_platform", payload)

    def test_frontend_entrypoint_is_served(self):
        with urlopen(f"{self.base_url}/", timeout=3) as response:
            html = response.read().decode("utf-8")
        self.assertIn("Ventoy Manager Studio", html)
        self.assertIn("/assets/app.js", html)

    def test_write_methods_are_disabled_in_foundation(self):
        request = Request(f"{self.base_url}/api/health", method="POST", data=b"{}")
        with self.assertRaises(HTTPError) as error:
            urlopen(request, timeout=3)
        self.assertEqual(error.exception.code, 405)
        payload = json.loads(error.exception.read().decode("utf-8"))
        self.assertTrue(payload["read_only"])


if __name__ == "__main__":
    unittest.main()
