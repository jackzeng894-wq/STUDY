"""Knowledge graph query tool for CrewAI agents.

Enables agents to query the JavaScript knowledge graph for
prerequisites, related topics, and learning dependencies.
Used by ResourcePlanner and PathCrew agents.
"""

import json
import uuid

from crewai.tools import tool


def create_graph_tool(graph_service=None):
    """Create a graph query tool with access to the graph service.

    The graph service is injected at tool creation time. If unavailable,
    the tool returns a descriptive error rather than failing silently.

    Args:
        graph_service: Optional graph_service instance with graph methods.
    """

    @tool("query_knowledge_graph")
    def query_knowledge_graph(
        operation: str,
        node_id: str = "",
        topic_code: str = "",
    ) -> str:
        """Query the JavaScript knowledge graph for learning structure information.

        Use this tool to understand topic dependencies, prerequisite chains,
        and related knowledge points. Essential for planning learning paths
        and deciding resource generation order.

        Args:
            operation: Query type:
                - "prerequisites": Get direct prerequisites for a node
                - "dependents": Get nodes that depend on this node
                - "related": Get related/extends/contrasts nodes
                - "topology": Get topological order of all nodes
                - "hub_nodes": Get high-importance (PageRank) hub nodes
                - "node_info": Get full info about a node
            node_id: Node UUID (for node_info, prerequisites, dependents, related).
            topic_code: Topic code like "js_async_promise" (alternative to node_id).
        Returns:
            JSON string with query results.
        """
        if graph_service is None:
            return json.dumps({
                "error": "知识图谱服务不可用。请基于已知的知识点依赖关系回答。",
                "data": None,
            }, ensure_ascii=False)

        try:
            if operation == "prerequisites":
                data = graph_service.get_prerequisites(
                    node_id=str(node_id) if node_id else None,
                    topic_code=topic_code or None,
                )
            elif operation == "dependents":
                data = graph_service.get_dependents(
                    node_id=str(node_id) if node_id else None,
                    topic_code=topic_code or None,
                )
            elif operation == "related":
                data = graph_service.get_related(
                    node_id=str(node_id) if node_id else None,
                    topic_code=topic_code or None,
                )
            elif operation == "topology":
                data = graph_service.get_topological_order()
            elif operation == "hub_nodes":
                data = graph_service.get_hub_nodes(top_k=10)
            elif operation == "node_info":
                data = graph_service.get_node_info(
                    node_id=str(node_id) if node_id else None,
                    topic_code=topic_code or None,
                )
            else:
                return json.dumps({
                    "error": f"未知操作类型: {operation}。支持: prerequisites, dependents, related, topology, hub_nodes, node_info",
                    "data": None,
                }, ensure_ascii=False)

            return json.dumps({"data": data}, ensure_ascii=False, default=str)

        except (ValueError, TypeError) as e:
            return json.dumps({
                "error": f"查询参数错误: {str(e)}",
                "data": None,
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "error": f"查询失败: {str(e)}",
                "data": None,
            }, ensure_ascii=False)

    return query_knowledge_graph
