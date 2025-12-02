from __future__ import annotations

import random
from pathlib import Path
from typing import Final

import scrapy


class ProxyMiddleware:
    """
    Basic proxy middleware.

    Reads proxies from `proxies.txt` (one URL per line) and assigns a random
    proxy to each outgoing request. If the file is missing or empty, it does
    nothing and never crashes the crawl.
    """

    _default_file: Final[str] = "proxies.txt"

    def __init__(self, proxy_list_file: str | None = None) -> None:
        filename = proxy_list_file or self._default_file
        self.proxies: list[str] = self._load_proxies(filename)

    def _load_proxies(self, filename: str) -> list[str]:
        path = Path(filename)
        if not path.exists():
            return []

        proxies: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            proxies.append(stripped)
        return proxies

    def process_request(self, request: scrapy.Request, spider: scrapy.Spider) -> None:
        if not self.proxies:
            return

        proxy = random.choice(self.proxies)
        request.meta["proxy"] = proxy


class RegionMiddleware:
    """
    Placeholder region middleware.

    Region is currently enforced at the API level via `city_uuid` in
    `AlkotekaSpider`, so this middleware stays unused for now.
    """

    pass
