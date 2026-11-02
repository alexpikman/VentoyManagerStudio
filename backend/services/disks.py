"""Read-only discovery of physical disks and their partitions on Windows.

This module deliberately contains no disk-writing, formatting, or partition-editing
commands. It is safe to call from the application's initial dashboard.
"""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
from typing import Any


POWERSHELL_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$items = @(
    Get-Disk | ForEach-Object {
        $disk = $_
        $partitions = @(
            Get-Partition -DiskNumber $disk.Number -ErrorAction SilentlyContinue |
            ForEach-Object {
                $partition = $_
                $volume = $partition | Get-Volume -ErrorAction SilentlyContinue
                [pscustomobject]@{
                    PartitionNumber = $partition.PartitionNumber
                    DriveLetter = if ($volume) { [string]$volume.DriveLetter } else { '' }
                    Label = if ($volume) { [string]$volume.FileSystemLabel } else { '' }
                    FileSystem = if ($volume) { [string]$volume.FileSystem } else { '' }
                    Size = [int64]$partition.Size
                    Type = [string]$partition.Type
                    IsSystem = [bool]$partition.IsSystem
                    IsBoot = [bool]$partition.IsBoot
                }
            }
        )
        [pscustomobject]@{
            Number = [int]$disk.Number
            FriendlyName = [string]$disk.FriendlyName
            SerialNumber = [string]$disk.SerialNumber
            BusType = [string]$disk.BusType
            PartitionStyle = [string]$disk.PartitionStyle
            OperationalStatus = (@($disk.OperationalStatus) -join ', ')
            HealthStatus = [string]$disk.HealthStatus
            Size = [int64]$disk.Size
            IsBoot = [bool]$disk.IsBoot
            IsSystem = [bool]$disk.IsSystem
            IsReadOnly = [bool]$disk.IsReadOnly
            Partitions = $partitions
        }
    }
)
ConvertTo-Json -InputObject $items -Depth 6 -Compress
"""


class DiskDiscoveryError(RuntimeError):
    """Raised when Windows disk discovery cannot be completed."""


def discover_disks() -> dict[str, Any]:
    """Return physical disk and partition information without modifying anything."""
    if platform.system() != "Windows":
        return {
            "supported": False,
            "message": "Обнаружение физических дисков доступно в Windows 10/11.",
            "disks": [],
        }

    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell:
        raise DiskDiscoveryError("Не найден Windows PowerShell.")

    try:
        completed = subprocess.run(
            [
                powershell,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                POWERSHELL_SCRIPT,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=25,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as exc:
        raise DiskDiscoveryError("Windows не ответила на запрос списка дисков за 25 секунд.") from exc
    except OSError as exc:
        raise DiskDiscoveryError(f"Не удалось запустить PowerShell: {exc}") from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or "PowerShell вернул неизвестную ошибку."
        raise DiskDiscoveryError(detail[-1200:])

    output = completed.stdout.strip()
    if not output:
        return {"supported": True, "message": "Физические диски не обнаружены.", "disks": []}

    try:
        parsed = json.loads(output)
    except json.JSONDecodeError as exc:
        raise DiskDiscoveryError("Не удалось разобрать ответ Windows о физических дисках.") from exc

    # PowerShell emits an object for one result and an array for multiple results.
    disks = parsed if isinstance(parsed, list) else [parsed]
    return {
        "supported": True,
        "message": f"Обнаружено физических дисков: {len(disks)}.",
        "disks": disks,
    }
