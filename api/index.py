"""Vercel ASGI entry point for the reviewed public GapSense fixture."""

from __future__ import annotations

import os
import sys
from pathlib import Path

repository_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repository_root / "src"))
os.environ.setdefault("ENVIRONMENT", "production")
os.environ.setdefault("GAPSENSE_DATA_PATH", str(repository_root / "fixtures" / "public-data"))

from gapsense.web.app import create_app  # noqa: E402
from gapsense.web.vercel import preserve_forwarded_path  # noqa: E402

app = preserve_forwarded_path(create_app())
