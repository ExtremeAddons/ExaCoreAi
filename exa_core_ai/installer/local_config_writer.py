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


class LocalConfigWriter:
    """
    Writes the final local configuration file after a successful installation.
    Records runtime executables, their installed dependencies, and asset paths.
    """

    def __init__(self, plan):
        self.plan = plan

    def write_config(self):
        """
        Build and persist the local_config.json with absolute paths
        for runtimes (executable + dependencies) and assets.

        Uses the resolved dependency names recorded by DependencyManager when available,
        falling back to the original dependency list from the plan.
        """
        global_target_dir = os.path.abspath(self.plan.get("global_target_dir"))
        bridge_in_path = os.path.join(global_target_dir, "bridge_in.py")

        # Resolved dependencies map populated by DependencyManager during installation
        resolved_dependencies_map = self.plan.get("resolved_dependencies", {})

        config_data = {
            "install_path": global_target_dir,
            "bridge_in_path": bridge_in_path,
            "runtimes": {},
            "assets": {}
        }

        for job in self.plan.get("jobs", []):
            job_type = job.get("type")
            name = job.get("name")
            target_path = job.get("target_path")

            if not name or not target_path:
                continue

            if job_type == "runtime":
                executable = job.get("executable")
                # Prefer resolved dependencies (hardware-specific) over original list
                dependencies = resolved_dependencies_map.get(name, job.get("dependencies", []))

                runtime_entry = {}
                if executable:
                    runtime_entry["executable"] = os.path.abspath(
                        os.path.join(target_path, executable)
                    )
                if dependencies:
                    runtime_entry["dependencies"] = dependencies

                config_data["runtimes"][name] = runtime_entry

            elif job_type == "asset":
                config_data["assets"][name] = os.path.abspath(target_path)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.abspath(os.path.join(current_dir, "..", "local_config.json"))

        with open(config_path, "w", encoding="utf8") as f:
            json.dump(config_data, f, indent=4)