# AGPL-3.0 License
# Copyright (c) Qodo Ltd.

"""
Base class for diagram generators.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from pr_agent.diagrams.diagram_types import DiagramType
from pr_agent.algo.types import FilePatchInfo


class BaseDiagramGenerator(ABC):
    """
    Abstract base class for all diagram generators.

    Each diagram type has its own generator that produces
    Mermaid-compatible markdown or other diagram formats.
    """

    def __init__(self, diagram_type: DiagramType):
        """
        Initialize diagram generator.

        Args:
            diagram_type: Type of diagram this generator produces
        """
        self.diagram_type = diagram_type

    @abstractmethod
    async def generate(
        self,
        patches: list[FilePatchInfo],
        context: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Generate diagram from PR patches.

        Args:
            patches: List of file patches from the PR
            context: Optional additional context (PR description, etc.)

        Returns:
            Diagram in Mermaid markdown format or other format
        """
        pass

    def format_mermaid(self, diagram_code: str) -> str:
        """
        Format diagram code as Mermaid markdown block.

        Args:
            diagram_code: Raw Mermaid diagram code

        Returns:
            Formatted markdown with mermaid code block
        """
        return f"```mermaid\n{diagram_code}\n```"

    @abstractmethod
    def get_prompt_template(self) -> str:
        """
        Get the AI prompt template for this diagram type.

        Returns:
            Prompt template string
        """
        pass

    def should_generate(self, patches: list[FilePatchInfo]) -> bool:
        """
        Determine if diagram generation makes sense for these patches.

        Args:
            patches: List of file patches

        Returns:
            True if diagram should be generated
        """
        # By default, only generate if there are patches
        return len(patches) > 0
