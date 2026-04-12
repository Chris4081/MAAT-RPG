# -*- coding: utf-8 -*-
"""
MAAT-OS | Model Downloader Plugin (resumable)
---------------------------------------------
• Prüft ob Modell im models/ liegt
• Falls nicht: fragt nach Download
• Resume via .part Datei
• Fortschritt immer sichtbar
• Retries bei Timeout/Verbindungsfehlern
• Musik während des Downloads (afplay-first, Linux-fähig)
• Kein hartes sys.exit im Plugin
"""

import json
import os
import platform
import sys
import time
import threading
import subprocess
from pathlib import Path
from typing import Optional

import requests
from colorama import Fore, Style
from shared.core.audio import ManagedAudioPlayer
from shared.core.maat_paths import get_models_dir as shared_get_models_dir, state_file
from shared.core.rpg_i18n import get_language

# ==========================================================
# CONFIG
# ==========================================================
TEICHAI_LOW_MODEL_SPEC = {
    "tier": "q3",
    "family": "teichai_qwen",
    "label": "TeichAI Qwen3-14B Claude Distill Q3_K_M",
    "name": "Qwen3-14B-Claude-4.5-Opus-Distill.q3_k_m.gguf",
    "repo_id": "TeichAI/Qwen3-14B-Claude-4.5-Opus-High-Reasoning-Distill-GGUF",
    "filename": "Qwen3-14B-Claude-4.5-Opus-Distill.q3_k_m.gguf",
    "url": (
        "https://huggingface.co/TeichAI/"
        "Qwen3-14B-Claude-4.5-Opus-High-Reasoning-Distill-GGUF/"
        "resolve/main/Qwen3-14B-Claude-4.5-Opus-Distill.q3_k_m.gguf?download=true"
    ),
    "aliases": ("qwen3-14b-claude-4.5-opus-distill", "teichai", "q3_k_m", "q3", "14b"),
}

TEICHAI_MID_MODEL_SPEC = {
    "tier": "q4",
    "family": "teichai_qwen",
    "label": "TeichAI Qwen3-14B Claude Distill Q4_K_M",
    "name": "Qwen3-14B-Claude-4.5-Opus-Distill.q4_k_m.gguf",
    "repo_id": "TeichAI/Qwen3-14B-Claude-4.5-Opus-High-Reasoning-Distill-GGUF",
    "filename": "Qwen3-14B-Claude-4.5-Opus-Distill.q4_k_m.gguf",
    "url": (
        "https://huggingface.co/TeichAI/"
        "Qwen3-14B-Claude-4.5-Opus-High-Reasoning-Distill-GGUF/"
        "resolve/main/Qwen3-14B-Claude-4.5-Opus-Distill.q4_k_m.gguf?download=true"
    ),
    "aliases": ("qwen3-14b-claude-4.5-opus-distill", "teichai", "q4_k_m", "q4", "14b"),
}

TEICHAI_HIGH_MODEL_SPEC = {
    "tier": "q5",
    "family": "teichai_qwen",
    "label": "TeichAI Qwen3-14B Claude Distill Q5_K_M",
    "name": "Qwen3-14B-Claude-4.5-Opus-Distill.q5_k_m.gguf",
    "repo_id": "TeichAI/Qwen3-14B-Claude-4.5-Opus-High-Reasoning-Distill-GGUF",
    "filename": "Qwen3-14B-Claude-4.5-Opus-Distill.q5_k_m.gguf",
    "url": (
        "https://huggingface.co/TeichAI/"
        "Qwen3-14B-Claude-4.5-Opus-High-Reasoning-Distill-GGUF/"
        "resolve/main/Qwen3-14B-Claude-4.5-Opus-Distill.q5_k_m.gguf?download=true"
    ),
    "aliases": ("qwen3-14b-claude-4.5-opus-distill", "teichai", "q5_k_m", "q5", "14b"),
}

LLAMA_ALT_MODEL_SPEC = {
    "tier": "q4",
    "family": "llama_alt",
    "label": "Meta-Llama-3.1-8B-Instruct-128k Q4_0",
    "name": "Meta-Llama-3.1-8B-Instruct-128k-Q4_0.gguf",
    "repo_id": "GPT4All-Community/Meta-Llama-3.1-8B-Instruct-128k-GGUF",
    "filename": "Meta-Llama-3.1-8B-Instruct-128k-Q4_0.gguf",
    "url": (
        "https://huggingface.co/GPT4All-Community/Meta-Llama-3.1-8B-Instruct-128k-GGUF/"
        "resolve/main/Meta-Llama-3.1-8B-Instruct-128k-Q4_0.gguf?download=true"
    ),
    "aliases": ("meta-llama-3.1-8b", "llama-3.1-8b", "gpt4all-community", "q4_0", "llama"),
}

CHUNK_SIZE = 1024 * 1024          # 1 MB
BAR_WIDTH = 40
CONNECT_TIMEOUT = 20
READ_TIMEOUT = 60
MAX_RETRIES = 8
RETRY_WAIT = 6

DOWNLOADER_TEXT = {
    "de": {
        "resume_at": "🔁 Fortsetzen bei {size}",
        "new_download": "🆕 Neuer Download startet",
        "incomplete": "Download unvollstaendig, wird erneut versucht.",
        "resume_rejected": "Server hat Resume nicht akzeptiert, starte neu.",
        "interrupted": "⚠ Download unterbrochen: {error}",
        "retrying": "🔁 Wiederhole in {wait}s (Versuch {retry}/{max_retries}) – Fortschritt bleibt erhalten.",
        "aborted": "Download nach {max_retries} Wiederholungen abgebrochen. Fortschritt bleibt erhalten: {progress}",
        "model_found": "\n✔ Modell gefunden: {model}\n",
        "path": "📁 Pfad: {path}\n",
        "missing_model": "\n⚠ Kein lokales Modell gefunden.\n",
        "required": "Benoetigt: {model}",
        "source": "Quelle: HuggingFace",
        "target": "Zielordner: {path}",
        "partial_with_total": "🧩 Teil-Download gefunden: {current} von {total} ({pct:.2f}%)",
        "partial_found": "🧩 Teil-Download gefunden: {size}",
        "resume_hint": "➡ Beim Start wird genau dort weitergeladen.\n",
        "no_partial": "➡ Noch kein Teil-Download vorhanden.\n",
        "download_prompt": "📥 Modell jetzt herunterladen / fortsetzen? [j/N]: ",
        "skipped": "\n⏭ Download uebersprungen. MAAT-OS wird beendet.\n",
        "loading": "⬇️  MAAT-OS laedt das Modell…\n",
        "wait": "Bitte warten. Der Fortschritt bleibt auch nach Abbruch erhalten.\n",
        "done": "\n✔ Download abgeschlossen\n",
        "saved": "📁 Gespeichert unter: {path}",
        "welcome": "🌿 Willkommen in MAAT-OS.\n",
        "download_error": "\n❌ Fehler beim Download:\n{error}\n",
        "progress_kept": "💾 Der bisherige Fortschritt wurde behalten und kann spaeter fortgesetzt werden.\n",
        "no_model_exit": "MAAT-OS: Kein Modell verfuegbar.",
        "system_profile": "🧠 Systemprofil: {arch}, ca. {ram_gb} GB RAM",
        "family_title": "🌐 Modellfamilie waehlen",
        "family_prompt": "Auswahl [1/2, Enter = Empfehlung]: ",
        "family_1": "[1] TeichAI Qwen3-14B Claude Distill (empfohlen)",
        "family_2": "[2] Meta-Llama-3.1-8B Instruct 128k (Alternative ohne Qwen)",
        "recommend_q3": "💡 Empfehlung: TeichAI Qwen3-14B Q3_K_M fuer x86_64/Intel-Systeme oder Geraete mit 16 GB RAM und weniger.",
        "recommend_q4": "💡 Empfehlung: TeichAI Qwen3-14B Q4_K_M fuer Apple Silicon ab 17 GB RAM.",
        "recommend_q5": "💡 Empfehlung: TeichAI Qwen3-14B Q5_K_M fuer Apple Silicon mit 32 GB RAM oder mehr.",
        "recommend_llama": "💡 Alternative: Meta-Llama-3.1-8B Q4_0 fuer Nutzer, die kein Qwen-Modell moechten.",
        "using_local": "\n✔ Lokales Modell gefunden: {model}\n",
        "using_local_path": "📁 Verwende: {path}\n",
        "using_fallback_local": "🌿 Es wird ein bereits vorhandenes lokales Modell verwendet, kein neuer Download noetig.",
        "gguf_hint": "🧩 Format: GGUF fuer llama.cpp / lokale Ausfuehrung",
        "quant_hint": "⚙️ Empfohlene Quantisierung: {label}",
        "hub_hint": "☁️ Download ueber Hugging Face Hub mit Resume-Unterstuetzung",
        "hub_start": "🤗 Download von Hugging Face startet …",
        "download_header": "🌿 MAAT-RPG Modell-Download",
        "tip_header": "💡 MAAT-Hinweise waehrend des Downloads",
        "tip_1": "• MAAT-RPG laeuft lokal auf deinem System.",
        "tip_2": "• /journal zeigt Maatis' Weg und Entscheidungen.",
        "tip_3": "• Guide-Kaempfe veraendern deinen Spielstand nicht.",
        "tip_4": "• Sprache kannst du spaeter im Menue umstellen.",
    },
    "en": {
        "resume_at": "🔁 Resuming at {size}",
        "new_download": "🆕 Starting new download",
        "incomplete": "Download incomplete, retrying.",
        "resume_rejected": "Server did not accept resume, restarting.",
        "interrupted": "⚠ Download interrupted: {error}",
        "retrying": "🔁 Retrying in {wait}s (attempt {retry}/{max_retries}) – progress is preserved.",
        "aborted": "Download aborted after {max_retries} retries. Progress remains preserved: {progress}",
        "model_found": "\n✔ Model found: {model}\n",
        "path": "📁 Path: {path}\n",
        "missing_model": "\n⚠ No local model found.\n",
        "required": "Required: {model}",
        "source": "Source: HuggingFace",
        "target": "Target folder: {path}",
        "partial_with_total": "🧩 Partial download found: {current} of {total} ({pct:.2f}%)",
        "partial_found": "🧩 Partial download found: {size}",
        "resume_hint": "➡ Startup will continue exactly from that point.\n",
        "no_partial": "➡ No partial download found yet.\n",
        "download_prompt": "📥 Download / resume the model now? [y/N]: ",
        "skipped": "\n⏭ Download skipped. MAAT-OS will exit.\n",
        "loading": "⬇️  MAAT-OS is loading the model…\n",
        "wait": "Please wait. Progress will be preserved even after interruption.\n",
        "done": "\n✔ Download complete\n",
        "saved": "📁 Saved at: {path}",
        "welcome": "🌿 Welcome to MAAT-OS.\n",
        "download_error": "\n❌ Download error:\n{error}\n",
        "progress_kept": "💾 Your current progress was preserved and can be resumed later.\n",
        "no_model_exit": "MAAT-OS: No model available.",
        "system_profile": "🧠 System profile: {arch}, about {ram_gb} GB RAM",
        "family_title": "🌐 Choose model family",
        "family_prompt": "Choice [1/2, Enter = recommended]: ",
        "family_1": "[1] TeichAI Qwen3-14B Claude Distill (recommended)",
        "family_2": "[2] Meta-Llama-3.1-8B Instruct 128k (non-Qwen alternative)",
        "recommend_q3": "💡 Recommendation: TeichAI Qwen3-14B Q3_K_M for x86_64/Intel systems or devices with 16 GB RAM and below.",
        "recommend_q4": "💡 Recommendation: TeichAI Qwen3-14B Q4_K_M for Apple Silicon with 17 GB RAM or more.",
        "recommend_q5": "💡 Recommendation: TeichAI Qwen3-14B Q5_K_M for Apple Silicon with 32 GB RAM or more.",
        "recommend_llama": "💡 Alternative: Meta-Llama-3.1-8B Q4_0 for users who do not want a Qwen model.",
        "using_local": "\n✔ Local model found: {model}\n",
        "using_local_path": "📁 Using: {path}\n",
        "using_fallback_local": "🌿 An existing local model will be used, no new download is required.",
        "gguf_hint": "🧩 Format: GGUF for llama.cpp / local execution",
        "quant_hint": "⚙️ Recommended quantization: {label}",
        "hub_hint": "☁️ Download via Hugging Face Hub with resume support",
        "hub_start": "🤗 Starting download from Hugging Face …",
        "download_header": "🌿 MAAT-RPG model download",
        "tip_header": "💡 MAAT hints while downloading",
        "tip_1": "• MAAT-RPG runs locally on your system.",
        "tip_2": "• /journal shows Maatis' path and decisions.",
        "tip_3": "• Guide battles do not change your progression.",
        "tip_4": "• You can change the language later in the menu.",
    },
}


def _dl_lang() -> str:
    return get_language(tuple(DOWNLOADER_TEXT.keys()))


def _dt(key: str, **kwargs) -> str:
    lang = _dl_lang()
    template = DOWNLOADER_TEXT.get(lang, DOWNLOADER_TEXT["de"]).get(key, DOWNLOADER_TEXT["de"].get(key, key))
    return template.format(**kwargs) if kwargs else template


def _yes(choice: str) -> bool:
    return choice.strip().lower() in ("j", "ja", "y", "yes")


# ==========================================================
# PATH HELPERS
# ==========================================================
def get_models_dir() -> Path:
    return shared_get_models_dir()


def _detect_ram_gb() -> int:
    try:
        if sys.platform == "darwin":
            raw = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip()
            return max(0, int(int(raw) / (1024 ** 3)))
        if sys.platform.startswith("linux"):
            with open("/proc/meminfo", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return max(0, int(kb / (1024 ** 2)))
    except Exception:
        pass
    return 0


def _system_profile() -> dict:
    arch = platform.machine().lower()
    ram_gb = _detect_ram_gb()
    return {"arch": arch, "ram_gb": ram_gb}


def _recommended_spec() -> dict:
    family = _preferred_family()
    profile = _system_profile()
    arch = profile["arch"]
    ram_gb = profile["ram_gb"]
    if family == "llama_alt":
        return LLAMA_ALT_MODEL_SPEC
    if arch != "arm64" or (ram_gb and ram_gb <= 16) or ram_gb == 0:
        return TEICHAI_LOW_MODEL_SPEC
    if ram_gb >= 32:
        return TEICHAI_HIGH_MODEL_SPEC
    return TEICHAI_MID_MODEL_SPEC


def _preferred_family() -> str:
    settings_path = Path(state_file("settings_state.json"))
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        family = data.get("model_family")
        if family in ("teichai_qwen", "llama_alt"):
            return family
    except Exception:
        pass
    return "teichai_qwen"


def _save_preferred_family(family: str):
    settings_path = Path(state_file("settings_state.json"))
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    data["model_family"] = family
    settings_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _choose_family() -> str:
    current = _preferred_family()
    print()
    print(Fore.CYAN + Style.BRIGHT + _dt("family_title") + Style.RESET_ALL)
    print(_dt("family_1"))
    print(_dt("family_2"))
    choice = input(_dt("family_prompt")).strip()
    if choice == "2":
        current = "llama_alt"
    elif choice == "1":
        current = "teichai_qwen"
    _save_preferred_family(current)
    return current


def _has_any_local_model(models_dir: Path) -> bool:
    return _find_any_local_model(models_dir) is not None


def _find_local_model(models_dir: Path, spec: dict) -> Optional[Path]:
    aliases = tuple(a.lower() for a in spec.get("aliases", ()))
    exact = models_dir / spec["name"]
    if exact.exists() and exact.stat().st_size > 0:
        return exact
    for path in sorted(models_dir.glob("*.gguf")):
        name = path.name.lower()
        if any(alias in name for alias in aliases):
            return path
    return None


def _find_any_local_model(models_dir: Path) -> Optional[Path]:
    for path in sorted(models_dir.glob("*.gguf")):
        if path.exists() and path.stat().st_size > 0:
            return path
    return None


def _print_download_panel(spec: dict):
    print(Fore.CYAN + Style.BRIGHT + _dt("download_header") + Style.RESET_ALL)
    print(_dt("quant_hint", label=spec["label"]))
    print(_dt("gguf_hint"))
    print(_dt("hub_hint"))
    print()
    print(Fore.YELLOW + _dt("tip_header") + Style.RESET_ALL)
    print(_dt("tip_1"))
    print(_dt("tip_2"))
    print(_dt("tip_3"))
    print(_dt("tip_4"))
    print()


def _print_recommendation(chosen_family: str, spec: dict, profile: dict):
    print(_dt("system_profile", arch=profile["arch"], ram_gb=profile["ram_gb"] or "?"))
    if chosen_family == "llama_alt":
        print(_dt("recommend_llama"))
    elif spec["tier"] == "q5":
        print(_dt("recommend_q5"))
    elif spec["tier"] == "q4":
        print(_dt("recommend_q4"))
    else:
        print(_dt("recommend_q3"))
    print(_dt("quant_hint", label=spec["label"]))
    print(_dt("gguf_hint"))
    print(_dt("hub_hint"))


# ==========================================================
# MUSIC
# ==========================================================
class Music:
    def __init__(self, track_path: str):
        self.track = track_path
        self._player = ManagedAudioPlayer(track_path)

    def start(self):
        if not os.path.isfile(self.track):
            return
        self._player.set_track(self.track)
        self._player.start_loop()

    def stop(self):
        self._player.stop()


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
        print(Fore.CYAN + _dt("resume_at", size=format_bytes(existing)) + Style.RESET_ALL)
    else:
        print(Fore.CYAN + _dt("new_download") + Style.RESET_ALL)

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
                        raise RuntimeError(_dt("resume_rejected"))

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
                raise RuntimeError(_dt("incomplete"))

            part_path.replace(final_path)
            meta_path.unlink(missing_ok=True)
            return

        except Exception as e:
            retries += 1
            print()
            print(Fore.YELLOW + _dt("interrupted", error=e) + Style.RESET_ALL)
            save_progress(meta_path, downloaded_total, total_size)

            if retries > MAX_RETRIES:
                raise RuntimeError(
                    _dt("aborted", max_retries=MAX_RETRIES, progress=format_bytes(downloaded_total))
                ) from e

            print(
                Fore.CYAN
                + _dt("retrying", wait=RETRY_WAIT, retry=retries, max_retries=MAX_RETRIES)
                + Style.RESET_ALL
            )
            time.sleep(RETRY_WAIT)


# ==========================================================
# CORE
# ==========================================================
def ensure_model(plugin_dir: str, force_open: bool = False) -> bool:
    models_dir = get_models_dir()
    chosen_family = _preferred_family()
    spec = _recommended_spec()
    final_path = models_dir / spec["name"]
    part_path = final_path.with_suffix(final_path.suffix + ".part")
    meta_path = final_path.with_suffix(final_path.suffix + ".progress.json")
    profile = _system_profile()

    local_match = _find_local_model(models_dir, spec)
    if local_match and not force_open:
        print(Fore.GREEN + _dt("using_local", model=local_match.name) + Style.RESET_ALL)
        print(_dt("using_local_path", path=local_match))
        return True

    fallback_local = _find_any_local_model(models_dir)
    if fallback_local and not force_open:
        print(Fore.GREEN + _dt("using_local", model=fallback_local.name) + Style.RESET_ALL)
        print(_dt("using_local_path", path=fallback_local))
        print(_dt("using_fallback_local"))
        return True

    if force_open:
        current_local = local_match or fallback_local
        if current_local:
            print(Fore.GREEN + _dt("using_local", model=current_local.name) + Style.RESET_ALL)
            print(_dt("using_local_path", path=current_local))
            print()

    chosen_family = _choose_family()
    spec = _recommended_spec()
    final_path = models_dir / spec["name"]
    part_path = final_path.with_suffix(final_path.suffix + ".part")
    meta_path = final_path.with_suffix(final_path.suffix + ".progress.json")

    _print_recommendation(chosen_family, spec, profile)

    if not force_open:
        print(Fore.RED + _dt("missing_model") + Style.RESET_ALL)
    print(_dt("required", model=spec["name"]))
    print(_dt("source"))
    print(_dt("target", path=models_dir))

    progress = load_progress(meta_path)
    if part_path.exists():
        partial_size = part_path.stat().st_size
        total = progress.get("total", 0)
        if total:
            pct = partial_size / total * 100
            print(_dt("partial_with_total", current=format_bytes(partial_size), total=format_bytes(total), pct=pct))
        else:
            print(_dt("partial_found", size=format_bytes(partial_size)))
        print(_dt("resume_hint"))
    else:
        print(_dt("no_partial"))

    choice = input(_dt("download_prompt")).strip().lower()
    if not _yes(choice):
        print(_dt("skipped"))
        return False

    music = Music(os.path.join(plugin_dir, "download_theme.mp3"))
    music.start()

    clear()
    print(Fore.CYAN + _dt("loading") + Style.RESET_ALL)
    print(_dt("wait"))
    _print_download_panel(spec)

    try:
        print(Fore.CYAN + _dt("hub_start") + Style.RESET_ALL)
        resumable_download(spec["url"], final_path)
        music.stop()

        print(Fore.GREEN + _dt("done") + Style.RESET_ALL)
        print(_dt("saved", path=final_path))
        print(_dt("welcome"))
        time.sleep(0.8)
        return True

    except Exception as e:
        music.stop()
        print(Fore.RED + _dt("download_error", error=e) + Style.RESET_ALL)
        print(_dt("progress_kept"))
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
            raise SystemExit(_dt("no_model_exit"))
