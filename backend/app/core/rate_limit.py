"""役割: エンドポイントのレート制限（インメモリのスライディングウィンドウ）

Brevo によるメール送信や Discord への投稿など、外部サービスへの送信を起こすエンドポイントの連打を防ぐ（#82）。
カウントはプロセスのメモリに持つため、再起動でリセットされ、複数プロセス・複数レプリカの間では共有されない
（Backend が 1 プロセスで動く前提。レプリカを増やす場合は共有ストアへの移行が必要）。
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from collections import deque
from typing import Callable

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


class RateLimitExceededError(Exception):
	"""上限に達した。retry_after は次に受け付けられるまでの秒数"""

	def __init__(self, retry_after: float):
		super().__init__("Rate limit exceeded")
		self.retry_after = retry_after


class SlidingWindowRateLimiter:
	"""キーごとに、直近 window_seconds 秒の受け付け回数を max_requests 回までに制限する"""

	def __init__(self, max_requests: int, window_seconds: float, clock: Callable[[], float] = time.monotonic):
		self.max_requests = max_requests
		self.window_seconds = window_seconds
		self._clock = clock
		self._hits: dict[str, deque[float]] = {}
		self._lock = asyncio.Lock()

	async def hit(self, key: str) -> None:
		"""1 回分を記録する。上限に達していれば記録せずに RateLimitExceededError を送出する"""
		async with self._lock:
			now = self._clock()
			self._prune(now)
			hits = self._hits.get(key)
			if hits is not None and len(hits) >= self.max_requests:
				raise RateLimitExceededError(hits[0] + self.window_seconds - now)
			self._hits.setdefault(key, deque()).append(now)

	def reset(self) -> None:
		self._hits.clear()

	def _prune(self, now: float) -> None:
		# 窓の外に出た記録を捨て、記録がなくなったキーは消す（キーが増え続けてメモリを使い切らないように）
		threshold = now - self.window_seconds
		for key in list(self._hits):
			hits = self._hits[key]
			while hits and hits[0] <= threshold:
				hits.popleft()
			if not hits:
				del self._hits[key]


def get_client_ip(request: Request) -> str:
	"""クライアントの IP アドレスを返す。

	本番では ingress が X-Forwarded-For を付けるため、その最右端（ingress が付けた値）を使う。
	Frontend の Server Action 経由の呼び出しは、Frontend が受け取った X-Forwarded-For を転送してくる。
	X-Forwarded-For がなければ（ローカル環境など）接続元のアドレスを使う。
	"""
	forwarded_for = request.headers.get("x-forwarded-for", "")
	addresses = [address.strip() for address in forwarded_for.split(",") if address.strip()]
	if addresses:
		return addresses[-1]
	return request.client.host if request.client else "unknown"


async def enforce_rate_limit(limiter: SlidingWindowRateLimiter, key: str, endpoint: str) -> None:
	"""上限に達していれば 429 を返す。ログにはキー（IP アドレス等）を出さない"""
	try:
		await limiter.hit(key)
	except RateLimitExceededError as e:
		logger.warning("Rate limit exceeded: endpoint=%s", endpoint)
		raise HTTPException(
			status_code=429,
			detail="Too many requests. Please try again later.",
			headers={"Retry-After": str(max(1, math.ceil(e.retry_after)))},
		)
