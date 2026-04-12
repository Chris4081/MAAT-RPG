# -*- coding: utf-8 -*-
"""Shared audio helpers with afplay-first playback and Linux fallbacks."""

import json
import os
import shutil
import subprocess
import threading
import time

from .maat_paths import state_file


_AUDIO_PROCESS_NAMES = ("afplay", "ffplay", "mpg123", "aplay")


def _afplay_path() -> str | None:
    return shutil.which("afplay")


def _audio_extension(track_path: str | None) -> str:
    return os.path.splitext(track_path or "")[1].lower()


def _audio_command(track_path: str | None) -> list[str] | None:
    if not track_path:
        return None

    afplay = _afplay_path()
    if afplay:
        return [afplay, track_path]

    ffplay = shutil.which("ffplay")
    if ffplay:
        return [ffplay, "-nodisp", "-autoexit", "-loglevel", "quiet", track_path]

    ext = _audio_extension(track_path)

    mpg123 = shutil.which("mpg123")
    if mpg123 and ext in {".mp3", ".mp2", ".mp1"}:
        return [mpg123, "-q", track_path]

    aplay = shutil.which("aplay")
    if aplay and ext in {".wav", ".au", ".voc"}:
        return [aplay, "-q", track_path]

    return None


def audio_available(track_path: str | None = None) -> bool:
    if track_path:
        return _audio_command(track_path) is not None
    return any(shutil.which(name) for name in _AUDIO_PROCESS_NAMES)


def play_audio_process(track_path: str | None) -> subprocess.Popen | None:
    if not track_path or not os.path.isfile(track_path):
        return None

    command = _audio_command(track_path)
    if not command:
        return None

    try:
        return subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return None


def stop_audio_process(proc: subprocess.Popen | None, timeout: float = 1.0):
    if proc is None or proc.poll() is not None:
        return

    try:
        proc.terminate()
        proc.wait(timeout=timeout)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def stop_all_audio_backends():
    pkill = shutil.which("pkill")
    if pkill:
        for name in _AUDIO_PROCESS_NAMES:
            try:
                subprocess.call([pkill, "-x", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        return

    killall = shutil.which("killall")
    if killall:
        for name in _AUDIO_PROCESS_NAMES:
            try:
                subprocess.call([killall, name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass


def music_enabled(default: bool = True) -> bool:
    try:
        with open(state_file("settings_state.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        return bool(data.get("music_enabled", default))
    except Exception:
        return bool(default)


class ManagedAudioPlayer:
    def __init__(self, track_path: str | None = None):
        self.track_path = track_path
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._run_id = 0

    def is_available(self) -> bool:
        return audio_available(self.track_path)

    def set_track(self, track_path: str | None):
        self.track_path = track_path

    def play_once(self, track_path: str | None = None) -> bool:
        if track_path is not None:
            self.track_path = track_path

        if not self.track_path or not os.path.isfile(self.track_path):
            return False

        if not audio_available(self.track_path):
            return False

        self.stop()

        proc = play_audio_process(self.track_path)
        if proc is None:
            return False

        with self._lock:
            self._proc = proc

        return True

    def start_loop(self, track_path: str | None = None) -> bool:
        if track_path is not None:
            self.track_path = track_path

        if not self.track_path or not os.path.isfile(self.track_path):
            return False

        if not audio_available(self.track_path):
            return False

        self.stop()

        with self._lock:
            self._stop_event.clear()
            self._run_id += 1
            run_id = self._run_id
            track_path = self.track_path

        def _runner(local_run_id: int, local_track_path: str):
            current = threading.current_thread()
            try:
                while True:
                    with self._lock:
                        should_stop = self._stop_event.is_set() or local_run_id != self._run_id
                    if should_stop:
                        break

                    proc = None
                    try:
                        proc = play_audio_process(local_track_path)
                        if proc is None:
                            time.sleep(0.2)
                            continue
                        with self._lock:
                            if local_run_id != self._run_id or self._stop_event.is_set():
                                stop_audio_process(proc)
                                break
                            self._proc = proc

                        while proc.poll() is None:
                            with self._lock:
                                should_stop = self._stop_event.is_set() or local_run_id != self._run_id
                            if should_stop:
                                stop_audio_process(proc)
                                break
                            time.sleep(0.05)
                    except Exception:
                        time.sleep(0.2)
                    finally:
                        if proc is not None:
                            stop_audio_process(proc)
                            with self._lock:
                                if self._proc is proc:
                                    self._proc = None
            finally:
                with self._lock:
                    if self._thread is current:
                        self._thread = None
                    if local_run_id == self._run_id:
                        self._proc = None

        thread = threading.Thread(target=_runner, args=(run_id, track_path), daemon=True)
        with self._lock:
            self._thread = thread
        thread.start()
        return True

    def stop(self):
        with self._lock:
            self._run_id += 1
            self._stop_event.set()
            proc = self._proc
            thread = self._thread
            self._proc = None

        stop_audio_process(proc)

        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2)

        with self._lock:
            if self._thread is thread:
                self._thread = None
