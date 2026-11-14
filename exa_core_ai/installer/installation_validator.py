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

import json
import os


class ServiceValidator:
    """
    Checks if all runtimes and assets defined in service_config.json
    are correctly present on the local disk without requiring network connection.
    """

    def __init__(self, base_path):
        self.base_path = base_path
        # If the passed path is a file (e.g. local_config.json), use it directly as config source.
        # Otherwise treat it as a base directory and default to service_config.json.
        if os.path.isfile(base_path):
            self.config_path = base_path
        else:
            self.config_path = os.path.join(os.path.dirname(__file__), "../service_config.json")

    def get_resource_lists(self) -> dict:
        """
        Estrae le liste pure dei nomi per runtime, dipendenze e asset.
        Ottimo per popolare l interfaccia grafica di Blender nel metodo draw.
        """
        config = self._read_config()
        runtimes = []
        dependencies = []
        assets = []

        for rt_name, rt in config.get("runtimes", {}).items():
            if rt_name:
                runtimes.append(rt_name)

            for dep in rt.get("dependencies", []):
                # Estrae solo il nome pulito della dipendenza rimuovendo la versione se presente
                clean_name = dep.split("==")[0].split(">=")[0].strip()
                if clean_name:
                    dependencies.append(clean_name)

        # Handle both formats: list of dicts (service_config) or dict name->path (local_config)
        assets_raw = config.get("assets", [])
        if isinstance(assets_raw, dict):
            for ast_name in assets_raw.keys():
                if ast_name:
                    assets.append(ast_name)
        else:
            for ast in assets_raw:
                ast_name = ast.get("name")
                if ast_name:
                    assets.append(ast_name)

        return {
            "runtimes": runtimes,
            "dependencies": dependencies,
            "assets": assets
        }

    def _read_config(self):
        if not os.path.exists(self.config_path):
            return {}
        try:
            with open(self.config_path, "r", encoding="utf_8") as file:
                return json.load(file)
        except Exception:
            return {}

    def is_installed(self) -> bool:
        """
        Checks the existence of all expected files and folders.
        Returns True if the installation is complete, False otherwise.
        """
        config = self._read_config()
        if not config:
            return False


        target_folder_name = config.get("target_folder_name", "ExaCoreAi")
        global_target_dir = os.path.join(self.base_path, target_folder_name)

        if not os.path.exists(global_target_dir):
            return False

        # 1. Check Runtimes
        runtimes = config.get("runtimes", {})
        for rt_name, runtime in runtimes.items():
            subfolder = runtime.get("target_subfolder", rt_name)
            runtime_path = os.path.normpath(os.path.join(global_target_dir, subfolder))

            if not os.path.exists(runtime_path) or not os.path.isdir(runtime_path):
                return False

            if os.name == "nt":
                executables = ["python.exe", "python"]
            else:
                executables = ["bin/python3", "bin/python", "python3", "python"]

            executable_found = any(
                os.path.exists(os.path.join(runtime_path, exe)) for exe in executables
            )

            if not executable_found:
                return False

        # 2. Check Assets
        assets = config.get("assets", [])
        for asset in assets:
            subfolder = asset.get("target_subfolder", asset.get("name", ""))
            asset_path = os.path.normpath(os.path.join(global_target_dir, subfolder))

            if not os.path.exists(asset_path) or not os.path.isfile(asset_path):
                return False

        return True
