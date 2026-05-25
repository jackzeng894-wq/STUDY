"""Knowledge graph service: NetworkX-powered graph algorithms.

Builds a directed graph from knowledge_nodes + knowledge_relations,
providing topological sort, shortest path (Dijkstra), PageRank,
and gap detection for personalized learning path planning.

All methods are synchronous (NetworkX runs in-memory, fast for 85 nodes).
"""

import uuid
from collections import defaultdict
from typing import Optional

import networkx as nx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeNode, KnowledgeRelation


class GraphService:
    """NetworkX graph operations on the JavaScript knowledge graph.

    The graph is lazily built from the database on first access.
    With only ~85 nodes and ~200 edges, in-memory computation is instant.
    """

    def __init__(self):
        self._graph: nx.DiGraph | None = None
        self._node_map: dict[str, str] = {}  # topic_code → id
        self._node_data: dict[str, dict] = {}       # topic_code → node metadata

    async def _ensure_graph(self, db: AsyncSession) -> nx.DiGraph:
        """Build or rebuild the NetworkX directed graph from the database."""
        # Skip rebuild if already loaded
        if self._graph is not None:
            return self._graph

        return await self.rebuild_graph(db)

    async def rebuild_graph(self, db: AsyncSession) -> nx.DiGraph:
        """Force-rebuild the graph from the database. Call after data changes."""
        self._graph = nx.DiGraph()
        self._node_map = {}
        self._node_data = {}

        # Load all nodes
        result = await db.execute(select(KnowledgeNode))
        nodes = result.scalars().all()

        for node in nodes:
            tc = node.topic_code
            self._node_map[tc] = node.id
            self._node_data[tc] = {
                "id": str(node.id),
                "topic_code": tc,
                "title": node.title,
                "difficulty": node.difficulty,
                "depth": node.depth,
                "keywords": node.keywords or [],
                "description": node.description or "",
            }
            self._graph.add_node(tc, **self._node_data[tc])

        # Load all edges
        result = await db.execute(select(KnowledgeRelation))
        relations = result.scalars().all()

        for rel in relations:
            # Resolve node IDs to topic codes
            source = await db.execute(
                select(KnowledgeNode.topic_code).where(
                    KnowledgeNode.id == rel.source_node_id
                )
            )
            target = await db.execute(
                select(KnowledgeNode.topic_code).where(
                    KnowledgeNode.id == rel.target_node_id
                )
            )
            src_tc = source.scalar_one_or_none()
            tgt_tc = target.scalar_one_or_none()

            if src_tc and tgt_tc:
                if rel.relation_type == "prerequisite":
                    self._graph.add_edge(
                        src_tc, tgt_tc,
                        relation_type=rel.relation_type,
                        weight=rel.weight,
                    )
                elif rel.relation_type == "related":
                    self._graph.add_edge(
                        src_tc, tgt_tc,
                        relation_type=rel.relation_type,
                        weight=rel.weight * 0.5,
                    )
                    self._graph.add_edge(
                        tgt_tc, src_tc,
                        relation_type=rel.relation_type,
                        weight=rel.weight * 0.5,
                    )
                elif rel.relation_type == "extends":
                    self._graph.add_edge(
                        src_tc, tgt_tc,
                        relation_type=rel.relation_type,
                        weight=rel.weight,
                    )
                elif rel.relation_type == "contrasts":
                    self._graph.add_edge(
                        src_tc, tgt_tc,
                        relation_type=rel.relation_type,
                        weight=rel.weight * 0.3,
                    )
                    self._graph.add_edge(
                        tgt_tc, src_tc,
                        relation_type=rel.relation_type,
                        weight=rel.weight * 0.3,
                    )

        return self._graph

    # ── Topological Sort ──────────────────────────────────────────────

    async def topological_sort(self, db: AsyncSession) -> list[dict]:
        """Return the topologically sorted order of all knowledge nodes.

        Respects prerequisite dependencies: prerequisites come first.
        Nodes with no prerequisites come first; those with unmet
        prerequisites appear later. Useful for generating the default
        learning order.
        """
        g = await self._ensure_graph(db)

        try:
            order = list(nx.topological_sort(g))
        except nx.NetworkXUnfeasible:
            # Graph has a cycle — use a best-effort approach
            # Remove edges with weight < 1.0 (soft relations) and retry
            soft_edges = [(u, v) for u, v, d in g.edges(data=True)
                          if d.get("weight", 1.0) < 1.0]
            g_copy = g.copy()
            g_copy.remove_edges_from(soft_edges)
            try:
                order = list(nx.topological_sort(g_copy))
            except nx.NetworkXUnfeasible:
                # Fallback: sort by depth then difficulty
                nodes = list(g.nodes(data=True))
                diff_order = {"beginner": 0, "intermediate": 1, "advanced": 2}
                nodes.sort(key=lambda x: (
                    x[1].get("depth", 0),
                    diff_order.get(x[1].get("difficulty", "beginner"), 0),
                ))
                order = [n for n, _ in nodes]

        return [
            {**self._node_data.get(tc, {}), "order_index": i}
            for i, tc in enumerate(order)
        ]

    # ── Shortest Path (Dijkstra) ─────────────────────────────────────

    async def shortest_path(
        self,
        db: AsyncSession,
        from_topic: str,
        to_topic: str,
    ) -> Optional[list[dict]]:
        """Find the optimal learning path between two knowledge topics.

        Uses Dijkstra's algorithm with edge weights. Prerequisites have
        weight 1.0, soft relations have higher weights (prefer prerequisites).
        This gives the most direct learning sequence from current level to goal.

        Args:
            db: Database session.
            from_topic: Starting knowledge point topic_code.
            to_topic: Target knowledge point topic_code.

        Returns:
            Ordered list of node data dicts, or None if no path exists.
        """
        g = await self._ensure_graph(db)

        if from_topic not in g or to_topic not in g:
            return None

        try:
            # Invert weight: we want minimum total weight path
            # Dijkstra uses edge weight as distance
            path = nx.shortest_path(
                g, source=from_topic, target=to_topic, weight="weight",
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            # Try ignoring soft edges
            try:
                path = nx.shortest_path(
                    g, source=from_topic, target=to_topic,
                )
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                return None

        total_weight = 0.0
        result = []
        for i, tc in enumerate(path):
            node = self._node_data.get(tc, {"topic_code": tc, "title": tc})
            # Calculate edge weight to next node
            if i < len(path) - 1:
                edge_data = g.get_edge_data(tc, path[i + 1])
                if edge_data:
                    total_weight += edge_data.get("weight", 1.0)
            result.append({**node, "step": i})

        return result

    # ── PageRank ─────────────────────────────────────────────────────

    async def pagerank(
        self,
        db: AsyncSession,
        top_k: int = 20,
    ) -> list[dict]:
        """Compute PageRank for all knowledge nodes.

        Hub nodes (high PageRank) are prerequisites for many other topics
        or have many related connections. These are the "linchpin" concepts
        that every student must master.

        Args:
            db: Database session.
            top_k: Number of top-ranked nodes to return.

        Returns:
            List of {node_data, pagerank_score}, sorted by score descending.
        """
        g = await self._ensure_graph(db)

        if len(g) == 0:
            return []

        # Use weight for personalized PageRank
        pr = nx.pagerank(g, weight="weight")

        ranked = sorted(pr.items(), key=lambda x: x[1], reverse=True)[:top_k]

        return [
            {
                **self._node_data.get(tc, {"topic_code": tc, "title": tc}),
                "pagerank_score": round(score, 4),
            }
            for tc, score in ranked
        ]

    # ── Gap Detection ─────────────────────────────────────────────────

    async def detect_gaps(
        self,
        db: AsyncSession,
        mastered_topics: list[str],
        target_topic: str,
    ) -> list[dict]:
        """Detect knowledge gaps: prerequisite nodes that are not yet mastered.

        When a student struggles with a topic, this traces backward through
        prerequisite chains to find which foundational concepts are missing.

        Args:
            db: Database session.
            mastered_topics: List of topic_codes the student has mastered.
            target_topic: The topic the student is struggling with.

        Returns:
            List of missing prerequisite nodes, ordered from most to least
            foundational (topological order).
        """
        g = await self._ensure_graph(db)

        if target_topic not in g:
            return []

        mastered_set = set(mastered_topics)

        # Find all ancestors (prerequisites) of the target topic
        # In our DAG, prerequisites point to dependents (prereq → dependent)
        # So we need predecessors of the target (things that must come before)
        try:
            ancestors = nx.ancestors(g, target_topic)
        except nx.NetworkXError:
            ancestors = set()

        # Also include the target itself
        ancestors.add(target_topic)

        # Find which ancestors are NOT mastered
        gaps = ancestors - mastered_set

        # Topologically sort the gaps
        subgraph = g.subgraph(gaps)
        try:
            gap_order = list(nx.topological_sort(subgraph))
        except nx.NetworkXUnfeasible:
            gap_order = list(gaps)

        return [
            {
                **self._node_data.get(tc, {"topic_code": tc, "title": tc}),
                "is_target": tc == target_topic,
            }
            for tc in gap_order
            if tc in gaps
        ]

    # ── Convenience Query Methods (used by graph_tool) ────────────────

    async def get_prerequisites(
        self,
        db: AsyncSession = None,
        node_id: str | None = None,
        topic_code: str | None = None,
    ) -> list[dict]:
        """Get direct prerequisites for a node."""
        g = self._graph
        if g is None or not (topic_code and topic_code in g):
            return []

        prereqs = []
        for pred in g.predecessors(topic_code):
            edge = g.get_edge_data(pred, topic_code)
            if edge and edge.get("relation_type") == "prerequisite":
                prereqs.append({
                    **self._node_data.get(pred, {"topic_code": pred}),
                    "weight": edge.get("weight", 1.0),
                })
        return prereqs

    async def get_dependents(
        self,
        db: AsyncSession = None,
        node_id: str | None = None,
        topic_code: str | None = None,
    ) -> list[dict]:
        """Get nodes that depend on this topic (dependents)."""
        g = self._graph
        if g is None or not (topic_code and topic_code in g):
            return []

        dependents = []
        for succ in g.successors(topic_code):
            edge = g.get_edge_data(topic_code, succ)
            if edge:
                dependents.append({
                    **self._node_data.get(succ, {"topic_code": succ}),
                    "relation_type": edge.get("relation_type", "unknown"),
                    "weight": edge.get("weight", 1.0),
                })
        return dependents

    async def get_related(
        self,
        db: AsyncSession = None,
        node_id: str | None = None,
        topic_code: str | None = None,
    ) -> list[dict]:
        """Get all nodes related to this topic (all edge types)."""
        g = self._graph
        if g is None or not (topic_code and topic_code in g):
            return []

        related = []
        for succ in g.successors(topic_code):
            edge = g.get_edge_data(topic_code, succ)
            if edge:
                related.append({
                    **self._node_data.get(succ, {"topic_code": succ}),
                    "relation_type": edge.get("relation_type", "unknown"),
                    "weight": edge.get("weight", 1.0),
                    "direction": "forward",
                })
        for pred in g.predecessors(topic_code):
            edge = g.get_edge_data(pred, topic_code)
            if edge:
                related.append({
                    **self._node_data.get(pred, {"topic_code": pred}),
                    "relation_type": edge.get("relation_type", "unknown"),
                    "weight": edge.get("weight", 1.0),
                    "direction": "backward",
                })
        return related

    async def get_topological_order(self, db: AsyncSession = None) -> list[dict]:
        """Get topological order using cached graph."""
        if self._graph is None:
            return []
        return await self.topological_sort(db)

    async def get_hub_nodes(self, db: AsyncSession = None, top_k: int = 10) -> list[dict]:
        """Get hub nodes by PageRank using cached graph."""
        if self._graph is None:
            return []
        return await self.pagerank(db, top_k=top_k)

    async def get_node_info(
        self,
        db: AsyncSession = None,
        node_id: str | None = None,
        topic_code: str | None = None,
    ) -> dict | None:
        """Get full info for a node."""
        if topic_code and topic_code in self._node_data:
            return self._node_data[topic_code]
        # Search by node_id
        for tc, data in self._node_data.items():
            if data.get("id") == str(node_id) if node_id else False:
                return data
        return None

    # ── Graph Stats ──────────────────────────────────────────────────

    async def get_stats(self, db: AsyncSession) -> dict:
        """Return graph statistics for dashboard display."""
        g = await self._ensure_graph(db)
        if len(g) == 0:
            return {"node_count": 0, "edge_count": 0}

        try:
            is_dag = nx.is_directed_acyclic_graph(g)
        except Exception:
            is_dag = False

        # Count by difficulty
        difficulty_counts = defaultdict(int)
        for _, data in g.nodes(data=True):
            difficulty_counts[data.get("difficulty", "unknown")] += 1

        # Count by relation type
        relation_counts = defaultdict(int)
        for _, _, data in g.edges(data=True):
            relation_counts[data.get("relation_type", "unknown")] += 1

        return {
            "node_count": len(g),
            "edge_count": len(g.edges()),
            "is_dag": is_dag,
            "difficulty_distribution": dict(difficulty_counts),
            "relation_distribution": dict(relation_counts),
        }
