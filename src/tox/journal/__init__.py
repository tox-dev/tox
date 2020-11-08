"""This module handles collecting and persisting in json format a tox session"""
from .env import EnvJournal
from .main import Journal

__all__ = (
    "Journal",
    "EnvJournal",
)
