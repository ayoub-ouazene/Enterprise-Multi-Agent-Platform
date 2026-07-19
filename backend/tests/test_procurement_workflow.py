from app.workflow.graph import build_workflow_graph


def test_central_graph_keeps_procurement_on_existing_nodes() -> None:
    graph = build_workflow_graph()
    nodes = set(graph.nodes)
    assert "department_execution" in nodes
    assert "tool" in nodes
    assert "collaboration" in nodes
    assert "human_action" in nodes
