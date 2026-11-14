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
#   Copyright 2019 2026(C) Andrea Donati
#


class DependencyRegistry:
    """
    Centralized registry to map hardware profiles to specific pip dependencies and URLs.
    This replaces hardcoded logic and scales to PyTorch, TensorFlow, xFormers etc.
    """

    @staticmethod
    def get_install_instructions(profile, dependency_base_name):
        registry = {
            "onnxruntime": {
                "windows": {
                    "cuda": {"pkg": "onnxruntime_gpu", "extra_args": []},
                    "directml": {"pkg": "onnxruntime_directml", "extra_args": []},
                    "cpu": {"pkg": "onnxruntime", "extra_args": []}
                },
                "linux": {
                    "cuda": {"pkg": "onnxruntime_gpu", "extra_args": []},
                    "rocm": {"pkg": "onnxruntime_rocm", "extra_args": []},
                    "openvino": {"pkg": "onnxruntime_openvino", "extra_args": []},
                    "cpu": {"pkg": "onnxruntime", "extra_args": []}
                },
                "macos": {
                    "silicon": {"pkg": "onnxruntime_silicon", "extra_args": []},
                    "cpu": {"pkg": "onnxruntime", "extra_args": []}
                }
            },
            "pytorch": {
                "windows": {
                    "cuda": {"pkg": "torch torchvision torchaudio",
                             "extra_args": ["--index-url", "https://download.pytorch.org/whl/cu121"]},
                    "directml": {"pkg": "torch torchvision torchaudio", "extra_args": []},
                    "cpu": {"pkg": "torch torchvision torchaudio", "extra_args": []}
                },
                "linux": {
                    "cuda": {"pkg": "torch torchvision torchaudio",
                             "extra_args": ["--index-url", "https://download.pytorch.org/whl/cu121"]},
                    "rocm": {"pkg": "torch torchvision torchaudio",
                             "extra_args": ["--index-url", "https://download.pytorch.org/whl/rocm60"]},
                    "openvino": {"pkg": "torch torchvision torchaudio", "extra_args": []},
                    "cpu": {"pkg": "torch torchvision torchaudio", "extra_args": []}
                },
                "macos": {
                    "silicon": {"pkg": "torch torchvision torchaudio", "extra_args": []},
                    "cpu": {"pkg": "torch torchvision torchaudio", "extra_args": []}
                }
            }
        }

        os_data = registry.get(dependency_base_name, {}).get(profile.os_type, {})
        result = os_data.get(profile.compute_backend, os_data.get("cpu"))

        return result