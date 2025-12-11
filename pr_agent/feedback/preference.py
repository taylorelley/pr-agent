# AGPL-3.0 License

"""
Preference model for learned team preferences.
"""

from dataclasses import dataclass


@dataclass
class Preference:
    """
    A learned preference pattern from user feedback.

    Preferences are extracted from feedback events and used
    to tune future suggestions.
    """

    pattern_type: str  # e.g., "suggestion_category", "code_pattern", "file_type"
    pattern: str  # e.g., "security", "functional_programming", "*.test.js"
    weight: float  # -1.0 (avoid) to 1.0 (prefer)
    confidence: float  # 0.0 to 1.0
    sample_count: int  # Number of feedback events supporting this preference

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "pattern_type": self.pattern_type,
            "pattern": self.pattern,
            "weight": self.weight,
            "confidence": self.confidence,
            "sample_count": self.sample_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Preference":
        """Create Preference from dictionary."""
        return cls(
            pattern_type=data["pattern_type"],
            pattern=data["pattern"],
            weight=data["weight"],
            confidence=data["confidence"],
            sample_count=data["sample_count"],
        )

    def update_with_feedback(self, positive: bool):
        """
        Update preference based on new feedback.

        Args:
            positive: True for positive feedback, False for negative
        """
        # Simple update: adjust weight based on feedback
        adjustment = 0.1 if positive else -0.1
        self.weight = max(-1.0, min(1.0, self.weight + adjustment))
        self.sample_count += 1

        # Recalculate confidence based on sample count
        # More samples = higher confidence (up to 1.0)
        self.confidence = min(1.0, self.sample_count / 10.0)
