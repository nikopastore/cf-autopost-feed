#!/usr/bin/env python3
"""
Unit tests for quality gate functionality.
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from build_rss import (
    quality_gate,
    contains_unquoted_I,
    has_banned_phrases,
    sanitize_xline,
    has_emoji,
    add_minimum_emojis
)


class TestQualityGate:
    """Test quality gate validation."""

    def test_rejects_dialogue_markers(self):
        """Should reject content with dialogue markers."""
        rules = {"banned_phrases": []}
        bad_lines = [
            "You: send me your resume. Them: okay!",
            "Q: What should I do? A: Apply now!",
            "You: Tell me more",
            "Them: Here it is"
        ]

        for line in bad_lines:
            ok, reason = quality_gate(line, rules)
            assert not ok, f"Should reject: {line}"
            assert "dialogue" in reason.lower() or "meta" in reason.lower()

    def test_rejects_meta_markers(self):
        """Should reject meta references."""
        rules = {"banned_phrases": []}
        bad_lines = [
            "Check the details in this thread",
            "See below for more info",
        ]

        for line in bad_lines:
            ok, reason = quality_gate(line, rules)
            assert not ok, f"Should reject: {line}"
            assert "meta" in reason.lower() or "dialogue" in reason.lower()

    def test_accepts_clean_second_person(self):
        """Should accept good second-person advice."""
        rules = {"enforce_second_person": True, "banned_phrases": []}
        good_lines = [
            "You can improve your resume by adding metrics.",
            "Your pitch should lead with outcomes.",
            "Focus on what you achieved in numbers."
        ]

        for line in good_lines:
            ok, reason = quality_gate(line, rules)
            assert ok, f"Should accept: {line} (reason: {reason})"

    def test_rejects_missing_second_person(self):
        """Should reject if no second-person signal when enforced."""
        rules = {"enforce_second_person": True, "banned_phrases": []}
        bad_line = "The resume should have metrics and achievements."

        ok, reason = quality_gate(bad_line, rules)
        assert not ok
        assert "second-person" in reason.lower()

    def test_allows_first_person_in_quotes(self):
        """Should allow first-person inside quotes."""
        rules = {
            "allow_first_person_in_quotes_only": True,
            "enforce_second_person": False,
            "banned_phrases": []
        }
        good_line = 'Use: "I improved revenue by 25% through automation."'

        ok, reason = quality_gate(good_line, rules)
        assert ok, f"Should accept quoted first-person (reason: {reason})"

    def test_rejects_unquoted_first_person(self):
        """Should reject first-person outside quotes."""
        rules = {
            "allow_first_person_in_quotes_only": True,
            "banned_phrases": []
        }
        bad_line = "I think you should add metrics to your resume."

        ok, reason = quality_gate(bad_line, rules)
        assert not ok
        assert "first-person" in reason.lower()

    def test_rejects_tense_conflict(self):
        """Should reject tense conflicts like 'when...I achieved'."""
        rules = {"banned_phrases": []}
        bad_lines = [
            "When pitching to investors, I achieved a 50% close rate.",
            "When negotiating salary, I delivered strong results.",
        ]

        for line in bad_lines:
            ok, reason = quality_gate(line, rules)
            assert not ok, f"Should reject: {line}"
            assert "tense conflict" in reason.lower()

    def test_rejects_banned_phrases(self):
        """Should reject content with banned phrases."""
        rules = {"banned_phrases": ["click here", "amazing opportunity", "game changer"]}

        bad_line = "This is an amazing opportunity for your career!"

        ok, reason = quality_gate(bad_line, rules)
        assert not ok
        assert "banned phrase" in reason.lower()


class TestFirstPersonDetection:
    """Test first-person detection logic."""

    def test_detects_unquoted_I(self):
        """Should detect 'I' outside quotes."""
        assert contains_unquoted_I("I think this is good")
        assert contains_unquoted_I("When I was working there")
        assert contains_unquoted_I("Did I mention that?")

    def test_ignores_quoted_I(self):
        """Should ignore 'I' inside quotes."""
        assert not contains_unquoted_I('"I improved metrics by 20%"')
        assert not contains_unquoted_I("Use: 'I achieved great results'")
        assert not contains_unquoted_I('Template: "I led the team"')

    def test_mixed_quoted_and_unquoted(self):
        """Should detect unquoted even with quotes present."""
        assert contains_unquoted_I('I think you should say "I improved X"')
        assert contains_unquoted_I('"I did this" but I also did that')


class TestBannedPhrases:
    """Test banned phrase detection."""

    def test_detects_banned_phrases(self):
        """Should detect banned phrases case-insensitively."""
        banned = ["click here", "amazing", "game changer"]

        assert has_banned_phrases("Click Here for more info", banned)
        assert has_banned_phrases("This is AMAZING", banned)
        assert has_banned_phrases("It's a real game changer", banned)

    def test_ignores_clean_content(self):
        """Should pass content without banned phrases."""
        banned = ["click here", "amazing"]

        assert not has_banned_phrases("Focus on metrics and outcomes", banned)
        assert not has_banned_phrases("Your pitch should be strong", banned)


class TestSanitization:
    """Test content sanitization."""

    def test_removes_dialogue_markers(self):
        """Should strip dialogue markers."""
        result = sanitize_xline("You: What should I do? Them: Apply now!")
        assert "You:" not in result
        assert "Them:" not in result

    def test_removes_urls(self):
        """Should remove URLs."""
        result = sanitize_xline("Check this out https://example.com for more")
        assert "https://example.com" not in result
        assert "Check this out" in result
        assert "for more" in result

    def test_removes_hashtags(self):
        """Should remove hashtags."""
        result = sanitize_xline("Great advice #career #jobsearch #hiring")
        assert "#career" not in result
        assert "#jobsearch" not in result
        assert "Great advice" in result

    def test_collapses_whitespace(self):
        """Should collapse multiple spaces."""
        result = sanitize_xline("Too    many     spaces")
        assert "Too many spaces" == result


class TestEmojiHandling:
    """Test emoji detection and addition."""

    def test_counts_emojis(self):
        """Should count emojis correctly."""
        assert has_emoji("✅ Great advice") >= 1
        assert has_emoji("✅ Great advice 🎯") >= 2
        assert has_emoji("No emojis here") == 0

    def test_adds_minimum_emojis(self):
        """Should add emojis when below minimum."""
        line = "Plain text"
        result = add_minimum_emojis(line, need_min=2)

        # Should have at least 2 emojis now
        assert has_emoji(result) >= 2
        assert "Plain text" in result

    def test_preserves_existing_emojis(self):
        """Should not add if minimum already met."""
        line = "✅ Already has emoji 🎯"
        result = add_minimum_emojis(line, need_min=2)

        # Should be unchanged
        assert result == line


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
