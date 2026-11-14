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


class LocalConfigReader:
    """
    Legge il file local_config.json e restituisce in modo sicuro i percorsi
    dei runtime, degli asset e del bridge installati sul disco locale.
    """

    def __init__(self, config_path=None):
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Trovandosi nella stessa cartella non serve risalire
            self.config_path = os.path.abspath(os.path.join(current_dir, "local_config.json"))
        else:
            self.config_path = os.path.abspath(config_path)

    def is_available(self) -> bool:
        """Verifica se il file di configurazione locale esiste sul disco."""
        return os.path.isfile(self.config_path)

    def _load_data(self) -> dict:
        if not self.is_available():
            raise FileNotFoundError(
                f"Configurazione locale non trovata in {self.config_path}. Eseguire prima l'installazione."
            )
        with open(self.config_path, "r", encoding="utf_8") as file:
            return json.load(file)

    def get_install_path(self) -> str:
        """Restituisce la cartella radice in cui il servizio e stato installato."""
        data = self._load_data()
        install_path = data.get("install_path")
        if not install_path:
            raise KeyError("Chiave 'install_path' mancante nella configurazione locale.")
        return install_path

    def get_bridge_in_path(self) -> str:
        """Restituisce il percorso assoluto dello script di ingresso del microservizio."""
        data = self._load_data()
        bridge_path = data.get("bridge_in_path")
        if not bridge_path:
            raise KeyError("Chiave 'bridge_in_path' mancante nella configurazione locale.")
        return bridge_path

    def get_runtime(self, runtime_name: str) -> str:
        """
        Returns the absolute path of the executable for the requested runtime.
        Supports both legacy (plain string) and new (dict with 'executable') formats.
        """
        data = self._load_data()
        runtimes = data.get("runtimes", {})
        entry = runtimes.get(runtime_name)
        if not entry:
            raise KeyError(f"Runtime '{runtime_name}' non trovato nella configurazione locale.")

        # Handle new dict format: {"executable": "...", "dependencies": [...]}
        if isinstance(entry, dict):
            executable_path = entry.get("executable")
        else:
            # Legacy format: plain string path
            executable_path = entry

        if not executable_path:
            raise KeyError(f"Runtime '{runtime_name}' non ha un eseguibile definito.")
        return executable_path

    def get_runtime_dependencies(self, runtime_name: str) -> list:
        """
        Returns the list of installed dependencies for the requested runtime.
        Returns an empty list if no dependencies are recorded.
        """
        data = self._load_data()
        runtimes = data.get("runtimes", {})
        entry = runtimes.get(runtime_name)
        if not entry:
            raise KeyError(f"Runtime '{runtime_name}' non trovato nella configurazione locale.")

        if isinstance(entry, dict):
            return entry.get("dependencies", [])
        return []

    def get_asset(self, asset_name: str) -> str:
        """Restituisce il percorso assoluto del modello o asset richiesto."""
        data = self._load_data()
        assets = data.get("assets", {})
        asset_path = assets.get(asset_name)
        if not asset_path:
            raise KeyError(f"Asset '{asset_name}' non trovato nella configurazione locale.")
        return asset_path

    def get_all_runtimes(self) -> dict:
        """Restituisce l'intero dizionario dei runtime installati."""
        return self._load_data().get("runtimes", {})

    def get_all_assets(self) -> dict:
        """Restituisce l'intero dizionario degli asset installati."""
        return self._load_data().get("assets", {})