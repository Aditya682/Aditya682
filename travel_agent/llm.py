"""Shared Anthropic client. One place to change auth/timeout/retry config."""

from __future__ import annotations

import functools

import anthropic


@functools.lru_cache(maxsize=1)
def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic()
