"""Syntax Corporation © 2026 — EBS AP PAF — pytest fixtures."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SAMPLE_DIR = ROOT / "sample_data"


@pytest.fixture
def sample_dir() -> Path:
    return SAMPLE_DIR


@pytest.fixture
def acme_invoice_text() -> str:
    return (SAMPLE_DIR / "invoice_acme_widgets.txt").read_text()


@pytest.fixture
def and_invoice_text() -> str:
    return (SAMPLE_DIR / "invoice_advanced_network_3495.txt").read_text()


@pytest.fixture
def mock_repo(sample_dir):
    from ebs_ap_paf.repository import MockEBSRepository
    return MockEBSRepository(sample_dir)


def _live_enabled() -> bool:
    return bool(os.environ.get("EBS_PASSWORD")) and \
        os.environ.get("EBS_RUN_LIVE", "").lower() in ("1", "true", "yes")


@pytest.fixture
def live_settings():
    from ebs_ap_paf.config import Settings
    return Settings.resolve(overrides={"backend": "live"})


requires_live = pytest.mark.skipif(
    not _live_enabled(),
    reason="live EBS tests need EBS_PASSWORD and EBS_RUN_LIVE=1",
)
