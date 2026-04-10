# shared/core/llm_loader.py
# Basis-Lader des MAAT-KI LLM-Systems
print("🧪 llm_loader.py: IMPORT START")

import os
import json
from pathlib import Path
from colorama import Fore, Style
from .backend_router import load_backend
from .rpg_i18n import get_language

# -------------------------------------------------------------
# ROOT + MODEL_DIR
# -------------------------------------------------------------

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

LLM_TEXT = {
    "de": {
        "perf_saved": "💾 Performance gespeichert: {path}",
        "perf_save_fail": "⚠ Konnte Performance nicht speichern: {error}",
        "model_saved": "💾 Modell gespeichert: {model} → {path}",
        "model_save_fail": "⚠ Konnte Modell nicht speichern: {error}",
        "no_models": "❌ Keine Modelle gefunden!",
        "auto_model": "🌿 Auto-Load: Verwende gespeichertes Modell: {model}",
        "model_header": "🌿 MAAT-KI — Modell auswaehlen",
        "choose": "\n🔢 Auswahl: ",
        "invalid_number": "Bitte eine gueltige Zahl eingeben.",
        "auto_perf": "🌿 Auto-Load Performance: n_ctx={n_ctx} temp={temp} top_p={top_p} backend={backend}",
        "perf_header": "⚙️ Performance-Modus",
        "perf_1": "[1] HIGH       (20k Kontext, stabil)",
        "perf_2": "[2] MEDIUM     (16k)",
        "perf_3": "[3] LOW        (12k)",
        "perf_4": "[4] ULTRA LOW  (10k wenig Speicher)",
        "perf_chosen": "⚙️ Performance gewaehlt: n_ctx={n_ctx} temp={temp} top_p={top_p} backend={backend}",
        "llm_loading": "🧠 LLM wird geladen …",
        "llm_model": "   Modell:  {model}",
        "llm_backend": "   Backend: {backend}",
        "llm_ctx": "   Kontext: {ctx}",
        "backend_fallback": "⚠ Backend-Fehler, fallback auf llama.cpp:\n{error}",
        "llama_missing": "❌ llama-cpp-python fehlt!",
    },
    "en": {
        "perf_saved": "💾 Performance saved: {path}",
        "perf_save_fail": "⚠ Could not save performance: {error}",
        "model_saved": "💾 Model saved: {model} → {path}",
        "model_save_fail": "⚠ Could not save model: {error}",
        "no_models": "❌ No models found!",
        "auto_model": "🌿 Auto-load: using saved model: {model}",
        "model_header": "🌿 MAAT-KI — Choose model",
        "choose": "\n🔢 Choice: ",
        "invalid_number": "Please enter a valid number.",
        "auto_perf": "🌿 Auto-load performance: n_ctx={n_ctx} temp={temp} top_p={top_p} backend={backend}",
        "perf_header": "⚙️ Performance mode",
        "perf_1": "[1] HIGH       (20k context, stable)",
        "perf_2": "[2] MEDIUM     (16k)",
        "perf_3": "[3] LOW        (12k)",
        "perf_4": "[4] ULTRA LOW  (10k low memory)",
        "perf_chosen": "⚙️ Chosen performance: n_ctx={n_ctx} temp={temp} top_p={top_p} backend={backend}",
        "llm_loading": "🧠 Loading LLM …",
        "llm_model": "   Model:   {model}",
        "llm_backend": "   Backend: {backend}",
        "llm_ctx": "   Context: {ctx}",
        "backend_fallback": "⚠ Backend error, falling back to llama.cpp:\n{error}",
        "llama_missing": "❌ llama-cpp-python is missing!",
    },
}


def _llm_lang() -> str:
    return get_language(tuple(LLM_TEXT.keys()))


def _lt(key: str, **kwargs) -> str:
    lang = _llm_lang()
    template = LLM_TEXT.get(lang, LLM_TEXT["de"]).get(key, LLM_TEXT["de"].get(key, key))
    return template.format(**kwargs) if kwargs else template

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
            + _lt("perf_saved", path=path)
            + Style.RESET_ALL
        )
    except Exception as e:
        print(Fore.RED + _lt("perf_save_fail", error=e) + Style.RESET_ALL)

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
            + _lt("model_saved", model=model_name, path=path)
            + Style.RESET_ALL
        )
    except Exception as e:
        print(Fore.RED + _lt("model_save_fail", error=e) + Style.RESET_ALL)

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
        print(Fore.RED + _lt("no_models") + Style.RESET_ALL)
        raise SystemExit(1)

    saved = load_saved_model_name()
    if saved and saved in models:
        print(
            Fore.GREEN
            + _lt("auto_model", model=saved)
            + Style.RESET_ALL
        )
        return os.path.join(model_dir, saved)

    print("──────────────────────────────────────────────")
    print(_lt("model_header"))
    print("──────────────────────────────────────────────")

    for i, m in enumerate(models, 1):
        print(f"[{i}] {m}")

    while True:
        choice = input(_lt("choose")).strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                chosen = models[idx]
                save_last_model_choice(chosen)
                return os.path.join(model_dir, chosen)
        except Exception:
            pass

        print(Fore.RED + _lt("invalid_number") + Style.RESET_ALL)

# -------------------------------------------------------------
# PERFORMANCE SELECTION
# -------------------------------------------------------------

def choose_performance() -> dict:
    saved = load_saved_perf()
    if isinstance(saved, dict):
        print(
            Fore.GREEN
            + _lt(
                "auto_perf",
                n_ctx=saved.get("n_ctx"),
                temp=saved.get("temperature"),
                top_p=saved.get("top_p"),
                backend=saved.get("backend", "llama"),
            )
            + Style.RESET_ALL
        )
        return saved

    print("\n──────────────────────────────────────────────")
    print(_lt("perf_header"))
    print("──────────────────────────────────────────────")
    print(_lt("perf_1"))
    print(_lt("perf_2"))
    print(_lt("perf_3"))
    print(_lt("perf_4"))

    profiles = {
        "1": dict(n_ctx=20000, temperature=1.0, top_p=0.9),
        "2": dict(n_ctx=16000, temperature=1.0, top_p=0.9),
        "3": dict(n_ctx=12000, temperature=0.9, top_p=0.9),
        "4": dict(n_ctx=10000, temperature=0.8, top_p=0.9),
    }

    choice = input(_lt("choose")).strip()
    perf = profiles.get(choice, profiles["1"])

    perf["backend"] = "llama"

    save_perf(perf)

    print(
        Fore.CYAN
        + _lt(
            "perf_chosen",
            n_ctx=perf["n_ctx"],
            temp=perf["temperature"],
            top_p=perf["top_p"],
            backend=perf["backend"],
        )
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
    print(_lt("llm_loading"))
    print(_lt("llm_model", model=model_path))
    print(_lt("llm_backend", backend=backend))
    print(_lt("llm_ctx", ctx=max_ctx))
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
            + _lt("backend_fallback", error=e)
            + Style.RESET_ALL
        )

        if not model_path.lower().endswith(".gguf"):
            raise

        try:
            from llama_cpp import Llama
        except ImportError:
            print(Fore.RED + _lt("llama_missing") + Style.RESET_ALL)
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
