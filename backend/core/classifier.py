"""
core/classifier.py — Rule-based file classifier.

Priority order:
  1. User-defined custom rules (loaded from DB at startup)
  2. Default extension → category table (from config)
  3. Fallback: "Others"

AI-ready: ClassificationResult carries a confidence float so a future
ML model can drop in as a second-stage classifier.
"""

from __future__ import annotations

import fnmatch
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from backend.config import DEFAULT_CATEGORY, EXT_TO_CATEGORY

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class ClassificationResult:
    category: str
    target_folder: str
    confidence: float       # 0.0–1.0 (1.0 = rule-based exact match)
    rule_name: str | None   # None = default classification


@dataclass(slots=True)
class CustomRule:
    """In-memory representation of a user-defined Rule from the DB."""

    id: int
    name: str
    pattern: str
    match_type: str     # "glob" | "regex" | "extension"
    category: str
    target_folder: str
    priority: int
    enabled: bool

    # Compiled pattern, set lazily
    _compiled: re.Pattern | None = None

    def matches(self, filename: str, extension: str) -> bool:
        if not self.enabled:
            return False
        try:
            if self.match_type == "extension":
                return extension.lower() == self.pattern.lower()
            elif self.match_type == "glob":
                return fnmatch.fnmatch(filename.lower(), self.pattern.lower())
            elif self.match_type == "regex":
                if self._compiled is None:
                    self._compiled = re.compile(self.pattern, re.IGNORECASE)
                return bool(self._compiled.search(filename))
        except Exception as exc:
            logger.warning("Rule %r match error: %s", self.name, exc)
        return False


class FileClassifier:
    """
    Stateful classifier that holds custom rules in memory.

    reload_rules() must be called after DB changes to pick up updates
    without restarting the service.
    """

    def __init__(self, custom_rules: list[CustomRule] | None = None) -> None:
        self._rules: list[CustomRule] = sorted(
            custom_rules or [], key=lambda r: r.priority, reverse=True
        )

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def reload_rules(self, rules: list[CustomRule]) -> None:
        self._rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        logger.info("Classifier reloaded with %d custom rules", len(self._rules))

    def classify(self, filename: str, extension: str | None = None) -> ClassificationResult:
        """Return the best classification for a file."""
        if extension is None:
            extension = Path(filename).suffix.lower()

        # 1. Check custom rules (highest-priority first)
        for rule in self._rules:
            if rule.matches(filename, extension):
                return ClassificationResult(
                    category=rule.category,
                    target_folder=rule.target_folder,
                    confidence=1.0,
                    rule_name=rule.name,
                )

        # 2. Default extension map
        category = EXT_TO_CATEGORY.get(extension.lower())
        if category:
            return ClassificationResult(
                category=category,
                target_folder=category,
                confidence=0.95,
                rule_name=None,
            )

        # 3. Fallback
        return ClassificationResult(
            category=DEFAULT_CATEGORY,
            target_folder=DEFAULT_CATEGORY,
            confidence=0.5,
            rule_name=None,
        )


# ---------------------------------------------------------------------------
# Module-level convenience function used by the scanner (no custom rules)
# ---------------------------------------------------------------------------
_default_classifier = FileClassifier()


def classify_file(filename: str, extension: str) -> str:
    """Fast path used by the scanner — returns just the category string."""
    return _default_classifier.classify(filename, extension).category
