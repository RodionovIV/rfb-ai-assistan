from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class Agent(ABC):
    """Base class for all analytical agents."""

    name: str = "agent"

    @abstractmethod
    def run(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute agent logic and return a serialisable payload."""


class AgentExecutionError(RuntimeError):
    """Raised when an agent fails during execution."""


