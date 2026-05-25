"""EvaluationCrew: Learning assessment agent for multi-dimensional analysis.

Evaluates student learning based on behavior data, generates structured
assessment reports, and produces adaptive adjustment recommendations.
"""

import json
from collections.abc import Callable

from crewai import Agent, Crew, Process, Task

from app.agents.llm_config import (
    get_spark_llm,
    REVIEWER_TEMPERATURE as EVALUATOR_TEMPERATURE,
)


def _create_evaluator(tools: list) -> Agent:
    llm = get_spark_llm(temperature=EVALUATOR_TEMPERATURE)
    return Agent(
        role="学习效果评估专家",
        goal=(
            "基于学生的学习行为数据，从多个维度评估学习效果："
            "知识掌握度、学习投入度、进步速度、薄弱点收敛趋势。"
            "生成数据驱动的评估报告和自适应调整建议。"
        ),
        backstory=(
            "你是一位教育数据科学家，精通学习分析和教育测量。"
            "你擅长从学习行为数据（答题记录、资源使用、学习时长）"
            "中提取insight，评估学习效果，预测学习趋势。"
            "你的评估客观、量化、有据可依。每项评估结论都有具体数据支撑。"
            "你的调整建议具体可操作，能直接指导学习路径和资源策略的优化。"
            "你使用中文输出所有报告。"
        ),
        tools=tools,
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def build_evaluation_crew(
    student_profile_summary: str,
    behavior_summary: str,
    evaluation_focus: str = "comprehensive",
    evaluator_tools: list | None = None,
    step_callback: Callable | None = None,
) -> Crew:
    """Build an EvaluationCrew for multi-dimensional learning assessment.

    Args:
        student_profile_summary: Current student profile.
        behavior_summary: Aggregated learning behavior data summary.
        evaluation_focus: What to focus on:
            - "comprehensive": All dimensions
            - "progress": Progress velocity + path completion
            - "weakness": Weakness identification + convergence
            - "readiness": Knowledge readiness for a specific goal
        evaluator_tools: Tools for the evaluator.
        step_callback: Optional callback for agent steps.

    Returns:
        Configured Crew instance. Call crew.kickoff() to run.
    """
    evaluator_tools = evaluator_tools or []
    evaluator = _create_evaluator(evaluator_tools)

    focus_instructions = {
        "comprehensive": "请从所有5个维度进行全面评估。",
        "progress": "重点评估学习进度和速度，分析哪些因素加速/减缓了学习。",
        "weakness": "重点分析薄弱点和知识断层，评估薄弱点的收敛趋势。",
        "readiness": "评估学生是否已经具备学习目标知识点的前置条件。",
    }

    evaluation_task = Task(
        description=(
            f"## 学生画像\n{student_profile_summary}\n\n"
            f"## 学习行为数据\n{behavior_summary}\n\n"
            f"## 评估要求\n{focus_instructions.get(evaluation_focus, focus_instructions['comprehensive'])}\n\n"
            f"## 评估维度\n\n"
            f"### 1. 知识掌握度 (Knowledge Mastery)\n"
            f"- 各知识点的掌握水平分布（已掌握/学习中/未学习）\n"
            f"- 哪些知识点掌握扎实（正确率>80%）\n"
            f"- 哪些知识点薄弱（正确率<50%或反复出错）\n"
            f"- 知识掌握的深度（能应用/能分析/能创造）\n\n"
            f"### 2. 学习投入度 (Engagement)\n"
            f"- 学习时长和频率（每日/每周）\n"
            f"- 资源使用情况（打开了哪些资源，完成了哪些练习）\n"
            f"- 主动学习行为（提问次数、探索性浏览）\n"
            f"- 投入度趋势（上升/稳定/下降）\n\n"
            f"### 3. 进步速度 (Progress Velocity)\n"
            f"- 已完成节点数 vs 总节点数\n"
            f"- 每日/每周平均进步速度\n"
            f"- 与预估时间的偏差\n"
            f"- 加速或减速的时间段及可能原因\n\n"
            f"### 4. 薄弱点收敛 (Weakness Convergence)\n"
            f"- 识别高频错误模式\n"
            f"- 错误模式是否在缩小（收敛）还是反复出现（未收敛）\n"
            f"- 未收敛薄弱点的可能根因（前置知识缺失/概念混淆/缺乏练习）\n\n"
            f"### 5. 自适应调整建议 (Adaptive Recommendations)\n"
            f"- 学习路径调整建议（节点顺序/增删/难度调整）\n"
            f"- 资源策略调整建议（增加/减少某类资源）\n"
            f"- 学习节奏建议（加速/减速/保持）\n\n"
            f"## 输出格式\n"
            f"请输出完整的JSON格式评估报告：\n"
            f'{{"report_date": "YYYY-MM-DD", '
            f'"dimensions": {{'
            f'  "knowledge_mastery": {{'
            f'    "score": 0-100, "level": "novice|developing|proficient|advanced", '
            f'    "summary": "评估摘要", '
            f'    "strong_topics": ["topic_code"], '
            f'    "weak_topics": ["topic_code"], '
            f'    "mastery_distribution": {{"mastered": N, "learning": N, "not_started": N}}'
            f'  }},'
            f'  "engagement": {{'
            f'    "score": 0-100, "level": "low|moderate|high|exceptional", '
            f'    "summary": "...", '
            f'    "trend": "rising|stable|declining", '
            f'    "weekly_hours_estimate": N'
            f'  }},'
            f'  "progress_velocity": {{'
            f'    "score": 0-100, "level": "slow|steady|fast|accelerating", '
            f'    "summary": "...", '
            f'    "completion_percentage": N, '
            f'    "estimated_completion_date": "YYYY-MM-DD or null"'
            f'  }},'
            f'  "weakness_convergence": {{'
            f'    "score": 0-100, "summary": "...", '
            f'    "converging_patterns": ["..."], '
            f'    "persistent_gaps": [{{"topic": "...", "root_cause": "..."}}]'
            f'  }}'
            f'}}, '
            f'"overall_score": 0-100, '
            f'"overall_assessment": "总体评价摘要", '
            f'"adaptive_recommendations": {{'
            f'  "path_adjustments": [{{"action": "...", "detail": "..."}}], '
            f'  "resource_adjustments": [{{"action": "...", "detail": "..."}}], '
            f'  "pace_recommendation": "..."'
            f'}}, '
            f'"next_milestones": ["可衡量的下一步目标"]}}'
        ),
        expected_output="JSON格式的完整5维度评估报告，含自适应调整建议。",
        agent=evaluator,
    )

    if step_callback:
        evaluation_task.callback = step_callback

    return Crew(
        agents=[evaluator],
        tasks=[evaluation_task],
        process=Process.sequential,
        verbose=False,
    )
