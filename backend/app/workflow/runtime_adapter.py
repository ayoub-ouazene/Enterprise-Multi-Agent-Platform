"""Simple runtime adapter for calling LangGraph nodes outside of LangGraph.

Nodes expect ``runtime: Runtime[WorkflowRuntimeContext]`` but we call them
from the linear runner with a plain dict.  ``RuntimeContext`` wraps the dict
so that ``runtime.context.attr`` works.
"""

from __future__ import annotations

from typing import Any


class SimpleContext:
    """Wraps a dict so attribute access works like LangGraph RuntimeContext."""

    def __init__(self, **kwargs: Any) -> None:
        self.__dict__.update(kwargs)


class RuntimeContext:
    """Minimal runtime stand-in for LangGraph nodes."""

    def __init__(self, **kwargs: Any) -> None:
        self.context = SimpleContext(**kwargs)

    def __getitem__(self, item: str) -> Any:
        return getattr(self.context, item)
