"""ASGI entry point for the GapSense web service."""

from gapsense.web.app import create_app

app = create_app()

__all__ = ["app", "create_app"]
