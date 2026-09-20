"""Entrypoint re-exporting app for platforms expecting main:app at backend root."""

from app.main import app

__all__ = ["app"]
