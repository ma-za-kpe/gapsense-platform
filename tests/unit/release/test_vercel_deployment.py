"""Repository contracts for the explicit Vercel production adapter."""

import json
from pathlib import Path


def test_vercel_configuration_keeps_promotion_explicit_and_routes_the_full_stack() -> None:
    """The reviewed file configuration must override stale dashboard settings."""
    repository_root = Path(__file__).resolve().parents[3]
    configuration = json.loads((repository_root / "vercel.json").read_text(encoding="utf-8"))

    assert configuration["git"] == {"deploymentEnabled": False}
    assert configuration["framework"] == "vite"
    assert configuration["outputDirectory"] == "public"
    assert configuration["buildCommand"].endswith("npm --prefix frontend run build:vercel")
    assert configuration["functions"]["api/index.py"]["includeFiles"] == ("fixtures/public-data/**")
    assert configuration["rewrites"] == [
        {
            "source": "/api/(.*)",
            "destination": "/api/index?_path=$1",
        },
        {
            "source": "/curriculum",
            "destination": "/",
        },
    ]
