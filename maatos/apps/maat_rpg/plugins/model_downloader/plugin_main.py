# -*- coding: utf-8 -*-
"""
MAAT-OS | Model Downloader Plugin (resumable)
---------------------------------------------
• Prüft ob Modell im models/ liegt
• Falls nicht: fragt nach Download
• Resume via .part Datei
• Fortschritt immer sichtbar
• Retries bei Timeout/Verbindungsfehlern
• Musik während des Downloads (macOS)
• Kein hartes sys.exit im Plugin
"""

import json
import os
import sys
import time
import threading
import subprocess
from pathlib import Path
from typing import Optional

import requests
from colorama import Fore, Style

# ==========================================================
# CONFIG
# ==========================================================
MODEL_NAME = "Qwen3-14B-Claude-4.5-Opus-Distill.q3_k_m.gguf"
MODEL_URL = (
    "https://huggingface.co/TeichAI/"
    "Qwen3-14B-Claude-4.5-Opus-High-Reasoning-Distill-GGUF/"
    "resolve/main/Qwen3-14B-Claude-4.5-Opus-Distill.q3_k_m.gguf?download=true"
)

CHUNK_SIZE = 1024 * 1024          # 1 MB
BAR_WIDTH = 40
CONNECT_TIMEOUT = 20
READ_TIMEOUT = 60
MAX_RETRIES = 8
RETRY_WAIT = 6


# ==========================================================
# PATH HELPERS
# ==========================================================
def get_models_dir() -> Path:
    env_dir = os.environ.get("MAAT_MODELS_DIR")
    if env_dir:
        path = Path(env_dir)
    else:
        path = Path.home() / "Library" / "Application Support" / "MAAT-RPG" / "models"

    path.mkdir(parents=True, exist_ok=True)
    return path


# ==========================================================
# MUSIC
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
# UI
# ==========================================================
def clear():
    os.system("clear" if os.name != "nt" else "cls")


def format_bytes(num: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num)
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{num} B"


def print_progress(downloaded: int, total: int, speed_bps: float | None = None):
    if total <= 0:
        line = f"\r⬇ {format_bytes(downloaded)}"
        if speed_bps:
            line += f" | {format_bytes(int(speed_bps))}/s"
        print(line, end="", flush=True)
        return

    pct = downloaded / total if total else 0.0
    pct = min(max(pct, 0.0), 1.0)
    filled = int(pct * BAR_WIDTH)
    bar = "█" * filled + "·" * (BAR_WIDTH - filled)

    line = (
        f"\r[{bar}] {pct * 100:6.2f}% "
        f"| {format_bytes(downloaded)} / {format_bytes(total)}"
    )

    if speed_bps and speed_bps > 0:
        remaining = total - downloaded
        eta = int(remaining / speed_bps) if speed_bps > 0 else 0
        line += f" | {format_bytes(int(speed_bps))}/s | ETA {eta}s"

    print(line, end="", flush=True)


# ==========================================================
# DOWNLOAD CORE
# ==========================================================
def get_remote_total_size(url: str) -> int:
    with requests.Session() as s:
        r = s.head(url, allow_redirects=True, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        r.raise_for_status()
        return int(r.headers.get("content-length", 0))


def save_progress(meta_path: Path, downloaded: int, total: int):
    data = {
        "downloaded": downloaded,
        "total": total,
        "updated_at": time.time(),
    }
    meta_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_progress(meta_path: Path) -> dict:
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def resumable_download(url: str, final_path: Path):
    part_path = final_path.with_suffix(final_path.suffix + ".part")
    meta_path = final_path.with_suffix(final_path.suffix + ".progress.json")

    # Schon fertig?
    if final_path.exists() and final_path.stat().st_size > 0:
        return

    total_size = 0
    try:
        total_size = get_remote_total_size(url)
    except Exception:
        total_size = 0

    existing = part_path.stat().st_size if part_path.exists() else 0

    if total_size > 0 and existing > total_size:
        part_path.unlink(missing_ok=True)
        meta_path.unlink(missing_ok=True)
        existing = 0

    if existing > 0:
        print(Fore.CYAN + f"🔁 Fortsetzen bei {format_bytes(existing)}" + Style.RESET_ALL)
    else:
        print(Fore.CYAN + "🆕 Neuer Download startet" + Style.RESET_ALL)

    retries = 0
    downloaded_total = existing

    while retries <= MAX_RETRIES:
        headers = {}
        mode = "ab"

        if downloaded_total > 0:
            headers["Range"] = f"bytes={downloaded_total}-"
        else:
            mode = "wb"

        try:
            with requests.Session() as s:
                with s.get(
                    url,
                    stream=True,
                    headers=headers,
                    allow_redirects=True,
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                ) as r:
                    # 206 = partial content, 200 = full content
                    if downloaded_total > 0 and r.status_code == 200:
                        # Server ignoriert Range -> sauber neu anfangen
                        downloaded_total = 0
                        if part_path.exists():
                            part_path.unlink()
                        if meta_path.exists():
                            meta_path.unlink()
                        headers = {}
                        mode = "wb"
                        raise RuntimeError("Server hat Resume nicht akzeptiert, starte neu.")

                    r.raise_for_status()

                    # Gesamtgröße aus Content-Range oder Content-Length
                    if "Content-Range" in r.headers:
                        # Beispiel: bytes 1048576-9999999/10000000
                        total_size = int(r.headers["Content-Range"].split("/")[-1])
                    elif total_size <= 0:
                        content_len = int(r.headers.get("content-length", 0))
                        total_size = downloaded_total + content_len if content_len else 0

                    last_tick = time.time()
                    last_bytes = downloaded_total

                    with open(part_path, mode) as f:
                        for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                            if not chunk:
                                continue
                            f.write(chunk)
                            downloaded_total += len(chunk)

                            now = time.time()
                            dt = max(now - last_tick, 1e-6)
                            speed = (downloaded_total - last_bytes) / dt

                            print_progress(downloaded_total, total_size, speed)
                            save_progress(meta_path, downloaded_total, total_size)

                            last_tick = now
                            last_bytes = downloaded_total

            # Fertig?
            print()
            if total_size > 0 and downloaded_total < total_size:
                raise RuntimeError("Download unvollständig, wird erneut versucht.")

            part_path.replace(final_path)
            meta_path.unlink(missing_ok=True)
            return

        except Exception as e:
            retries += 1
            print()
            print(Fore.YELLOW + f"⚠ Download unterbrochen: {e}" + Style.RESET_ALL)
            save_progress(meta_path, downloaded_total, total_size)

            if retries > MAX_RETRIES:
                raise RuntimeError(
                    f"Download nach {MAX_RETRIES} Wiederholungen abgebrochen. "
                    f"Fortschritt bleibt erhalten: {format_bytes(downloaded_total)}"
                ) from e

            print(
                Fore.CYAN
                + f"🔁 Wiederhole in {RETRY_WAIT}s "
                  f"(Versuch {retries}/{MAX_RETRIES}) – Fortschritt bleibt erhalten."
                + Style.RESET_ALL
            )
            time.sleep(RETRY_WAIT)


# ==========================================================
# CORE
# ==========================================================
def ensure_model(plugin_dir: str) -> bool:
    models_dir = get_models_dir()
    final_path = models_dir / MODEL_NAME
    part_path = final_path.with_suffix(final_path.suffix + ".part")
    meta_path = final_path.with_suffix(final_path.suffix + ".progress.json")

    if final_path.exists() and final_path.stat().st_size > 0:
        print(Fore.GREEN + f"\n✔ Modell gefunden: {MODEL_NAME}\n" + Style.RESET_ALL)
        print(f"📁 Pfad: {final_path}\n")
        return True

    print(Fore.RED + "\n⚠ Kein lokales Modell gefunden.\n" + Style.RESET_ALL)
    print(f"Benötigt: {MODEL_NAME}")
    print("Quelle: HuggingFace")
    print("Zielordner:", models_dir)

    progress = load_progress(meta_path)
    if part_path.exists():
        partial_size = part_path.stat().st_size
        total = progress.get("total", 0)
        if total:
            pct = partial_size / total * 100
            print(f"🧩 Teil-Download gefunden: {format_bytes(partial_size)} von {format_bytes(total)} ({pct:.2f}%)")
        else:
            print(f"🧩 Teil-Download gefunden: {format_bytes(partial_size)}")
        print("➡ Beim Start wird genau dort weitergeladen.\n")
    else:
        print("➡ Noch kein Teil-Download vorhanden.\n")

    choice = input("📥 Modell jetzt herunterladen / fortsetzen? [j/N]: ").strip().lower()
    if choice != "j":
        print("\n⏭ Download übersprungen. MAAT-OS wird beendet.\n")
        return False

    music = Music(os.path.join(plugin_dir, "download_theme.mp3"))
    music.start()

    clear()
    print(Fore.CYAN + "⬇️  MAAT-OS lädt das Modell…\n" + Style.RESET_ALL)
    print("Bitte warten. Der Fortschritt bleibt auch nach Abbruch erhalten.\n")

    try:
        resumable_download(MODEL_URL, final_path)
        music.stop()

        print(Fore.GREEN + "\n✔ Download abgeschlossen\n" + Style.RESET_ALL)
        print(f"📁 Gespeichert unter: {final_path}")
        print("🌿 Willkommen in MAAT-OS.\n")
        time.sleep(0.8)
        return True

    except Exception as e:
        music.stop()
        print(Fore.RED + f"\n❌ Fehler beim Download:\n{e}\n" + Style.RESET_ALL)
        print("💾 Der bisherige Fortschritt wurde behalten und kann später fortgesetzt werden.\n")
        return False


# ==========================================================
# PLUGIN WRAPPER
# ==========================================================
class Plugin:
    type = "startup"

    def __init__(self):
        self.plugin_dir = os.path.dirname(__file__)

    def on_startup(self, context=None):
        clear()
        ok = ensure_model(self.plugin_dir)
        if not ok:
            raise SystemExit("MAAT-OS: Kein Modell verfügbar.")