"""
utils_http.py — Shared HTTP client for StackScreener P1 modules.

Centralises User-Agent headers so modules don't repeat them inline.
Each module instantiates one HttpClient at import time with its own headers.
"""
from __future__ import annotations

import requests


class HttpClient:
    """Thin wrapper around requests.get that injects a default headers dict.

    Pass explicit headers= to override for a single call.
    """

    def __init__(self, headers: dict[str, str]) -> None:
        self.headers = headers

    def get(self, url: str, **kwargs) -> requests.Response:
        if "headers" not in kwargs:
            kwargs["headers"] = self.headers
        return requests.get(url, **kwargs)

    def get_json(self, url: str, **kwargs) -> dict:
        resp = self.get(url, **kwargs)
        resp.raise_for_status()
        return resp.json()
