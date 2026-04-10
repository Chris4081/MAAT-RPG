# shared/core/llm_loader.py
# Basis-Lader des MAAT-KI LLM-Systems
print("🧪 llm_loader.py: IMPORT START")

import os
import json
from pathlib import Path
from colorama import Fore, Style
from .backend_router import load_backend

# -------------------------------------------------------------
# ROOT + MODEL_DIR
# -------------------------------------------------------------

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

def _app_support_dir() -> str:
    env = os.environ.get("MAAT_APP_SUPPORT_DIR")
    if env:
        path = Path(env)
    else:
        path = Path.home() / "Library" / "Application Support" / "MAAT-RPG"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)

def _data_dir() -> str:
    env = os.environ.get("MAAT_DATA_DIR")
    if env:
        path = Path(env)
    else:
        path = Path(_app_support_dir()) / "data"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)

def _models_dir() -> str:
    env = os.environ.get("MAAT_MODELS_DIR")
    if env:
        path = Path(env)
    else:
        path = Path(_app_support_dir()) / "models"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)

MODEL_DIR_DEFAULT = os.environ.get(
    "MAAT_MODELS_DIR",
    os.path.join(ROOT, "models")
)

# -------------------------------------------------------------
# OVERRIDE PATHS (MODEL / PERF)
# -------------------------------------------------------------

def _model_override_path() -> str:
    return os.path.join(_data_dir(), "model_override.txt")

def _perf_override_path() -> str:
    return os.path.join(_data_dir(), "perf_override.json")

# 🔁 Backward compatibility (alte Aufrufe)
def _override_path() -> str:
    return _model_override_path()

# -------------------------------------------------------------
# PERFORMANCE SAVE / LOAD
# -------------------------------------------------------------

def load_saved_perf() -> dict | None:
    path = _perf_override_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else None
    except Exception:
        return None

def save_perf(perf: dict):
    try:
        path = _perf_override_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(perf, f, indent=2)
        print(
            Fore.CYAN
            + f"💾 Performance gespeichert: {path}"
            + Style.RESET_ALL
        )
    except Exception as e:
        print(Fore.RED + f"⚠ Konnte Performance nicht speichern: {e}" + Style.RESET_ALL)

# -------------------------------------------------------------
# MODEL SAVE / LOAD
# -------------------------------------------------------------

def load_saved_model_name() -> str | None:
    path = _model_override_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            name = f.read().strip()
            return name if name else None
    except Exception:
        return None

def save_last_model_choice(model_name: str):
    try:
        path = _model_override_path()
        with open(path, "w", encoding="utf-8") as f:
            f.write(model_name.strip())
        print(
            Fore.CYAN
            + f"💾 Modell gespeichert: {model_name} → {path}"
            + Style.RESET_ALL
        )
    except Exception as e:
        print(Fore.RED + f"⚠ Konnte Modell nicht speichern: {e}" + Style.RESET_ALL)

# -------------------------------------------------------------
# MODEL LISTING
# -------------------------------------------------------------

def list_available_models(model_dir: str = None) -> list[str]:
    if model_dir is None:
        model_dir = MODEL_DIR_DEFAULT
    if not os.path.isdir(model_dir):
        return []

    models = []
    for name in os.listdir(model_dir):
        full = os.path.join(model_dir, name)
        if os.path.isdir(full) or name.endswith(".gguf"):
            models.append(name)

    return sorted(models)

# -------------------------------------------------------------
# MODEL SELECTION
# -------------------------------------------------------------

def auto_select_model(model_dir: str = None) -> str:
    if model_dir is None:
        model_dir = MODEL_DIR_DEFAULT

    models = list_available_models(model_dir)
    if not models:
        print(Fore.RED + "❌ Keine Modelle gefunden!" + Style.RESET_ALL)
        raise SystemExit(1)

    saved = load_saved_model_name()
    if saved and saved in models:
        print(
            Fore.GREEN
            + f"🌿 Auto-Load: Verwende gespeichertes Modell: {saved}"
            + Style.RESET_ALL
        )
        return os.path.join(model_dir, saved)

    print("──────────────────────────────────────────────")
    print("🌿 MAAT-KI — Modell auswählen")
    print("──────────────────────────────────────────────")

    for i, m in enumerate(models, 1):
        print(f"[{i}] {m}")

    while True:
        choice = input("\n🔢 Auswahl: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                chosen = models[idx]
                save_last_model_choice(chosen)
                return os.path.join(model_dir, chosen)
        except Exception:
            pass

        print(Fore.RED + "Bitte eine gültige Zahl eingeben." + Style.RESET_ALL)

# -------------------------------------------------------------
# PERFORMANCE SELECTION
# -------------------------------------------------------------

def choose_performance() -> dict:
    saved = load_saved_perf()
    if isinstance(saved, dict):
        print(
            Fore.GREEN
            + f"🌿 Auto-Load Performance: "
              f"n_ctx={saved.get('n_ctx')} "
              f"temp={saved.get('temperature')} "
              f"top_p={saved.get('top_p')} "
              f"backend={saved.get('backend', 'llama')}"
            + Style.RESET_ALL
        )
        return saved

    print("\n──────────────────────────────────────────────")
    print("⚙️ Performance-Modus")
    print("──────────────────────────────────────────────")
    print("[1] HIGH       (20k Kontext, stabil)")
    print("[2] MEDIUM     (16k)")
    print("[3] LOW        (12k)")
    print("[4] ULTRA LOW  (10k wenig Speicher)")

    profiles = {
        "1": dict(n_ctx=20000, temperature=1.0, top_p=0.9),
        "2": dict(n_ctx=16000, temperature=1.0, top_p=0.9),
        "3": dict(n_ctx=12000, temperature=0.9, top_p=0.9),
        "4": dict(n_ctx=10000, temperature=0.8, top_p=0.9),
    }

    choice = input("\n🔢 Auswahl: ").strip()
    perf = profiles.get(choice, profiles["1"])

    perf["backend"] = "llama"

    save_perf(perf)

    print(
        Fore.CYAN
        + f"⚙️ Performance gewählt: "
          f"n_ctx={perf['n_ctx']} "
          f"temp={perf['temperature']} "
          f"top_p={perf['top_p']} "
          f"backend={perf['backend']}"
        + Style.RESET_ALL
    )

    return perf

# -------------------------------------------------------------
# LLM LOAD
# -------------------------------------------------------------

def load_llm(model_path: str, perf: dict):
    backend = perf.get("backend", "llama")

    max_ctx = int(perf.get("n_ctx", 4096))
    temperature = float(perf.get("temperature", 0.7))
    threads = int(perf.get("threads", 4))
    gpu_layers = int(perf.get("gpu_layers", 0))

    print("──────────────────────────────────────────────")
    print("🧠 LLM wird geladen …")
    print(f"   Modell:  {model_path}")
    print(f"   Backend: {backend}")
    print(f"   Kontext: {max_ctx}")
    print("──────────────────────────────────────────────")

    try:
        llm = load_backend(
            model_path,
            backend=backend,
            max_ctx=max_ctx,
            temperature=temperature,
            n_threads=threads,
            n_gpu_layers=gpu_layers,
        )

        if isinstance(llm, dict):
            llm["_maat_perf"] = perf
        else:
            setattr(llm, "_maat_perf", perf)

        return llm

    except Exception as e:
        print(
            Fore.RED
            + f"⚠ Backend-Fehler, fallback auf llama.cpp:\n{e}"
            + Style.RESET_ALL
        )

        if not model_path.lower().endswith(".gguf"):
            raise

        try:
            from llama_cpp import Llama
        except ImportError:
            print(Fore.RED + "❌ llama-cpp-python fehlt!" + Style.RESET_ALL)
            raise SystemExit(1)

        llm = Llama(
            model_path=model_path,
            n_ctx=max_ctx,
            temperature=temperature,
            n_threads=threads,
            n_gpu_layers=gpu_layers,
            logits_all=False,
            embedding=False,
            verbose=False,
        )

        setattr(llm, "_maat_perf", perf)
        return llm

print("🧪 llm_loader.py: IMPORT END")