"""Shared interface every tool adapter implements."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAdapter(ABC):
    #: e.g. "playwright", "selenium", "cypress" — used in filenames/reports
    name: str
    #: file extension for generated test files, including the leading dot
    file_extension: str

    @abstractmethod
    def generate(self, test_def: dict[str, Any]) -> str:
        """Return complete, runnable source code for one intermediate test definition."""
        raise NotImplementedError

    def generate_filename(self, test_def: dict[str, Any]) -> str:
        slug = "".join(c if c.isalnum() else "_" for c in test_def["test_name"].lower())
        while "__" in slug:
            slug = slug.replace("__", "_")
        return f"test_{slug.strip('_')}{self.file_extension}"
