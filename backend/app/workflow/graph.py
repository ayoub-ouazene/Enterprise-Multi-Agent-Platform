"""Backward-compatible stub for tests that import from app.workflow.graph.

The real execution now goes through ``CompiledLinearGraph`` in ``linear_graph.py``.
This module only re-exports the interface so existing tests can still import it.
"""

from app.workflow.linear_graph import CompiledLinearGraph

workflow_graph = CompiledLinearGraph()
build_workflow_graph = CompiledLinearGraph
