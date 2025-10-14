#!/usr/bin/env python3
"""
Health check script for Career Forge RSS automation.
Validates system state and reports any issues.
"""

import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple
from logger_config import get_logger

logger = get_logger(__name__)


class HealthCheck:
    """System health validation."""

    def __init__(self):
        self.checks: List[Tuple[str, bool, str]] = []

    def add_result(self, check_name: str, passed: bool, message: str = "") -> None:
        """Add a check result."""
        self.checks.append((check_name, passed, message))
        status = "✓ PASS" if passed else "✗ FAIL"
        log_method = logger.info if passed else logger.error
        log_method(f"{status}: {check_name} - {message}")

    def check_file_exists(self, file_path: str, description: str) -> bool:
        """Check if a required file exists."""
        exists = os.path.exists(file_path)
        self.add_result(
            f"File: {description}",
            exists,
            file_path if exists else f"{file_path} not found"
        )
        return exists

    def check_rss_valid(self, rss_path: str = "rss.xml") -> bool:
        """Validate RSS feed is well-formed XML."""
        try:
            tree = ET.parse(rss_path)
            root = tree.getroot()
            channel = root.find("channel")

            if channel is None:
                self.add_result("RSS Structure", False, "Missing channel element")
                return False

            # Check required elements
            required = ["title", "link", "description"]
            missing = [elem for elem in required if channel.find(elem) is None]

            if missing:
                self.add_result("RSS Structure", False, f"Missing elements: {missing}")
                return False

            self.add_result("RSS Structure", True, "Valid RSS 2.0 feed")
            return True
        except ET.ParseError as e:
            self.add_result("RSS Structure", False, f"XML parse error: {e}")
            return False
        except Exception as e:
            self.add_result("RSS Structure", False, f"Unexpected error: {e}")
            return False

    def check_recent_post(self, rss_path: str = "rss.xml", max_hours: int = 24) -> bool:
        """Check if there's a recent post within the specified hours."""
        try:
            tree = ET.parse(rss_path)
            channel = tree.getroot().find("channel")
            items = channel.findall("item") if channel else []

            if not items:
                self.add_result("Recent Post", False, "No items in feed")
                return False

            # Check the most recent item
            first_item = items[0]
            pub_date_elem = first_item.find("pubDate")

            if pub_date_elem is None or not pub_date_elem.text:
                self.add_result("Recent Post", False, "Missing pubDate")
                return False

            # Parse pubDate (RSS format: "Tue, 10 Oct 2023 14:30:00 +0000")
            pub_date_str = pub_date_elem.text
            pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z")
            now = datetime.now(timezone.utc)
            age_hours = (now - pub_date).total_seconds() / 3600

            if age_hours > max_hours:
                self.add_result(
                    "Recent Post",
                    False,
                    f"Last post is {age_hours:.1f} hours old (max: {max_hours})"
                )
                return False

            self.add_result(
                "Recent Post",
                True,
                f"Last post is {age_hours:.1f} hours old"
            )
            return True
        except Exception as e:
            self.add_result("Recent Post", False, f"Error checking post date: {e}")
            return False

    def check_file_size(self, file_path: str, max_mb: float, description: str) -> bool:
        """Check if file size is within acceptable limits."""
        try:
            if not os.path.exists(file_path):
                self.add_result(f"File Size: {description}", False, f"{file_path} not found")
                return False

            size_mb = os.path.getsize(file_path) / (1024 * 1024)

            if size_mb > max_mb:
                self.add_result(
                    f"File Size: {description}",
                    False,
                    f"{size_mb:.2f}MB exceeds limit of {max_mb}MB"
                )
                return False

            self.add_result(
                f"File Size: {description}",
                True,
                f"{size_mb:.2f}MB (limit: {max_mb}MB)"
            )
            return True
        except Exception as e:
            self.add_result(f"File Size: {description}", False, f"Error: {e}")
            return False

    def check_env_var(self, var_name: str) -> bool:
        """Check if required environment variable is set."""
        value = os.getenv(var_name)
        is_set = value is not None and value != ""

        self.add_result(
            f"Environment: {var_name}",
            is_set,
            "Set" if is_set else "Not set"
        )
        return is_set

    def run_all_checks(self) -> bool:
        """Run all health checks."""
        logger.info("Starting health checks...")

        # File existence checks
        self.check_file_exists("rss.xml", "Main RSS Feed")
        self.check_file_exists("ops/config.json", "Configuration")
        self.check_file_exists("ops/rules.json", "Quality Rules")
        self.check_file_exists("ops/bandit.json", "Style Weights")
        self.check_file_exists("analytics/fingerprints.json", "Fingerprints")
        self.check_file_exists("content/seeds_topics.txt", "Topic Seeds")

        # RSS validation
        self.check_rss_valid("rss.xml")

        # Recent post check (24 hours)
        self.check_recent_post("rss.xml", max_hours=24)

        # File size checks (prevent runaway growth)
        self.check_file_size("analytics/fingerprints.json", max_mb=5, description="Fingerprints")
        self.check_file_size("rss.xml", max_mb=10, description="RSS Feed")

        # Environment checks (only in CI/CD)
        if os.getenv("CI"):
            self.check_env_var("OPENAI_API_KEY")

        # Summary
        total = len(self.checks)
        passed = sum(1 for _, result, _ in self.checks if result)
        failed = total - passed

        logger.info(f"\nHealth Check Summary: {passed}/{total} passed, {failed} failed")

        if failed > 0:
            logger.error("\nFailed checks:")
            for name, result, message in self.checks:
                if not result:
                    logger.error(f"  - {name}: {message}")

        return failed == 0

    def get_summary(self) -> Dict:
        """Get summary statistics."""
        total = len(self.checks)
        passed = sum(1 for _, result, _ in self.checks if result)

        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": (passed / total * 100) if total > 0 else 0
        }


def main():
    """Run health checks and exit with appropriate code."""
    health = HealthCheck()
    success = health.run_all_checks()

    summary = health.get_summary()
    print(f"\n{'='*50}")
    print(f"Health Check Results: {summary['passed']}/{summary['total']} passed")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(f"{'='*50}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
