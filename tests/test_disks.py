import unittest
from unittest.mock import patch

from backend.services.disks import discover_disks


class DiskDiscoveryTests(unittest.TestCase):
    @patch("backend.services.disks.platform.system", return_value="Linux")
    def test_non_windows_platform_returns_unsupported_without_running_commands(self, _system):
        result = discover_disks()
        self.assertFalse(result["supported"])
        self.assertEqual(result["disks"], [])
        self.assertIn("Windows", result["message"])


if __name__ == "__main__":
    unittest.main()
