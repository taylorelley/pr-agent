# AGPL-3.0 License
# Copyright (c) Qodo Ltd.

"""
Feedback event types and data structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class FeedbackEvent(Enum):
    """
    Types of feedback events that can be logged.
    """

    SUGGESTION_APPLIED = "suggestion_applied"
    """User applied a code suggestion"""

    SUGGESTION_DISMISSED = "suggestion_dismissed"
    """User explicitly dismissed a suggestion"""

    COMMENT_RESOLVED = "comment_resolved"
    """Review comment was marked as resolved"""

    COMMENT_REPLIED = "comment_replied"
    """User replied to a review comment"""

    THUMBS_UP = "thumbs_up"
    """User gave positive feedback (thumbs up)"""

    THUMBS_DOWN = "thumbs_down"
    """User gave negative feedback (thumbs down)"""

    FINDING_DISPUTED = "finding_disputed"
    """User disputed a finding as incorrect"""

    CHECK_BYPASSED = "check_bypassed"
    """User bypassed a blocking check"""


@dataclass
class FeedbackEventData:
    """
    Complete data for a feedback event.
    """

    event_type: FeedbackEvent
    timestamp: datetime
    pr_id: str
    repository: str
    user: str

    # Content context
    suggestion_content: Optional[str] = None
    code_context: Optional[str] = None
    finding_category: Optional[str] = None
    finding_severity: Optional[str] = None

    # Metadata
    file_path: Optional[str] = None
    language: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "pr_id": self.pr_id,
            "repository": self.repository,
            "user": self.user,
            "suggestion_content": self.suggestion_content,
            "code_context": self.code_context,
            "finding_category": self.finding_category,
            "finding_severity": self.finding_severity,
            "file_path": self.file_path,
            "language": self.language,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FeedbackEventData":
        """Create FeedbackEventData from dictionary."""
        return cls(
            event_type=FeedbackEvent(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            pr_id=data["pr_id"],
            repository=data["repository"],
            user=data["user"],
            suggestion_content=data.get("suggestion_content"),
            code_context=data.get("code_context"),
            finding_category=data.get("finding_category"),
            finding_severity=data.get("finding_severity"),
            file_path=data.get("file_path"),
            language=data.get("language"),
            metadata=data.get("metadata", {}),
        )
