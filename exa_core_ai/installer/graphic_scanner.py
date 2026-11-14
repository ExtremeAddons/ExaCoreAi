#   #
#    This program is free software; you can redistribute it and/or
#    modify it under the terms of the GNU General Public License
#    as published by the Free Software Foundation; either version
#    of the License, or (at your option) any later version.
#   #
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#   #
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software Foundation,
#    Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#   #
#   Copyright 2019-2026(C) Andrea Donati


import platform
import ctypes
import subprocess
import os


class HardwareProfile:
    """
    Standardized representation of the user system.
    """

    def __init__(self, os_type, compute_backend):
        self.os_type = os_type
        self.compute_backend = compute_backend


class ProGraphicScanner:
    """
    Enterprise hardware scanner.
    Returns a standardized HardwareProfile instead of specific dependency names.
    """

    @staticmethod
    def _run_system_query(cmd_list):
        try:
            kwargs = {"capture_output": True, "text": True}
            if os.name == "nt":
                kwargs["creationflags"] = 0x08000000
            result = subprocess.run(cmd_list, **kwargs)
            return result.stdout.lower()
        except Exception:
            return ""

    @classmethod
    def _scan_windows(cls):
        has_nvidia = False
        has_amd = False
        has_intel = False

        try:
            ctypes.windll.LoadLibrary("nvcuda.dll")
            has_nvidia = True
        except OSError:
            pass

        gpu_info = cls._run_system_query(["wmic", "path", "win32_VideoController", "get", "name"])

        if "nvidia" in gpu_info:
            has_nvidia = True
        if "amd" in gpu_info or "radeon" in gpu_info:
            has_amd = True
        if "intel" in gpu_info:
            has_intel = True

        if has_nvidia:
            return HardwareProfile("windows", "cuda")
        if has_amd or has_intel:
            return HardwareProfile("windows", "directml")

        return HardwareProfile("windows", "cpu")

    @classmethod
    def _scan_linux(cls):
        has_nvidia = False
        has_amd = False
        has_intel = False

        try:
            ctypes.cdll.LoadLibrary("libcuda.so.1")
            has_nvidia = True
        except OSError:
            try:
                ctypes.cdll.LoadLibrary("libcuda.so")
                has_nvidia = True
            except OSError:
                pass

        gpu_info = cls._run_system_query(["lspci"])

        if "nvidia" in gpu_info:
            has_nvidia = True
        if "amd" in gpu_info or "radeon" in gpu_info:
            has_amd = True
        if "intel" in gpu_info:
            has_intel = True

        if has_nvidia:
            return HardwareProfile("linux", "cuda")
        if has_amd:
            return HardwareProfile("linux", "rocm")
        if has_intel:
            return HardwareProfile("linux", "openvino")

        return HardwareProfile("linux", "cpu")

    @classmethod
    def _scan_macos(cls):
        machine = platform.machine().lower()
        if "arm64" in machine:
            return HardwareProfile("macos", "silicon")
        return HardwareProfile("macos", "cpu")

    @classmethod
    def get_system_profile(cls, force_preference=None):
        """
        Returns the hardware profile.
        Allowed force_preference values: 'cuda', 'rocm', 'directml', 'openvino', 'silicon', 'cpu'
        """
        sys_name = platform.system().lower()
        os_mapped = "macos" if sys_name == "darwin" else sys_name

        if force_preference:
            return HardwareProfile(os_mapped, force_preference.lower())

        if os_mapped == "windows":
            return cls._scan_windows()
        if os_mapped == "linux":
            return cls._scan_linux()
        if os_mapped == "macos":
            return cls._scan_macos()

        return HardwareProfile("unknown", "cpu")


