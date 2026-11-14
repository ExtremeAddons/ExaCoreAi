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


# import os
# import re
# import stat
# import subprocess
# import threading
#
# from .graphic_scanner import ProGraphicScanner
# from .dependency_registry import DependencyRegistry
#
#
# class DependencyManager:
#     """
#     Manages dependency installation for each runtime in the plan,
#     monitoring cancellation and executing commands universally.
#     Resolves hardware-specific dependencies via DependencyRegistry.
#     """
#
#     def __init__(self, plan, cancel_event=None):
#         self.plan = plan
#         self.cancel_event = cancel_event
#         # Detect hardware profile once for all dependency resolutions
#         self.hardware_profile = ProGraphicScanner.get_system_profile()
#
#     def _check_cancel(self):
#         if self.cancel_event and self.cancel_event.is_set():
#             raise RuntimeError("Operation cancelled.")
#
#     def _resolve_dependencies(self, dependencies):
#         """
#         Resolve each dependency string against the DependencyRegistry.
#         If the base dependency name matches a registry entry, replace it with
#         the hardware-specific variant and collect any extra_args (e.g. --index-url).
#         Otherwise, keep the original dependency string unchanged.
#
#         Args:
#             dependencies: List of dependency strings from the installation plan.
#
#         Returns:
#             Tuple of (resolved_dependencies list, extra_args list).
#         """
#         resolved_dependencies = []
#         extra_args = []
#
#         for dep in dependencies:
#             # Extract base name by stripping version specifiers (==, >=, <=, ~=, !=)
#             base_name = re.split(r'[=<>!~]', dep)[0].strip().lower()
#
#             instructions = DependencyRegistry.get_install_instructions(
#                 self.hardware_profile, base_name
#             )
#
#             if instructions:
#                 resolved_dependencies.append(instructions["pkg"])
#                 extra_args.extend(instructions.get("extra_args", []))
#             else:
#                 # No registry match, keep original dependency as-is
#                 resolved_dependencies.append(dep)
#
#         return resolved_dependencies, extra_args
# ...existing code...
#             # Resolve hardware-specific dependencies and collect extra args
# ...existing code...

from collections import deque
import os
import re
import stat
import subprocess

from .graphic_scanner import ProGraphicScanner
from .dependency_registry import DependencyRegistry


class DependencyManager:
    """
    Manages dependency installation for each runtime in the plan,
    monitoring cancellation and reporting live progress to the UI queue.
    """

    def __init__(
        self,
        plan,
        cancel_event=None,
        message_queue=None,
        base_progress=0.85,
        max_progress=0.98
    ):
        self.plan = plan
        self.cancel_event = cancel_event
        self.message_queue = message_queue
        self.base_progress = base_progress
        self.max_progress = max_progress
        self.hardware_profile = ProGraphicScanner.get_system_profile()

    def _emit(self, message, progress):
        if self.message_queue:
            self.message_queue.put(("RUNNING", message, progress))

    def _check_cancel(self, process=None):
        if self.cancel_event and self.cancel_event.is_set():
            if process and process.poll() is None:
                process.terminate()
            raise RuntimeError("Operation cancelled.")

    def _resolve_single_dependency(self, dep):
        """
        Resolves a single dependency entry against DependencyRegistry.
        Splits space separated dependency strings into individual pip arguments.
        """
        base_name = re.split(r'[=<>!~]', dep)[0].strip().lower()

        instructions = DependencyRegistry.get_install_instructions(
            self.hardware_profile, base_name
        )

        if instructions:
            dependencies = instructions["pkg"].split()
            extra_args = list(instructions.get("extra_args", []))
            return dependencies, extra_args

        return [dep], []

    def _format_pip_line(self, dep_label, line, current_idx, total_deps):
        prefix = f"[{current_idx}/{total_deps}] {dep_label}"
        if line.startswith("Collecting "):
            pkg = line.replace("Collecting ", "").split()[0]
            return f"{prefix}: collecting {pkg}..."
        if line.startswith("Downloading "):
            pkg = line.replace("Downloading ", "").split()[0]
            return f"{prefix}: downloading {pkg}..."
        if line.startswith("Installing collected dependencies:"):
            return f"{prefix}: installing dependencies..."
        return None

    def execute_installations(self):
        jobs = self.plan.get("jobs", [])
        runtime_jobs = [
            job for job in jobs
            if job.get("type") == "runtime"
            and job.get("executable")
            and job.get("dependencies")
        ]

        total_deps = sum(len(job.get("dependencies", [])) for job in runtime_jobs)
        if total_deps == 0:
            return

        completed_deps = 0
        progress_span = self.max_progress - self.base_progress

        # Dictionary to store resolved dependency names per runtime,
        # so LocalConfigWriter can record what was actually installed.
        resolved_dependencies_map = self.plan.setdefault("resolved_dependencies", {})

        for job in runtime_jobs:
            self._check_cancel()

            target_path = job.get("target_path")
            executable = job.get("executable")
            args = job.get("args", [])
            dependencies = job.get("dependencies", [])
            runtime_name = job.get("name", "default")

            executable_path = os.path.join(target_path, executable)
            if not os.path.exists(executable_path):
                raise FileNotFoundError(f"Eseguibile non trovato in {executable_path}")

            if os.name != "nt":
                try:
                    current_mode = os.stat(executable_path).st_mode
                    os.chmod(
                        executable_path,
                        current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                    )
                except Exception:
                    pass

            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"

            # Collect all resolved dependency names for this runtime
            installed_dependencies = []

            for dep in dependencies:
                self._check_cancel()

                current_step = completed_deps + 1
                step_progress = self.base_progress + (completed_deps / total_deps) * progress_span
                self._emit(f"[{current_step}/{total_deps}] Preparing {dep}...", step_progress)

                resolved_deps, extra_args = self._resolve_single_dependency(dep)
                cmd = [executable_path] + args + extra_args + resolved_deps

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=env
                )

                recent_logs = deque(maxlen=25)
                for raw_line in iter(process.stdout.readline, ""):
                    self._check_cancel(process)
                    clean_line = raw_line.strip()
                    if not clean_line:
                        continue

                    recent_logs.append(clean_line)
                    status_msg = self._format_pip_line(dep, clean_line, current_step, total_deps)
                    if status_msg:
                        self._emit(status_msg, step_progress)

                process.stdout.close()
                process.wait()

                if process.returncode != 0:
                    error_tail = "\n".join(recent_logs)
                    raise RuntimeError(
                        f"Errore durante l'installazione di '{dep}':\n{error_tail}"
                    )

                # Record the actually installed dependency names
                installed_dependencies.extend(resolved_deps)

                completed_deps += 1
                done_progress = self.base_progress + (completed_deps / total_deps) * progress_span
                self._emit(f"[{completed_deps}/{total_deps}] Installed {dep}", done_progress)

            # Store resolved dependencies for this runtime in the plan
            resolved_dependencies_map[runtime_name] = installed_dependencies
