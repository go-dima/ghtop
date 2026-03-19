# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, patch


# Sample data fixtures
SAMPLE_ORGS = [
    {"login": "acme-corp"},
    {"login": "my-team"},
]
SAMPLE_USER = {"login": "alice"}

SAMPLE_REPOS = [
    {"name": "backend-api", "updatedAt": "2026-03-19T10:00:00Z"},
    {"name": "frontend", "updatedAt": "2026-03-18T08:00:00Z"},
]

SAMPLE_PRS = [
    {
        "number": 42,
        "title": "fix: auth token expiry",
        "author": {"login": "alice"},
        "createdAt": "2026-03-19T10:00:00Z",
        "headRefName": "fix/auth",
        "labels": [{"name": "bug"}],
        "reviewRequests": [],
    },
    {
        "number": 41,
        "title": "feat: rate limiting",
        "author": {"login": "bob"},
        "createdAt": "2026-03-18T10:00:00Z",
        "headRefName": "feat/rate-limit",
        "labels": [],
        "reviewRequests": [],
    },
]
