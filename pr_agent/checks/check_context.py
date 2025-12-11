# AGPL-3.0 License

"""
Check context data for pre-merge checks.
"""

from dataclasses import dataclass, field
from typing import Optional, Any

from pr_agent.algo.types import FilePatchInfo


@dataclass
class CheckContext:
    """
    Context data provided to checks during execution.

    Contains all relevant information about the PR that checks
    may need to evaluate.
    """

    # PR metadata
    pr_url: str
    pr_title: str
    pr_description: str
    pr_author: str
    pr_labels: list[str] = field(default_factory=list)

    # Diff information
    files_changed: list[str] = field(default_factory=list)
    patches: list[FilePatchInfo] = field(default_factory=list)

    # Git provider instance (for advanced checks)
    git_provider: Optional[Any] = None

    # Configuration settings (for check-specific config)
    config: Optional[dict] = None

    # Path filters (files relevant to this check)
    filtered_files: Optional[list[str]] = None
