# -*- coding: utf-8 -*-
"""
Kleine Audio-Helfer fuer lokale afplay-Wiedergabe auf macOS.

Ziel:
- nur eigene Prozesse stoppen
- optionales Looping ohne globales killall
- fail-safe, wenn afplay nicht vorhanden ist
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time


def _afplay_path() -> str | None:
    return shutil.which("afplay")


class ManagedAudioPlayer:
    def __init__(self, track_path: str | None = None):
        self.track_path = track_path
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

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
            self._proc = subprocess.Popen(
                [afplay, self.track_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            self._proc = None
            return False

    def start_loop(self, track_path: str | None = None) -> bool:
        if track_path is not None:
            self.track_path = track_path

        if not self.track_path or not os.path.isfile(self.track_path):
            return False

        afplay = _afplay_path()
        if not afplay or self._thread is not None:
            return False

        self._stop_event.clear()

        def _runner():
            while not self._stop_event.is_set():
                try:
                    self._proc = subprocess.Popen(
                        [afplay, self.track_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    while self._proc.poll() is None and not self._stop_event.is_set():
                        time.sleep(0.1)
                except Exception:
                    time.sleep(0.5)
                finally:
                    if self._proc is not None and self._proc.poll() is None:
                        try:
                            self._proc.terminate()
                        except Exception:
                            pass
                    self._proc = None

        self._thread = threading.Thread(target=_runner, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop_event.set()

        proc = self._proc
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

        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=1)
