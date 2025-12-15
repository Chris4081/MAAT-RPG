# -*- coding: utf-8 -*-
"""
MAAT-OS | Model Downloader Plugin
---------------------------------
• Prüft ob Modell im models/ liegt
• Falls nicht: fragt nach Download
• Cinematic Download + Progress Anzeige
• Musik während des Downloads (macOS)
• Stoppt Musik nach Erfolg/Fehler
• Kein hartes sys.exit im Plugin
"""

import os
import sys
import time
import threading
import subprocess
from typing import Optional

import requests
from colorama import Fore, Style

# ==========================================================
# CONFIG
# ==========================================================

MODEL_NAME = "Meta-Llama-3.1-8B-Instruct-128k-Q4_0.gguf"
MODEL_URL = (
    "https://huggingface.co/GPT4All-Community/"
    "Meta-Llama-3.1-8B-Instruct-128k-GGUF/"
    "resolve/main/Meta-Llama-3.1-8B-Instruct-128k-Q4_0.gguf"
)

MODEL_DIR = "models"
CHUNK_SIZE = 8192
BAR_WIDTH = 40


# ==========================================================
# MUSIC (macOS only, silent fallback)
# ==========================================================

class Music:
    def __init__(self, track_path: str):
        self.track = track_path
        self._run = False
        self._thread: Optional[threading.Thread] = None

    def _loop(self):
        while self._run:
            subprocess.call(
                ["afplay", self.track],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    def start(self):
        if sys.platform != "darwin":
            return
        if not os.path.isfile(self.track):
            return

        self._run = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._run = False
        if sys.platform == "darwin":
            subprocess.call(
                ["killall", "afplay"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


# ==========================================================
# HELPERS
# ==========================================================

def clear():
    os.system("clear" if os.name != "nt" else "cls")


def _print_progress(downloaded: int, total: int):
    if total <= 0:
        print(f"\r{downloaded / 1e6:.2f} MB", end="")
        return

    pct = downloaded / total
    filled = int(pct * BAR_WIDTH)
    bar = "█" * filled + "·" * (BAR_WIDTH - filled)

    print(f"\r[{bar}] {pct * 100:5.1f}%", end="")


def download_with_progress(url: str, target_path: str):
    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0

        with open(target_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                _print_progress(downloaded, total)

    print("\n")


# ==========================================================
# CORE
# ==========================================================

def ensure_model(plugin_dir: str) -> bool:
    """
    Returns:
        True  -> Modell vorhanden oder erfolgreich geladen
        False -> Nutzer abgebrochen
    """

    # sauber & robust: Root = 4 Ebenen hoch
    root = os.path.abspath(
        os.path.join(plugin_dir, "..", "..", "..", "..")
    )

    models_dir = os.path.join(root, MODEL_DIR)
    os.makedirs(models_dir, exist_ok=True)

    target = os.path.join(models_dir, MODEL_NAME)

    if os.path.isfile(target):
        print(
            Fore.GREEN
            + f"\n✔ Modell gefunden: {MODEL_NAME}\n"
            + Style.RESET_ALL
        )
        return True

    # ------------------------------------------------------
    # USER CONFIRMATION
    # ------------------------------------------------------

    print(Fore.RED + "\n⚠ Kein lokales Modell gefunden.\n" + Style.RESET_ALL)
    print(f"Benötigt: {MODEL_NAME}")
    print("Quelle: HuggingFace")
    print("Größe: ~4 GB")
    print("Internetverbindung erforderlich.\n")

    choice = input("📥 Modell jetzt herunterladen? [j/N]: ").strip().lower()
    if choice != "j":
        print("\n⏭ Download übersprungen. MAAT-OS wird beendet.\n")
        return False

    # ------------------------------------------------------
    # CINEMATIC DOWNLOAD
    # ------------------------------------------------------

    music = Music(os.path.join(plugin_dir, "download_theme.mp3"))
    music.start()

    clear()
    print(Fore.CYAN + "⬇️  MAAT-OS lädt das Modell…\n" + Style.RESET_ALL)
    print("Bitte warten. Dies kann einige Minuten dauern.\n")

    try:
        download_with_progress(MODEL_URL, target)
        music.stop()

        print(Fore.GREEN + "\n✔ Download abgeschlossen\n" + Style.RESET_ALL)
        print("🌿 Willkommen in MAAT-OS.\n")
        time.sleep(0.8)
        return True

    except Exception as e:
        music.stop()
        print(
            Fore.RED
            + f"\n❌ Fehler beim Download:\n{e}\n"
            + Style.RESET_ALL
        )
        return False


# ==========================================================
# PLUGIN WRAPPER
# ==========================================================

class Plugin:
    """
    Startup-Plugin:
    • blockiert NICHT hart
    • übergibt Kontrolle sauber an den AppLoader
    """

    type = "startup"

    def __init__(self):
        self.plugin_dir = os.path.dirname(__file__)

    def on_startup(self, context=None):
        clear()
        ok = ensure_model(self.plugin_dir)

        if not ok:
            # sauber abbrechen – kein sys.exit im Plugin
            raise SystemExit("MAAT-OS: Kein Modell verfügbar.")