# -*- coding: utf-8 -*-
"""Shared audio helpers for macOS-backed playback."""

import json
import os
import shutil
import subprocess
import threading
import time

from .maat_paths import state_file


def _afplay_path() -> str | None:
    return shutil.which("afplay")


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
        return bool(_afplay_path())

    def set_track(self, track_path: str | None):
        self.track_path = track_path

    def play_once(self, track_path: str | None = None) -> bool:
        if track_path is not None:
            self.track_path = track_path

        if not self.track_path or not os.path.isfile(self.track_path):
            return False

        afplay = _afplay_path()
        if not afplay:
            return False

        self.stop()

        try:
            proc = subprocess.Popen(
                [afplay, self.track_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            return False

        with self._lock:
            self._proc = proc

        return True

    def start_loop(self, track_path: str | None = None) -> bool:
        if track_path is not None:
            self.track_path = track_path

        if not self.track_path or not os.path.isfile(self.track_path):
            return False

        afplay = _afplay_path()
        if not afplay:
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
                        proc = subprocess.Popen(
                            [afplay, local_track_path],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        with self._lock:
                            if local_run_id != self._run_id or self._stop_event.is_set():
                                try:
                                    proc.terminate()
                                except Exception:
                                    pass
                                break
                            self._proc = proc

                        while proc.poll() is None:
                            with self._lock:
                                should_stop = self._stop_event.is_set() or local_run_id != self._run_id
                            if should_stop:
                                try:
                                    proc.terminate()
                                except Exception:
                                    pass
                                break
                            time.sleep(0.05)
                    except Exception:
                        time.sleep(0.2)
                    finally:
                        if proc is not None:
                            if proc.poll() is None:
                                try:
                                    proc.terminate()
                                    proc.wait(timeout=1)
                                except Exception:
                                    try:
                                        proc.kill()
                                    except Exception:
                                        pass
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

        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=1)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2)

        with self._lock:
            if self._thread is thread:
                self._thread = None
