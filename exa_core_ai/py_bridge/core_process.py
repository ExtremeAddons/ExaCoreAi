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


import os
import subprocess
import threading
import atexit

DAEMON_CODE = '''import sys
import pickle
import struct
import traceback
import importlib

active_instances = {}

def resolve_target(module_name, target_path):
    mod = importlib.import_module(module_name)
    target = mod
    for attr in target_path.split("."):
        target = getattr(target, attr)
    return target

def main():
    while True:
        try:
            raw_len = sys.stdin.buffer.read(4)
            if not raw_len:
                break
            length = struct.unpack(">I", raw_len)[0]
            payload_data = sys.stdin.buffer.read(length)
            if not payload_data:
                break
            
            payload = pickle.loads(payload_data)
            addon_path = payload.get("sys_path")
            
            if addon_path and addon_path not in sys.path:
                sys.path.insert(0, addon_path)
            
            action = payload.get("action", "run_function")
            
            if action == "run_function":
                target = resolve_target(payload["module"], payload["function"])
                result = target(*payload.get("args", ()), **payload.get("kwargs", {}))
                
            elif action == "instantiate":
                target = resolve_target(payload["module"], payload["class_name"])
                instance = target(*payload.get("args", ()), **payload.get("kwargs", {}))
                instance_id = str(id(instance))
                active_instances[instance_id] = instance
                result = instance_id
                
            elif action == "call_method":
                instance_id = payload["instance_id"]
                instance = active_instances[instance_id]
                method = getattr(instance, payload["method"])
                result = method(*payload.get("args", ()), **payload.get("kwargs", {}))

            elif action == "free_instance":
                instance_id = payload["instance_id"]
                del active_instances[instance_id]
                result = True
                
            response = {"success": True, "result": result}
        except Exception as e:
            response = {"success": False, "error": str(e), "trace": traceback.format_exc()}
        
        resp_data = pickle.dumps(response)
        sys.stdout.buffer.write(struct.pack(">I", len(resp_data)) + resp_data)
        sys.stdout.flush()

if __name__ == "__main__":
    main()
'''

class CoreProcess:
    def __init__(self, python_executable, install_path):
        self.python_executable = python_executable
        self.install_path = install_path
        self.daemon_script_path = install_path
        self.process = None
        self.lock = threading.Lock()
        atexit.register(self.close)

    def _ensure_daemon_script(self):
        if not os.path.exists(self.daemon_script_path):
            parent = os.path.dirname(self.daemon_script_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(self.daemon_script_path, "w", encoding="utf8") as f:
                f.write(DAEMON_CODE)

    def start(self):
        with self.lock:
            if self.process is not None:
                if self.process.poll() is None:
                    return self.process

            self._ensure_daemon_script()

            # Senza bufsize=0 gli stream sono buffered: read(n) restituisce esattamente n byte
            # (con uno stream raw su pipe read(n) può restituire meno, troncando la risposta)
            self.process = subprocess.Popen(
                [
                    self.python_executable,
                    self.daemon_script_path
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            return self.process

    def close(self):
        with self.lock:
            if self.process is not None:
                if self.process.poll() is None:
                    self.process.terminate()
                    self.process.wait()
                self.process = None