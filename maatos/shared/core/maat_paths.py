# -*- coding: utf-8 -*-
from pathlib import Path
import os
import sys

APP_NAME = "MAAT-RPG"


def _default_app_support_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / APP_NAME

    return Path.home() / ".local" / "share" / APP_NAME


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _dir_from_env(env_name: str, fallback: Path) -> Path:
    env = os.environ.get(env_name)
    if env:
        return _ensure_dir(Path(env))
    return _ensure_dir(fallback)


def get_default_app_support_dir() -> Path:
    return _ensure_dir(_default_app_support_dir())


def get_app_support_dir() -> Path:
    return _dir_from_env("MAAT_APP_SUPPORT_DIR", _default_app_support_dir())


def get_data_dir() -> Path:
    return _dir_from_env("MAAT_DATA_DIR", get_app_support_dir() / "data")


def get_models_dir() -> Path:
    return _dir_from_env("MAAT_MODELS_DIR", get_app_support_dir() / "models")


def get_logs_dir() -> Path:
    return _dir_from_env("MAAT_LOGS_DIR", get_app_support_dir() / "logs")


def get_cache_dir() -> Path:
    return _dir_from_env("MAAT_CACHE_DIR", get_app_support_dir() / "cache")


def get_saves_dir() -> Path:
    return _dir_from_env("MAAT_SAVES_DIR", get_app_support_dir() / "saves")


def get_state_dir() -> Path:
    return _dir_from_env("MAAT_STATE_DIR", get_app_support_dir() / "state")


def get_profiles_dir() -> Path:
    return _ensure_dir(get_default_app_support_dir() / "profiles")


def data_file(name: str) -> str:
    return str(get_data_dir() / name)


def model_file(name: str) -> str:
    return str(get_models_dir() / name)


def log_file(name: str) -> str:
    return str(get_logs_dir() / name)


def cache_file(name: str) -> str:
    return str(get_cache_dir() / name)


def save_file(name: str) -> str:
    return str(get_saves_dir() / name)


def state_file(name: str) -> str:
    return str(get_state_dir() / name)
