import json
import subprocess
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

    @patch("backend.services.disks.subprocess.run")
    @patch("backend.services.disks.shutil.which", return_value="powershell.exe")
    @patch("backend.services.disks.platform.system", return_value="Windows")
    def test_windows_discovery_parses_single_disk(self, _system, _which, run):
        sample = [{"Number": 2, "FriendlyName": "USB Test Drive", "Size": 16000000000, "Partitions": []}]
        run.return_value = subprocess.CompletedProcess([], 0, json.dumps(sample), "")
        result = discover_disks()
        self.assertTrue(result["supported"])
        self.assertEqual(len(result["disks"]), 1)
        self.assertEqual(result["disks"][0]["FriendlyName"], "USB Test Drive")
        self.assertEqual(run.call_args.kwargs["timeout"], 25)


if __name__ == "__main__":
    unittest.main()
