from dataclasses import dataclass
from datetime import datetime as dt
from datetime import timedelta as td
from typing import Optional

import pytest  # noqa: F401


@dataclass
class StoredString:
    upd: dt
    val: str
    ttl: Optional[td] = None
    exp: Optional[dt] = None


class FakeRedisCache:
    def __init__(self):
        self.store = {}

    def __call__(self):
        """this is so we can "pretend" to instantiate"""
        return self

    def set(self, key: str, value: str) -> bool:
        self.store[key] = StoredString(upd=dt.now(), val=value)
        return True

    def setex(self, key: str, value: str = "", expiry: td = td(hours=24)) -> bool:
        self.store[key] = StoredString(upd=dt.now(), val=value, ttl=expiry, exp=dt.now() + expiry)
        return True

    def exists(self, key: str) -> bool:
        return key in self.store

    def get(self, key: str) -> Optional[str]:
        data = self._get(key)
        if data is None:
            return None
        return data.val

    def _get(self, key: str) -> Optional[StoredString]:
        """internal method for testing purposes"""
        data = self.store.get(key, None)
        if data is None:
            return None
        if data.exp < dt.now():
            self.delete(key)
            return None
        return data

    def delete(self, key: str) -> None:
        if key in self.store:
            del self.store[key]
