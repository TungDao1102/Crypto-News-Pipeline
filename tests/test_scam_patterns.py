"""Tests for scam patterns — REQ-3.19–3.21."""

import pytest

from src.models import DraftContent
from src.scam_patterns import (
    SCAM_KEYWORDS,
    is_low_confidence,
    is_suspicious,
)


class TestScamKeywords:
    """REQ-3.19: SCAM_KEYWORDS list contains 14+ scam patterns."""

    def test_at_least_14_keywords(self):
        assert len(SCAM_KEYWORDS) >= 14

    def test_required_keywords_present(self):
        required = [
            "pump",
            "dump",
            "get-rich-quick",
            "guaranteed",
        ]
        for kw in required:
            assert kw in SCAM_KEYWORDS, f"Missing required keyword: {kw}"

    def test_all_keywords_are_strings(self):
        for kw in SCAM_KEYWORDS:
            assert isinstance(kw, str), f"Keyword not a string: {kw!r}"
            assert len(kw) > 0, "Empty keyword in list"


class TestIsSuspicious:
    """REQ-3.20: is_suspicious() case-insensitive keyword matching."""

    @pytest.mark.parametrize("suspicious_text", [
        "This is a pump and dump scheme",
        "GET-RICH-QUICK with crypto",
        "Guaranteed returns every time",
        "Double your money in 24 hours",
        "Risk-free investment opportunity",
        "Fast profit guaranteed!",
        "Instant profit no waiting",
        "No loss trading strategy",
        "Guaranteed return on your deposit",
        "Make money fast with this trick",
        "100% profit guaranteed",
        "Get rich now!!",
    ])
    def test_detects_suspicious_texts(self, suspicious_text):
        assert is_suspicious(suspicious_text), f"Should detect: {suspicious_text!r}"

    @pytest.mark.parametrize("safe_text", [
        "Bitcoin reached a new all-time high today",
        "Ethereum 2.0 staking rewards explained",
        "DeFi protocol announces governance vote",
        "Market analysis for the week ahead",
        "New partnership between blockchain projects",
        "",
        "Regular news about cryptocurrency markets",
    ])
    def test_clean_text_not_flagged(self, safe_text):
        assert not is_suspicious(safe_text), f"Should not flag: {safe_text!r}"

    def test_case_insensitive_matching(self):
        """Keywords match regardless of case."""
        assert is_suspicious("PUMP AND DUMP")
        assert is_suspicious("Pump And Dump")
        assert is_suspicious("pump and dump")

    def test_keyword_as_substring_of_legitimate_word(self):
        """Keywords should be matched as substrings via re.search (regex)."""
        # 'pump' is a keyword and appears in 'pumpkin' but is_suspicious
        # uses re.search(re.escape(kw), text) so 'pump' will match 'pumpkin'
        # This is the current behavior — document it as a known limitation.
        # The requirement says "keyword matching" which is substring-based.
        assert is_suspicious("pumpkin spice latte"), (
            "Known behavior: 'pump' in 'pumpkin' triggers match"
        )

    def test_empty_string_not_suspicious(self):
        assert not is_suspicious("")

    def test_keywords_appear_in_non_scam_context(self):
        """Words like 'guaranteed' in benign context are still flagged."""
        assert is_suspicious("Your satisfaction is guaranteed")


class TestIsLowConfidence:
    """REQ-3.21: is_low_confidence checks used_fallback, <100 chars, <3 sentences."""

    def make_draft(self, telegram: str = "", binance_square: str = "") -> DraftContent:
        return DraftContent(
            title_vn="Test",
            telegram_markdown=telegram,
            binance_square_markdown=binance_square,
            used_fallback=False,
        )

    def test_used_fallback_triggers_low_confidence(self):
        """If draft had a fallback model, it's low confidence regardless of content."""
        draft = self.make_draft(
            telegram=(
                "This is a perfectly long text with enough words to pass the"
                " length check and has at least three sentences."
                " Here is another one. And a third one."
            ),
            binance_square="",
        )
        assert is_low_confidence(draft, used_fallback=True)

    def test_body_shorter_than_100_chars_is_low_confidence(self):
        draft = self.make_draft(
            telegram="Short text.",
            binance_square="",
        )
        assert len("Short text.") < 100
        assert is_low_confidence(draft, used_fallback=False)

    def test_body_combines_telegram_and_binance_fields(self):
        """The body is the concatenation of both markdown fields."""
        draft = self.make_draft(
            telegram="Hello. ",
            binance_square="World. ",
        )
        # Combined: "Hello. World. " → 2 sentences, <100 chars → low confidence
        assert is_low_confidence(draft, used_fallback=False)

    def test_body_exactly_100_chars_stripped_is_not_low_confidence_by_length(self):
        """100+ chars alone is not sufficient — must also have >=3 sentences."""
        body = "A" * 99 + "."  # 100 chars, 1 sentence
        draft = self.make_draft(telegram=body, binance_square="")
        # Length >= 100, but only 1 sentence → low confidence due to <3 sentences
        assert is_low_confidence(draft, used_fallback=False)

    def test_long_body_with_three_sentences_is_not_low_confidence(self):
        """Body >=100 chars AND >=3 sentences → not low confidence."""
        body = (
            "Bitcoin reached a new all-time high this week. "
            "Ethereum also saw significant gains across the board. "
            "The overall market sentiment remains bullish for now."
        )
        draft = self.make_draft(telegram=body, binance_square="")
        assert len(body.strip()) >= 100
        assert not is_low_confidence(draft, used_fallback=False), \
            "Long body with 3+ sentences should be high confidence"

    def test_three_sentences_but_short_body_is_low_confidence(self):
        """Even with 3+ sentences, body <100 chars is still low confidence."""
        body = "First sentence. Second sentence. Third sentence."
        draft = self.make_draft(telegram=body, binance_square="")
        assert len(body.strip()) < 100
        assert is_low_confidence(draft, used_fallback=False)

    def test_high_confidence_draft(self):
        """Draft with >=100 chars, >=3 sentences, and no fallback is NOT low confidence."""
        body = (
            "Bitcoin reached a new high today. Ethereum also saw gains."
            " The market is looking bullish overall."
            " Many investors are optimistic about the trend."
        )
        draft = self.make_draft(telegram=body, binance_square="")
        assert len(body.strip()) >= 100
        assert not is_low_confidence(draft, used_fallback=False)

    def test_fewer_than_three_sentences_is_low_confidence_even_if_long(self):
        """A long text with only 1-2 sentences is still low confidence."""
        body = "Bitcoin reached a new high today and Ethereum also saw gains. " * 10
        assert len(body.strip()) >= 100
        body2 = (
            "This is one very long sentence that goes on and on about various"
            " topics without ever using a period to break it up so it remains"
            " as a single sentence even though it is quite long yes indeed it"
            " is very long but it never reaches a period so it should count"
            " as one sentence "
        )
        assert len(body2.strip()) >= 100
        draft2 = self.make_draft(telegram=body2, binance_square="")
        assert is_low_confidence(draft2, used_fallback=False)

    def test_sentence_count_edge_cases(self):
        """Edge cases for sentence splitting."""
        draft = self.make_draft(
            telegram="No punctuation here at all just words",
            binance_square="",
        )
        assert is_low_confidence(draft, used_fallback=False)

        # 3 sentences with ? ! . but <100 chars → still low confidence (length)
        draft2 = self.make_draft(
            telegram="Question? Exclamation! Period.",
            binance_square="",
        )
        assert is_low_confidence(draft2, used_fallback=False), \
            "3 sentences but <100 chars: low confidence due to length"

        # 3 explicit sentences with varied punctuation and >=100 chars → not low confidence
        draft3 = self.make_draft(
            telegram="Is Bitcoin the future of finance? Absolutely! "
                     "Many experts believe blockchain technology will revolutionize "
                     "how we think about money and transactions across the globe. ",
            binance_square="",
        )
        assert len(draft3.telegram_markdown.strip()) >= 100
        assert not is_low_confidence(draft3, used_fallback=False), \
            "3+ sentences with >=100 chars should pass"

    def test_whitespace_only_body_is_low_confidence(self):
        """Body with only whitespace is <100 chars after strip."""
        draft = self.make_draft(telegram="   \n\n   ", binance_square="")
        assert is_low_confidence(draft, used_fallback=False)
