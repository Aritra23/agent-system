from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    output: Any
    steps: list[str] = field(default_factory=list)
    error: str | None = None


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this tool does."""
        ...

    @property
    @abstractmethod
    def keywords(self) -> list[str]:
        """Keywords used by the agent to select this tool."""
        ...

    @abstractmethod
    def execute(self, input_text: str) -> ToolResult:
        """Execute the tool with the given input."""
        ...

    def can_handle(self, input_text: str) -> bool:
        """Returns True if this tool is likely able to handle the input."""
        lowered = input_text.lower()
        return any(kw in lowered for kw in self.keywords)
