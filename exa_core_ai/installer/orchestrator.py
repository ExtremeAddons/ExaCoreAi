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


import queue
import threading

from .config_reader import ConfigReader
from .downloader import ResourceDownloader
from .extractor import ResourceExtractor
from .dependency_manager import DependencyManager


class Orchestrator:
    def __init__(self, base_path):
        self.base_path = base_path
        self.message_queue = queue.Queue()
        self._cancel_event = threading.Event()
        self.thread = None

    def start_installation_async(self):
        self.thread = threading.Thread(target=self._run_pipeline)
        self.thread.daemon = True
        self.thread.start()

    def request_cancel(self):
        self._cancel_event.set()
        self.message_queue.put(("CANCELLED", "Cancellation requested by user.", 0.0))

    def _run_pipeline(self):
        try:
            self.message_queue.put(("RUNNING", "Reading configuration...", 0.02))

            if self._cancel_event.is_set(): return

            reader = ConfigReader(self.base_path)
            plan = reader.get_installation_plan()
            if not plan.get("jobs", []):
                self.message_queue.put(("FINISHED", "No work to execute.", 1.0))
                return

            self.message_queue.put(("RUNNING", "Starting downloads...", 0.05))

            # Passa self.message_queue al Downloader in modo che possa parlare con l'interfaccia
            downloader = ResourceDownloader(
                plan,
                cancel_event=self._cancel_event,
                message_queue=self.message_queue,
                base_progress=0.05,
                max_progress=0.70
            )
            downloader.execute_downloads()

            if self._cancel_event.is_set(): return

            self.message_queue.put(("RUNNING", "Extracting archives...", 0.70))
            extractor = ResourceExtractor(plan, self._cancel_event)
            extractor.execute_extractions()

            if self._cancel_event.is_set(): return

            # self.message_queue.put(("RUNNING", "Installing dependencies...", 0.85))
            # manager = DependencyManager(plan, self._cancel_event)
            # manager.execute_installations()

            self.message_queue.put(("RUNNING", "Installing dependencies...", 0.85))
            manager = DependencyManager(
                plan,
                cancel_event=self._cancel_event,
                message_queue=self.message_queue,
                base_progress=0.85,
                max_progress=0.98
            )
            manager.execute_installations()

            if self._cancel_event.is_set(): return

            from .local_config_writer import LocalConfigWriter
            writer = LocalConfigWriter(plan)
            writer.write_config()

            self.message_queue.put(("FINISHED", "Installation completed successfully!", 1.0))

        except Exception as error:
            self.message_queue.put(("ERROR", str(error), 0.0))