"""
Prompt Library Loader

Loads AI prompt templates from gapsense-data repo into memory.

Why in-memory vs database:
- Small size (~50KB, 13 prompts)
- Frequently accessed (every AI call)
- No complex queries needed
- Version tracked in JSON (not runtime data)

Architecture:
- Load once at app startup
- Keep in memory as singleton
- Fast O(1) lookup by prompt_id
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gapsense.config import settings


class PromptLibrary:
    """In-memory prompt library loaded from JSON.

    Provides fast access to AI prompt templates.
    """

    def __init__(self, prompt_library_path: Path | None = None):
        """Initialize prompt library.

        Args:
            prompt_library_path: Path to prompt library JSON.
                                 Defaults to settings.prompt_library_path
        """
        self.path = prompt_library_path or settings.prompt_library_path
        self.prompts: dict[str, dict[str, Any]] = {}
        self.metadata: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load prompts from JSON file."""
        if not self.path.exists():
            raise FileNotFoundError(
                f"Prompt library not found: {self.path}\n"
                f"Make sure GAPSENSE_DATA_PATH points to gapsense-data repo."
            )

        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)

        # Extract metadata
        self.metadata = {
            "version": data.get("version", "unknown"),
            "last_updated": data.get("last_updated"),
            "total_prompts": len(data.get("prompts", [])),
        }

        # Build prompt lookup dict: prompt_id → prompt_data
        for prompt in data.get("prompts", []):
            prompt_id = prompt["prompt_id"]
            self.prompts[prompt_id] = prompt

    def get_prompt(self, prompt_id: str) -> dict[str, Any]:
        """Get prompt by ID.

        Args:
            prompt_id: Prompt identifier (e.g., 'DIAG-001', 'PARENT-002')

        Returns:
            Prompt data dict with keys:
                - prompt_id: str
                - name: str
                - category: str
                - version: str
                - system_prompt: str
                - user_template: str (optional)
                - output_schema: dict (optional)
                - model: str
                - temperature: float
                - max_tokens: int

        Raises:
            KeyError: If prompt_id not found
        """
        if prompt_id not in self.prompts:
            available = ", ".join(sorted(self.prompts.keys()))
            raise KeyError(
                f"Prompt '{prompt_id}' not found in library.\nAvailable prompts: {available}"
            )

        return self.prompts[prompt_id]

    def get_system_prompt(self, prompt_id: str) -> str:
        """Get system prompt text only.

        Args:
            prompt_id: Prompt identifier

        Returns:
            System prompt string
        """
        prompt = self.get_prompt(prompt_id)
        result = prompt["system_prompt"]
        assert isinstance(result, str)
        return result

    def get_user_template(self, prompt_id: str) -> str | None:
        """Get user message template.

        Args:
            prompt_id: Prompt identifier

        Returns:
            User template string with {{placeholders}}, or None if not defined
        """
        return self.get_prompt(prompt_id).get("user_template")

    def list_prompts(self, category: str | None = None) -> list[str]:
        """List all prompt IDs, optionally filtered by category.

        Args:
            category: Filter by category (diagnostic, parent_engagement, guard, etc.)

        Returns:
            List of prompt IDs
        """
        if category is None:
            return sorted(self.prompts.keys())

        return sorted(
            prompt_id
            for prompt_id, prompt in self.prompts.items()
            if prompt.get("category") == category
        )

    def get_prompt_config(self, prompt_id: str) -> dict[str, Any]:
        """Get AI configuration for prompt (model, temperature, max_tokens).

        Args:
            prompt_id: Prompt identifier

        Returns:
            Dict with:
                - model: str
                - temperature: float
                - max_tokens: int
        """
        prompt = self.get_prompt(prompt_id)
        return {
            "model": prompt.get("model", "claude-sonnet-4-5"),
            "temperature": prompt.get("temperature", 0.3),
            "max_tokens": prompt.get("max_tokens", 2048),
        }

    def __len__(self) -> int:
        """Return number of prompts in library."""
        return len(self.prompts)

    def __contains__(self, prompt_id: str) -> bool:
        """Check if prompt exists."""
        return prompt_id in self.prompts

    def __repr__(self) -> str:
        """String representation."""
        return f"PromptLibrary(version={self.metadata['version']}, prompts={len(self.prompts)})"


# Global singleton instance
_prompt_library: PromptLibrary | None = None


def get_prompt_library(force_reload: bool = False) -> PromptLibrary:
    """Get singleton prompt library instance.

    Args:
        force_reload: Force reload from disk (default: False)

    Returns:
        PromptLibrary instance
    """
    global _prompt_library

    if _prompt_library is None or force_reload:
        _prompt_library = PromptLibrary()

    return _prompt_library


def reload_prompt_library() -> PromptLibrary:
    """Reload prompt library from disk.

    Useful for hot-reloading during development or after updating prompts.

    Returns:
        Reloaded PromptLibrary instance
    """
    return get_prompt_library(force_reload=True)
