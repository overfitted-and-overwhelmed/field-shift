"""Vercel entry point: Vercel looks for a FastAPI object called ``app`` in this file. The app is in chatbot/api.py."""

from chatbot.api import app

__all__ = ["app"]
