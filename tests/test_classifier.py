"""
tests/test_classifier.py — Unit tests for the file classifier.
"""

import pytest
from backend.core.classifier import FileClassifier, CustomRule, classify_file


class TestDefaultClassification:
    def test_image_extensions(self):
        for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic"]:
            assert classify_file(f"photo{ext}", ext) == "Images", f"Failed for {ext}"

    def test_video_extensions(self):
        for ext in [".mp4", ".avi", ".mkv", ".mov"]:
            assert classify_file(f"video{ext}", ext) == "Videos"

    def test_audio_extensions(self):
        for ext in [".mp3", ".wav", ".flac", ".aac"]:
            assert classify_file(f"song{ext}", ext) == "Audio"

    def test_document_extensions(self):
        for ext in [".pdf", ".docx", ".txt", ".xlsx"]:
            assert classify_file(f"doc{ext}", ext) == "Documents"

    def test_code_extensions(self):
        for ext in [".py", ".js", ".ts", ".rs", ".go"]:
            assert classify_file(f"main{ext}", ext) == "Code"

    def test_archive_extensions(self):
        for ext in [".zip", ".tar", ".7z", ".rar"]:
            assert classify_file(f"archive{ext}", ext) == "Archives"

    def test_unknown_extension_returns_others(self):
        assert classify_file("mystery.xyz", ".xyz") == "Others"

    def test_no_extension(self):
        assert classify_file("Makefile", "") == "Others"


class TestCustomRules:
    def _make_classifier(self, rules):
        return FileClassifier(custom_rules=rules)

    def test_extension_rule_overrides_default(self):
        rule = CustomRule(
            id=1, name="PDF as Finance", pattern=".pdf",
            match_type="extension", category="Finance",
            target_folder="Finance", priority=100, enabled=True,
        )
        clf = self._make_classifier([rule])
        result = clf.classify("budget.pdf", ".pdf")
        assert result.category == "Finance"
        assert result.rule_name == "PDF as Finance"
        assert result.confidence == 1.0

    def test_glob_rule_matches(self):
        rule = CustomRule(
            id=2, name="Invoice glob", pattern="*invoice*",
            match_type="glob", category="Invoices",
            target_folder="Finance/Invoices", priority=50, enabled=True,
        )
        clf = self._make_classifier([rule])
        result = clf.classify("2024_invoice_001.pdf")
        assert result.category == "Invoices"

    def test_regex_rule_matches(self):
        rule = CustomRule(
            id=3, name="Tax files", pattern=r"tax_\d{4}",
            match_type="regex", category="Tax",
            target_folder="Finance/Tax", priority=50, enabled=True,
        )
        clf = self._make_classifier([rule])
        result = clf.classify("tax_2023.pdf")
        assert result.category == "Tax"

    def test_disabled_rule_is_skipped(self):
        rule = CustomRule(
            id=4, name="Disabled", pattern=".pdf",
            match_type="extension", category="ShouldNotMatch",
            target_folder="X", priority=999, enabled=False,
        )
        clf = self._make_classifier([rule])
        result = clf.classify("doc.pdf", ".pdf")
        # Should fall through to default
        assert result.category == "Documents"

    def test_priority_ordering(self):
        low = CustomRule(
            id=5, name="Low priority", pattern=".pdf",
            match_type="extension", category="LowCat",
            target_folder="Low", priority=10, enabled=True,
        )
        high = CustomRule(
            id=6, name="High priority", pattern=".pdf",
            match_type="extension", category="HighCat",
            target_folder="High", priority=100, enabled=True,
        )
        clf = self._make_classifier([low, high])
        result = clf.classify("file.pdf", ".pdf")
        assert result.category == "HighCat"
