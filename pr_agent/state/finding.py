# AGPL-3.0 License

"""
Finding data structure for tracking review findings.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional
import hashlib


@dataclass
class Finding:
    """
    A finding from a code review that can be tracked across PR updates.

    Findings have a stable ID based on their location and content,
    allowing them to be tracked as code changes.
    """

    file_path: str
    line_range: tuple[int, int]  # (start_line, end_line)
    category: str  # e.g., "security", "performance", "style"
    severity: str  # e.g., "critical", "high", "medium", "low"
    message: str
    suggestion: Optional[str] = None
    status: Literal["open", "resolved", "invalidated", "dismissed"] = "open"
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    id: Optional[str] = None

    def __post_init__(self):
        """Generate ID if not provided."""
        if self.id is None:
            self.id = self.generate_id()
        if self.created_at is None:
            self.created_at = datetime.now()

    def generate_id(self) -> str:
        """
        Generate a stable ID for this finding.

        The ID is based on file path, line range, and a hash of the message.
        This allows findings to be tracked even as line numbers shift slightly.

        Returns:
            Stable finding ID
        """
        content = f"{self.file_path}:{self.line_range[0]}-{self.line_range[1]}:{self.category}:{self.message}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def mark_resolved(self):
        """Mark this finding as resolved."""
        self.status = "resolved"
        self.resolved_at = datetime.now()

    def mark_invalidated(self):
        """Mark this finding as invalidated (code changed, finding no longer applies)."""
        self.status = "invalidated"
        self.resolved_at = datetime.now()

    def mark_dismissed(self):
        """Mark this finding as dismissed by user."""
        self.status = "dismissed"
        self.resolved_at = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "line_range": list(self.line_range),
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "suggestion": self.suggestion,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Finding":
        """Create Finding from dictionary."""
        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        resolved_at = datetime.fromisoformat(data["resolved_at"]) if data.get("resolved_at") else None

        return cls(
            id=data["id"],
            file_path=data["file_path"],
            line_range=tuple(data["line_range"]),
            category=data["category"],
            severity=data["severity"],
            message=data["message"],
            suggestion=data.get("suggestion"),
            status=data["status"],
            created_at=created_at,
            resolved_at=resolved_at,
        )
