"""Small bounded in-memory store for the demonstrator."""

from collections import deque
from threading import Lock


class IncidentStore:
    def __init__(self, limit=100):
        self._items = deque(maxlen=limit)
        self._lock = Lock()

    def add(self, incident):
        with self._lock:
            self._items.appendleft(incident)

    def list_all(self):
        with self._lock:
            return list(self._items)

    def get(self, incident_id):
        with self._lock:
            return next(
                (item for item in self._items if item["id"] == incident_id),
                None,
            )
