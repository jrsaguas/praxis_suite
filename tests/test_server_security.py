import unittest
from pathlib import Path
import tempfile
import json

import server
from security_utils import safe_child_path, safe_filename


class RequestLimitTests(unittest.TestCase):
    def test_limit_rejects_oversized_content_length(self):
        class Headers(dict):
            def get(self, key, default=None):
                return super().get(key, default)
        class R:
            headers = Headers({"Content-Length": str(server.MAX_REQUEST_BYTES + 1)})
            rfile = None
            def _read_body(self):
                return server.PraxisRequestHandler._read_body(self)
        with self.assertRaises(ValueError):
            R()._read_body()


class PathSafetyTests(unittest.TestCase):
    def test_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                safe_child_path(root, "..", "secret.txt")

    def test_filename_is_basename(self):
        self.assertEqual(safe_filename("../../secret.txt"), "secret.txt")


if __name__ == "__main__":
    unittest.main()
