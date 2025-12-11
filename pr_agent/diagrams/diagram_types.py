# AGPL-3.0 License

"""
Diagram type definitions.
"""

from enum import Enum


class DiagramType(Enum):
    """
    Types of diagrams that can be generated.
    """

    CHANGE_FLOW = "change_flow"
    """Flow diagram showing logical changes in the PR (existing feature)"""

    COMPONENT = "component"
    """Component diagram showing module relationships and dependencies"""

    DATA_FLOW = "data_flow"
    """Data flow diagram showing data transformations"""

    SEQUENCE = "sequence"
    """Sequence diagram showing interaction flow (future)"""

    CLASS = "class"
    """Class diagram showing class relationships (future)"""

    @classmethod
    def from_string(cls, value: str) -> "DiagramType":
        """
        Create DiagramType from string.

        Args:
            value: String representation

        Returns:
            DiagramType enum value

        Raises:
            ValueError: If value doesn't match any diagram type
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_types = [dt.value for dt in cls]
            raise ValueError(f"Invalid diagram type '{value}'. Valid types: {valid_types}")

    def __str__(self) -> str:
        return self.value
