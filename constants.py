#!/usr/bin/env python3
"""
Constants and configuration values for Career Forge.
Centralizes magic numbers and provides documentation for each value.
"""

# ========== Content Length Limits ==========

class ContentLimits:
    """Character limits for various content types."""

    # X/Twitter limits
    X_CHAR_LIMIT = 280  # Official X character limit
    X_RESERVED_SPACE = 50  # Reserve space for links, etc.
    X_EFFECTIVE_LIMIT = 230  # Actual limit for content generation

    # Description limits
    DESC_TITLE_MAX = 80  # Hook/title length
    DESC_POINT_MAX = 80  # Individual bullet point length
    DESC_CTA_MAX = 110  # Call-to-action length

    # Emoji requirements
    MIN_EMOJIS = 2  # Minimum emojis per post
    MAX_EMOJIS = 4  # Maximum emojis per post


# ========== Unicode Ranges ==========

class UnicodeRanges:
    """Unicode code point ranges for character detection."""

    # Emoji ranges (simplified - covers most common emojis)
    EMOJI_START = 0x1F300  # Start of emoji block
    EMOJI_END = 0x1FAFF    # End of extended emoji block

    # Additional emoji ranges
    EMOJI_SYMBOLS_START = 0x2600  # Miscellaneous symbols
    EMOJI_SYMBOLS_END = 0x26FF

    # Variation selectors (affect emoji rendering)
    VARIATION_SELECTOR_START = 0xFE00
    VARIATION_SELECTOR_END = 0xFE0F

    # Skin tone modifiers
    SKIN_TONE_START = 0x1F3FB
    SKIN_TONE_END = 0x1F3FF

    # Regional indicators (flags)
    REGIONAL_INDICATOR_START = 0x1F1E6
    REGIONAL_INDICATOR_END = 0x1F1FF


# ========== Style Weights ==========

class StyleWeights:
    """Default weights for content style selection."""

    DEFAULT_WEIGHTS = {
        "coach_tip": 1.4,        # Higher weight = selected more often
        "recruiter_inside": 1.3,
        "checklist": 1.1,
        "mistake_fix": 1.1,
        "template_drop": 1.0,
        "data_bite": 0.9,
        "challenge": 0.8,        # Lower weight = selected less often
    }

    # Minimum weight to prevent division by zero
    MIN_WEIGHT = 0.01


# ========== Duplicate Detection ==========

class DuplicateGuard:
    """Settings for duplicate content detection."""

    NGRAM_SIZE = 5  # N-gram size for similarity detection
    SIMILARITY_THRESHOLD = 0.8  # Jaccard similarity threshold (0-1)
    HISTORY_SIZE = 200  # Number of recent posts to check

    # When duplicate detected, reduce style weight
    DUPLICATE_STYLE_PENALTY = 0.35


# ========== Quality Gates ==========

class QualityRules:
    """Default quality gate rules."""

    # Content requirements
    MIN_EMOJIS = 2
    REQUIRE_NUMBER_IN_TITLE = False  # Require %/$ in title
    ENFORCE_SECOND_PERSON = False    # Require 'you/your'
    ALLOW_FIRST_PERSON_IN_QUOTES_ONLY = False

    # Banned patterns (checked case-insensitively)
    DEFAULT_BANNED_PHRASES = [
        "click here",
        "in this thread",
        "see below",
        "You:",
        "Them:",
        "Q:",
        "A:",
    ]


# ========== OpenAI Configuration ==========

class OpenAIConfig:
    """OpenAI API configuration."""

    DEFAULT_MODEL = "gpt-4o"  # Primary model
    FALLBACK_MODELS = ["gpt-4o", "gpt-4o-mini"]  # Models to try in order
    TEMPERATURE = 0.6  # Creativity vs consistency (0-1)
    MAX_RETRIES = 3  # Number of retry attempts
    RETRY_MIN_WAIT = 4  # Minimum wait between retries (seconds)
    RETRY_MAX_WAIT = 60  # Maximum wait between retries (seconds)


# ========== File Paths ==========

class Paths:
    """Standard file paths."""

    # Configuration
    CONFIG = "ops/config.json"
    RULES = "ops/rules.json"
    BANDIT = "ops/bandit.json"

    # Content
    TAGS = "content/tags.json"
    TRENDS = "content/trends.json"
    TOPICS = "content/seeds_topics.txt"

    # Feeds
    FEED_MAIN = "rss.xml"
    FEED_X = "rss_x.xml"
    FEED_X_LIVE = "rss_x_live.xml"
    FEED_FACEBOOK = "rss_fb.xml"
    FEED_FACEBOOK_LIVE = "rss_fb_live.xml"
    FEED_LINKEDIN = "rss_li.xml"
    FEED_LINKEDIN_LIVE = "rss_li_live.xml"

    # Analytics
    FINGERPRINTS = "analytics/fingerprints.json"
    POSTS_FEATURES = "analytics/posts_features.csv"
    FEATURE_SUMMARY = "analytics/feature_summary.csv"
    ENGAGEMENT = "analytics/engagement.csv"

    # Backups
    BACKUP_DIR = "backups"
    BACKUP_KEEP_COUNT = 30


# ========== Platform-Specific Limits ==========

class PlatformLimits:
    """Character limits for different social platforms."""

    # X/Twitter
    X_FULL_LIMIT = 280
    X_SAFE_LIMIT = 260  # Leave buffer for variations

    # LinkedIn
    LINKEDIN_POST_LIMIT = 3000
    LINKEDIN_SAFE_LIMIT = 1300  # Recommended for engagement

    # Facebook
    FACEBOOK_POST_LIMIT = 63206  # Technical limit
    FACEBOOK_SAFE_LIMIT = 500  # Optimal for engagement


# ========== Timing Configuration ==========

class Timing:
    """Time-related constants."""

    # Health check thresholds
    MAX_POST_AGE_HOURS = 24  # Alert if no post in this many hours

    # Backup retention
    BACKUP_KEEP_DAYS = 30

    # Analytics windows
    ANALYTICS_LOOKBACK_DAYS = 7


# ========== Branding ==========

class Branding:
    """Default branding values."""

    DEFAULT_BRAND = "Career Forge"
    DEFAULT_SITE_URL = "https://example.com/"
    CHANNEL_LANGUAGE = "en-us"


# Helper function to get environment-aware values
def get_brand_name() -> str:
    """Get brand name from environment or default."""
    import os
    return os.getenv("BRAND", Branding.DEFAULT_BRAND)


def get_site_url() -> str:
    """Get site URL from environment or default."""
    import os
    return os.getenv("SITE_URL", Branding.DEFAULT_SITE_URL)


def get_model() -> str:
    """Get OpenAI model from environment or default."""
    import os
    return os.getenv("MODEL", OpenAIConfig.DEFAULT_MODEL)
