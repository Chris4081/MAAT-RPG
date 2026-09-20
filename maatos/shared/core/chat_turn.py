"""A GUI chat counts only after successful generation and visible delivery.

Game events run normally. Message rewards and memory saves are deferred, so
cancelling never requires rolling back a completed battle or story choice.
"""
import threading


class ChatCancelled(BaseException):
    """Control flow, deliberately not swallowed by legacy plugin error handlers."""


class ChatTurn:
    def __init__(self, identifier):
        self.id = identifier
        self.cancelled = threading.Event()
        self.presented = threading.Event()
        self.committed = False
        self._callbacks = []
        self._lock = threading.Lock()

    def cancel(self):
        with self._lock:
            if self.committed:
                return False
            self.cancelled.set()
            self.presented.set()
            return True

    def check(self):
        if self.cancelled.is_set():
            raise ChatCancelled()

    def defer(self, callback):
        self.check()
        if self.committed:
            callback()
        else:
            self._callbacks.append(callback)

    def commit(self):
        with self._lock:
            self.check()
            if self.committed:
                return
            self.committed = True
        callbacks, self._callbacks = self._callbacks, []
        for callback in callbacks:
            callback()


DEFERRED_CHAT_PLUGINS = {
    'achievements', 'emotional_achievements', 'quests', 'maat_fields',
    'dungeon_60', 'dungeon_500', 'dungeon_1000', 'inner_boss_system',
}
