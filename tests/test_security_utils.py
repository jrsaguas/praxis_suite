import tempfile
import unittest
from pathlib import Path

from security_utils import safe_child_path, safe_filename, validate_component


class SecurityUtilsTests(unittest.TestCase):
    def test_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                safe_child_path(root, "..", "secret.txt")
            with self.assertRaises(ValueError):
                safe_child_path(root, "../outside")

    def test_filename_is_basename(self):
        self.assertEqual(safe_filename("../../secret.txt"), "secret.txt")
        self.assertEqual(safe_filename(r"..\secret.txt"), "secret.txt")

    def test_valid_component(self):
        self.assertEqual(validate_component("chat_001"), "chat_001")


if __name__ == "__main__":
    unittest.main()
