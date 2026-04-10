# -*- coding: utf-8 -*-
from pathlib import Path
import os

APP_NAME = "MAAT-RPG"


def get_app_support_dir() -> Path:
    env = os.environ.get("MAAT_APP_SUPPORT_DIR")
    if env:
        path = Path(env)
    else:
        path = Path.home() / "Library" / "Application Support" / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_data_dir() -> Path:
    path = get_app_support_dir() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_models_dir() -> Path:
    path = get_app_support_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logs_dir() -> Path:
    path = get_app_support_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_cache_dir() -> Path:
    path = get_app_support_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_saves_dir() -> Path:
    path = get_app_support_dir() / "saves"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_state_dir() -> Path:
    path = get_app_support_dir() / "state"
    path.mkdir(parents=True, exist_ok=True)
    return path


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