# AGPL-3.0 License
# Copyright (c) Qodo Ltd.

"""
Check result data structures.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class CheckDetail:
    """
    Detailed information about a specific check finding.
    """
    file_path: str
    line_number: Optional[int] = None
    message: str = ""
    suggestion: Optional[str] = None


@dataclass
class CheckResult:
    """
    Result of executing a pre-merge check.

    Attributes:
        passed: Whether the check passed
        message: Human-readable summary message
        details: List of specific findings
        severity: Severity level of the result
    """
    passed: bool
    message: str
    details: list[CheckDetail] = field(default_factory=list)
    severity: Literal["info", "warning", "error"] = "info"

    def __str__(self) -> str:
        status = "✓ PASSED" if self.passed else "✗ FAILED"
        return f"[{self.severity.upper()}] {status}: {self.message}"
