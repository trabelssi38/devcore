"""Immediate admission on one event loop; estimates are not billed tokens."""
import asyncio
import math
import time
from collections import deque


class RateLimitRefusal(Exception):
    def __init__(self, retry_after):
        super().__init__('Local provider admission saturated')
        self.retry_after = retry_after


class SlidingWindowRateLimiter:
    def __init__(self, max_rpm=8, max_tpm=200_000, *, clock=time.monotonic):
        if type(max_rpm) is not int or not 1 <= max_rpm <= 4096:
            raise ValueError('Invalid RPM capacity')
        if type(max_tpm) is not int or not 1 <= max_tpm < (1 << 63):
            raise ValueError('Invalid token capacity')
        self.max_rpm, self.max_tpm, self.clock = max_rpm, max_tpm, clock
        self._admitted = deque()
        self._reported = {}
        self._loop = None
        self._last = None

    def _now(self):
        loop = asyncio.get_running_loop()
        if self._loop is not None and self._loop is not loop:
            raise RuntimeError('Limiter belongs to another event loop')
        now = self.clock()
        if type(now) not in (int, float) or not math.isfinite(now) or (self._last is not None and now < self._last):
            raise ValueError('Invalid monotonic clock')
        self._loop, self._last = loop, now
        while self._admitted and self._admitted[0][0] + 60 <= now:
            self._admitted.popleft()
        self._reported = {end: tokens for end, tokens in self._reported.items() if end + 60 > now}
        return now

    @staticmethod
    def _tokens(value):
        if type(value) is not int or not 0 <= value < (1 << 63):
            raise ValueError('Invalid token count')

    async def wait_if_needed(self, estimated_tokens=500):
        # Compatibility name: no sleep, lock acquisition or network await.
        self._tokens(estimated_tokens)
        now = self._now()
        current = sum(tokens for _, tokens in self._admitted) + sum(self._reported.values())
        if len(self._admitted) >= self.max_rpm or current + estimated_tokens > self.max_tpm:
            expiry = [timestamp + 60 for timestamp, _ in self._admitted]
            expiry.extend(end + 60 for end in self._reported)
            retry = max(1, min(61, math.ceil(min(expiry) - now))) if expiry else 60
            raise RateLimitRefusal(retry)
        self._admitted.append((now, estimated_tokens))

    async def record_tokens(self, token_count):
        self._tokens(token_count)
        now = self._now()
        if token_count:
            # Round expiry upwards: at most 61 buckets, conservative by <1s.
            end = math.ceil(now)
            self._reported[end] = min(self.max_tpm + 1, self._reported.get(end, 0) + token_count)

    def snapshot(self):
        return {'scope': 'limiter_instance', 'reserved_requests': len(self._admitted),
            'reported_buckets': len(self._reported), 'max_rpm': self.max_rpm,
            'max_tpm': self.max_tpm}
