# AGPL-3.0 License

"""
PR state data structure.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional

from pr_agent.state.finding import Finding


@dataclass
class Message:
    """
    A message in a conversation history.

    Used to track Q&A exchanges in the /ask feature.
    """
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """Create Message from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class PRState:
    """
    Complete state for a pull request.

    Stores findings, reviewed commits, conversation history,
    and other persistent data across PR updates.
    """

    pr_id: str  # Unique identifier (e.g., "owner/repo/123")
    provider: str  # e.g., "github", "gitlab"
    findings: list[Finding] = field(default_factory=list)
    reviewed_commits: list[str] = field(default_factory=list)
    last_review_at: Optional[datetime] = None
    paused: bool = False
    conversation_history: list[Message] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def add_finding(self, finding: Finding):
        """Add a new finding to the state."""
        # Check for duplicates
        existing_ids = {f.id for f in self.findings}
        if finding.id not in existing_ids:
            self.findings.append(finding)

    def get_active_findings(self) -> list[Finding]:
        """Get all findings that are still open."""
        return [f for f in self.findings if f.status == "open"]

    def get_resolved_findings(self) -> list[Finding]:
        """Get all findings that have been resolved."""
        return [f for f in self.findings if f.status in ["resolved", "invalidated", "dismissed"]]

    def add_message(self, role: Literal["user", "assistant"], content: str, metadata: dict = None):
        """Add a message to conversation history."""
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        self.conversation_history.append(message)

    def get_recent_messages(self, limit: int = 10) -> list[Message]:
        """Get the most recent messages from conversation history."""
        return self.conversation_history[-limit:]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "pr_id": self.pr_id,
            "provider": self.provider,
            "findings": [f.to_dict() for f in self.findings],
            "reviewed_commits": self.reviewed_commits,
            "last_review_at": self.last_review_at.isoformat() if self.last_review_at else None,
            "paused": self.paused,
            "conversation_history": [m.to_dict() for m in self.conversation_history],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PRState":
        """Create PRState from dictionary."""
        findings = [Finding.from_dict(f) for f in data.get("findings", [])]
        conversation_history = [Message.from_dict(m) for m in data.get("conversation_history", [])]
        last_review_at = datetime.fromisoformat(data["last_review_at"]) if data.get("last_review_at") else None

        return cls(
            pr_id=data["pr_id"],
            provider=data["provider"],
            findings=findings,
            reviewed_commits=data.get("reviewed_commits", []),
            last_review_at=last_review_at,
            paused=data.get("paused", False),
            conversation_history=conversation_history,
            metadata=data.get("metadata", {}),
        )
