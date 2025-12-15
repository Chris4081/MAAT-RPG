# shared/profile_loader.py
# Lädt Profile (JSON) aus /maatos/profiles

import os
import json


class ProfileLoader:
    def __init__(self, root_path: str):
        """
        root_path:
          - kann /maatos sein (wie in maat_classic/basic.py)
          - oder ein Unterordner wie /maatos/apps/maat_rpg

        Der Loader sucht immer nach /maatos/profiles.
        """
        self.root = os.path.abspath(root_path)
        self.maatos_root = self._find_maatos_root()
        self.profile_dir = os.path.join(self.maatos_root, "profiles")

        if not os.path.isdir(self.profile_dir):
            os.makedirs(self.profile_dir, exist_ok=True)

    def _find_maatos_root(self) -> str:
        """
        Geht im Pfad nach oben, bis ein Ordner 'maatos' gefunden wird.
        """
        p = self.root
        while True:
            if os.path.basename(p) == "maatos":
                return p
            new_p = os.path.dirname(p)
            if new_p == p:
                # Fallback: 'maatos' nicht gefunden → root zurückgeben
                return self.root
            p = new_p

    def list_profiles(self):
        """Gibt alle Profil-Dateien (*.json) unter /maatos/profiles zurück."""
        return [
            f for f in os.listdir(self.profile_dir)
            if f.endswith(".json")
        ]

    def load_profile(self, name: str) -> dict:
        """
        Lädt ein Profil als Dict.
        name: z.B. 'classic.json' oder 'maat_rpg.json'
        """
        path = os.path.join(self.profile_dir, name)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Profil nicht gefunden: {path}")

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_profile(self, name: str, data: dict):
        """
        Speichert ein Profil (Dict → JSON) nach /maatos/profiles/name.
        """
        path = os.path.join(self.profile_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)