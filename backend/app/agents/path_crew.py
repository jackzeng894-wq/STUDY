"""PathCrew: PathDesigner + PathEvaluator in Sequential process.

Designs a personalized learning path by combining NetworkX graph
algorithm results with student profile analysis. The evaluator then
reviews the path for quality and coherence.
"""

import json
from collections.abc import Callable

from crewai import Agent, Crew, Process, Task

from app.agents.llm_config import (
    get_spark_llm,
    GENERATOR_TEMPERATURE as DESIGNER_TEMPERATURE,
    REVIEWER_TEMPERATURE as EVALUATOR_TEMPERATURE,
)


def _create_designer(tools: list) -> Agent:
    llm = get_spark_llm(temperature=DESIGNER_TEMPERATURE)
    return Agent(
        role="学习路径规划专家",
        goal=(
            "基于知识图谱图算法结果和学生画像，设计个性化的JavaScript学习路径。"
            "路径需体现拓扑排序的合法顺序，覆盖从当前水平到学习目标的最优路径。"
            "每个路径节点须包含推荐资源类型和预估学习时长。"
        ),
        backstory=(
            "你是一位教学系统设计师，精通课程编排和个性化学习方案设计。"
            "你擅长将图算法（拓扑排序/Dijkstra/PageRank）的计算结果"
            "转化为学生易于理解和执行的学习计划。你的路径设计兼顾科学性"
            "（遵循知识依赖关系）和个性化（匹配学生风格和节奏）。"
            "你使用中文输出所有规划。"
        ),
        tools=tools,
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def _create_evaluator(tools: list) -> Agent:
    llm = get_spark_llm(temperature=EVALUATOR_TEMPERATURE)
    return Agent(
        role="路径效果评估专家",
        goal=(
            "评估学习路径的合理性和有效性。检查：1）知识依赖顺序是否正确；"
            "2）难度递进是否合理；3）总时长是否在学生时间投入范围内；"
            "4）薄弱点是否得到足够关注。提供具体的调整建议。"
        ),
        backstory=(
            "你是一位学习科学和教育测量专家。你通过数据驱动的分析"
            "来评估学习方案的预期效果。你对JavaScript知识体系了如指掌，"
            "能快速识别路径中的逻辑问题和节奏问题。"
            "你的评估意见精确、建设性，能直接转化为路径改进。"
        ),
        tools=tools,
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def build_path_crew(
    student_profile_summary: str,
    graph_analysis: dict,
    learning_goal: str = "",
    designer_tools: list | None = None,
    evaluator_tools: list | None = None,
    step_callback: Callable | None = None,
) -> Crew:
    """Build a PathCrew for personalized learning path generation.

    Args:
        student_profile_summary: Human-readable profile summary string.
        graph_analysis: Dict with graph algorithm results:
            - topological_order: Topologically sorted nodes
            - shortest_path: Optimal path from current to target (optional)
            - hub_nodes: PageRank top nodes
            - gaps: Detected knowledge gaps (optional)
        learning_goal: Student's stated learning goal.
        designer_tools: Tools for PathDesigner (graph_tool, profile_tool).
        evaluator_tools: Tools for PathEvaluator (graph_tool).
        step_callback: Optional callback for each agent step.

    Returns:
        Configured Crew instance. Call crew.kickoff() to run.
    """
    designer_tools = designer_tools or []
    evaluator_tools = evaluator_tools or []

    designer = _create_designer(designer_tools)
    evaluator = _create_evaluator(evaluator_tools)

    # Format graph analysis for prompt
    topo_nodes = graph_analysis.get("topological_order", [])
    hub_nodes = graph_analysis.get("hub_nodes", [])
    shortest_path = graph_analysis.get("shortest_path")
    gaps = graph_analysis.get("gaps", [])
    stats = graph_analysis.get("graph_stats", {})

    topo_summary = "\n".join(
        f"  {n.get('order_index', i)+1}. [{n.get('difficulty', '?')}] {n.get('title', n.get('topic_code', '?'))}"
        for i, n in enumerate(topo_nodes[:30])  # Show first 30
    ) if topo_nodes else "（拓扑排序数据不可用）"

    hubs_summary = "\n".join(
        f"  - {n.get('title', n.get('topic_code', '?'))} (PageRank: {n.get('pagerank_score', 0):.4f})"
        for n in (hub_nodes or [])[:10]
    ) if hub_nodes else "（枢纽节点数据不可用）"

    path_summary = ""
    if shortest_path:
        path_summary = "目标路径节点序列：\n" + "\n".join(
            f"  {n.get('step', i)+1}. [{n.get('difficulty', '?')}] {n.get('title', n.get('topic_code', '?'))}"
            for i, n in enumerate(shortest_path)
        )

    gaps_summary = ""
    if gaps:
        gaps_summary = "检测到的知识断层（缺失前置知识）：\n" + "\n".join(
            f"  - {n.get('title', n.get('topic_code', '?'))}"
            + (" ← 目标知识点" if n.get('is_target') else "")
            for n in gaps
        )

    # Designer task
    design_task = Task(
        description=(
            f"## 学生画像\n{student_profile_summary}\n\n"
            f"## 学习目标\n{learning_goal or '系统掌握JavaScript核心知识'}\n\n"
            f"## 知识图谱分析结果\n\n"
            f"### 图统计\n"
            f"- 总节点数: {stats.get('node_count', '?')}\n"
            f"- 总边数: {stats.get('edge_count', '?')}\n"
            f"- 是否为有向无环图: {stats.get('is_dag', '?')}\n\n"
            f"### 拓扑排序（前30个节点）\n{topo_summary}\n\n"
            f"### 枢纽知识点（PageRank Top 10）\n{hubs_summary}\n\n"
            f"{'### 最优学习路径' + chr(10) + path_summary + chr(10) + chr(10) if path_summary else ''}"
            f"{'### 知识断层' + chr(10) + gaps_summary + chr(10) + chr(10) if gaps_summary else ''}"
            f"## 你的任务\n"
            f"为这位学生设计一个个性化的JavaScript学习路径。输出格式要求：\n\n"
            f'{{"path_title": "路径标题", "description": "路径概述", '
            f'"estimated_total_hours": 30, '
            f'"nodes": ['
            f'  {{"order": 1, "knowledge_node_id": "...", "topic_code": "...", '
            f'   "title": "知识点名称", "status": "ready|locked", '
            f'   "recommended_resources": ["course_doc", "exercise"], '
            f'   "estimated_minutes": 45, '
            f'   "rationale": "为什么这个节点放在这里"}}'
            f']}}\n\n'
            f"## 设计原则\n"
            f"- 严格遵守拓扑排序的依赖关系（前置知识必须先学）\n"
            f"- 优先安排PageRank高的枢纽知识点\n"
            f"- 如有知识断层，先补断层再前进\n"
            f"- 难度递进要合理（beginner → intermediate → advanced）\n"
            f"- 总时长要匹配学生的时间投入能力\n"
            f"- 每个节点推荐2-3种最适合该学生的资源类型"
        ),
        expected_output="JSON格式的个性化学习路径，包含有序节点列表及每节点的推荐资源。",
        agent=designer,
    )

    if step_callback:
        design_task.callback = step_callback

    # Evaluator task
    evaluate_task = Task(
        description=(
            f"## 学生画像\n{student_profile_summary}\n\n"
            f"## 学习目标\n{learning_goal or '系统掌握JavaScript核心知识'}\n\n"
            f"## 知识断层\n{gaps_summary if gaps_summary else '未检测到明显断层'}\n\n"
            f"请评估 PathDesigner 设计的学习路径，检查以下维度：\n\n"
            f"1. **依赖顺序正确性**: 每个节点的前置知识是否已在前面的步骤中覆盖？\n"
            f"2. **难度递进合理性**: 难度是否从基础到高级平稳过渡？\n"
            f"3. **时长可行性**: 预估总时长是否在学生可投入的时间范围内？\n"
            f"4. **断层覆盖**: 知识断层节点是否被有效纳入路径？\n"
            f"5. **资源推荐适配**: 推荐的资源类型是否匹配学生的认知风格和学习偏好？\n\n"
            f"输出评估报告JSON：\n"
            f'{{"overall_score": 0-100, "passed": true/false, '
            f'"dimension_scores": {{"dependency": 85, "progression": 90, '
            f'"time_feasibility": 80, "gap_coverage": 95, "resource_adaptation": 88}}, '
            f'"adjustments": [{{"node_order": 3, "action": "move_earlier|move_later|replace|add|remove", '
            f'"suggestion": "具体调整建议"}}], '
            f'"summary": "总体评价"}}'
        ),
        expected_output="JSON格式的路径评估报告，包含评分和调整建议。",
        agent=evaluator,
    )

    if step_callback:
        evaluate_task.callback = step_callback

    return Crew(
        agents=[designer, evaluator],
        tasks=[design_task, evaluate_task],
        process=Process.sequential,
        verbose=False,
    )
