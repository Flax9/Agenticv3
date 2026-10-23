"""Pembatas percobaan login gagal (masterplan 9.3 butir 2).

Disimpan di memori proses: cukup untuk satu proses uvicorn. Bila backend berjalan dengan
beberapa worker/replika, pindahkan ke Redis agar hitungan dibagi antar proses.
"""

import time
from collections import defaultdict, deque

from app.config import settings


class LoginRateLimiter:
    def __init__(self, max_failures: int, window_seconds: int):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> deque[float]:
        attempts = self._failures[key]
        while attempts and now - attempts[0] > self.window_seconds:
            attempts.popleft()
        return attempts

    def retry_after(self, key: str) -> int:
        """Detik sampai boleh mencoba lagi; 0 bila tidak sedang diblokir."""
        now = time.monotonic()
        attempts = self._prune(key, now)
        if len(attempts) < self.max_failures:
            return 0
        return int(self.window_seconds - (now - attempts[0])) + 1

    def record_failure(self, key: str) -> None:
        self._failures[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)


login_limiter = LoginRateLimiter(settings.login_max_failures, settings.login_lockout_minutes * 60)


class SlidingWindowLimiter:
    """Maksimum `limit` kejadian per `window_seconds` untuk tiap kunci (0 = tanpa batas)."""

    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str) -> int:
        """Catat satu kejadian. Mengembalikan 0 bila diizinkan, atau detik tunggu bila melebihi batas."""
        if self.limit <= 0:
            return 0
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()
        if len(hits) >= self.limit:
            return int(self.window_seconds - (now - hits[0])) + 1
        hits.append(now)
        return 0

    def reset(self) -> None:
        self._hits.clear()


# Melindungi kuota/biaya LLM dari pemakaian berlebihan satu akun
chat_limiter = SlidingWindowLimiter(settings.chat_rate_limit_per_minute)
