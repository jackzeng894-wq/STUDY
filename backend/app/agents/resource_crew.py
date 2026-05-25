"""ResourceCrew: 10-agent Hierarchical Process for resource generation.

ResourcePlanner (Manager) → 8 specialized generators (parallel)
→ ResourceReviewer (review). Review-retry is orchestrated by the
service layer (resource_service.py).

Agent communication uses structured ResourceTask objects, not raw strings.
"""

from collections.abc import Callable
from dataclasses import dataclass, field, asdict
from typing import Optional

from crewai import Agent, Crew, Process, Task

from app.agents.llm_config import (
    get_spark_llm,
    GENERATOR_TEMPERATURE,
    REVIEWER_TEMPERATURE,
)

# Temperature for the planner/manager
PLANNER_TEMPERATURE = 0.4


# ── Structured data transfer between agents ──────────────────────────

@dataclass
class ResourceTask:
    """Structured task payload passed from Planner to generators.

    Serialized to JSON string for CrewAI inter-agent communication.
    """
    task_id: str
    resource_type: str  # course_doc|mind_map|exercise|code_case|ppt|project|reading|video_script
    knowledge_node_id: str
    topic_title: str
    difficulty: str  # beginner|intermediate|advanced
    student_profile_snapshot: dict = field(default_factory=dict)
    rag_context: str = ""
    constraints: list[str] = field(default_factory=list)

    def to_prompt_context(self) -> str:
        """Format as prompt context for injection into generator tasks."""
        profile = self.student_profile_snapshot
        profile_str = (
            f"学生水平: {profile.get('knowledge_foundation', '未知')}\n"
            f"学习风格: {profile.get('cognitive_style', 'unknown')}\n"
            f"学习目标: {profile.get('learning_goals', [])}\n"
            f"常见错误: {profile.get('common_errors', [])}"
        ) if profile else "学生画像未提供"

        constraints_str = "\n".join(f"- {c}" for c in self.constraints)

        return (
            f"## 任务信息\n"
            f"- 任务ID: {self.task_id}\n"
            f"- 资源类型: {RESOURCE_TYPE_LABELS.get(self.resource_type, self.resource_type)}\n"
            f"- 知识点: {self.topic_title}\n"
            f"- 难度: {self.difficulty}\n\n"
            f"## 学生画像\n{profile_str}\n\n"
            f"## 约束条件\n{constraints_str}\n\n"
            f"## 知识库参考内容\n{self.rag_context or '（无额外知识库内容）'}"
        )


# Labels for resource types (Chinese display names)
RESOURCE_TYPE_LABELS = {
    "design_plan": "资源设计方案",
    "course_doc": "课程讲解文档（Markdown）",
    "mind_map": "知识点思维导图（JSON）",
    "exercise": "练习题集（JSON）",
    "code_case": "代码实战案例",
    "ppt": "PPT讲义",
    "project": "实践项目材料（JSON）",
    "reading": "拓展阅读材料（Markdown）",
    "video_script": "教学动画脚本（JSON）",
}

# Resource type to expected output format
RESOURCE_OUTPUT_FORMATS = {
    "course_doc": "Markdown文档，含标题层级、代码块（```javascript）、知识点讲解",
    "mind_map": 'JSON格式：{"topic": "根主题", "children": [{"topic": "子主题", "children": []}]}',
    "exercise": 'JSON格式：{"title": "", "questions": [{"type": "choice|fill|code", "question": "", "options": [], "answer": "", "explanation": ""}]}',
    "code_case": "Markdown文档，含场景说明、完整可运行代码（```javascript）、运行结果预期",
    "ppt": 'JSON格式：{"title": "", "slides": [{"slide_number": 1, "title": "", "content_type": "text|code|bullets", "content": "", "notes": ""}]}',
    "project": 'JSON格式：{"title": "", "description": "", "learning_objectives": [], "starter_code": "", "requirements": [], "test_cases": [], "step_by_step_guide": []}',
    "reading": "Markdown文档，含深入分析、外部参考资料链接、与课程内容的关联说明",
    "video_script": 'JSON格式：{"title": "", "description": "", "scenes": [{"scene_id": 1, "narration": "", "duration_seconds": 10, "animation_type": "fade_in|code_execute|...", "code_snippet": ""}]}',
}


# ── Agent factories ───────────────────────────────────────────────────

def _create_planner(tools: list) -> Agent:
    """ResourcePlanner: analyzes profile + knowledge graph, plans resource mix."""
    llm = get_spark_llm(temperature=PLANNER_TEMPERATURE)
    return Agent(
        role="教学资源规划师",
        goal=(
            "分析学生的画像数据和知识点图谱，制定精确的资源生成方案。"
            "决定应该生成哪些类型的资源（从8种中选取最适合的组合）、"
            "确定难度等级、分配任务给各专业生成Agent。"
            "方案必须基于知识库内容，不得脱离实际课程内容凭空规划。"
        ),
        backstory=(
            "你是一位资深教学设计师，拥有丰富的JavaScript教学经验。"
            "你擅长根据学生的认知水平、学习风格和知识薄弱点，"
            "设计精准适配的学习资源组合。你的每次规划都有数据支撑，"
            "每个决策都可以追溯到学生画像中的具体维度。"
            "你使用中文进行所有规划和工作委派。"
        ),
        tools=tools,
        llm=llm,
        verbose=False,
        allow_delegation=True,
    )


def _create_doc_generator(tools: list) -> Agent:
    llm = get_spark_llm(temperature=GENERATOR_TEMPERATURE)
    return Agent(
        role="课程文档撰写专家",
        goal=(
            "生成适配学生水平的JavaScript课程讲解文档（Markdown格式）。"
            "内容必须基于知识库，包含代码示例、关键概念解释和常见误区提醒。"
            "难度严格匹配学生画像中的知识基础维度。"
        ),
        backstory=(
            "你是一位技术文档撰写专家，擅长将复杂的JavaScript概念"
            "用通俗易懂的方式呈现。你会根据学生的认知水平调整语言复杂度，"
            "对初学者使用类比和图示，对进阶学生使用底层原理和源码分析。"
            "所有代码示例都经过你反复验证确保可运行。"
        ),
        tools=tools,
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def _create_ppt_generator(tools: list) -> Agent:
    llm = get_spark_llm(temperature=GENERATOR_TEMPERATURE)
    return Agent(
        role="PPT制作师",
        goal=(
            "将JavaScript知识点组织成结构清晰的PPT讲义（JSON格式）。"
            "每页幻灯片聚焦一个要点，使用合适的排版模式（代码展示/概念图/列表对比）。"
            "确保逻辑流畅，从引入到深入，符合教学节奏。"
        ),
        backstory=(
            "你是一位教学PPT设计专家，精通信息可视化和教学设计。"
            "你知道什么样的PPT排版能帮助学生理解和记忆。"
            "你的幻灯片既美观又实用，每页都有明确的教学目标。"
        ),
        tools=tools,
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def _create_exercise_generator(tools: list) -> Agent:
    llm = get_spark_llm(temperature=GENERATOR_TEMPERATURE)
    return Agent(
        role="练习题设计专家",
        goal=(
            "生成难度适配、覆盖知识点的练习题集（JSON格式）。"
            "包含选择题、填空题和编程题，每道题配有详细解析。"
            "题目难度递进：基础理解 → 应用分析 → 综合创造。"
        ),
        backstory=(
            "你是一位精通JavaScript的考试命题专家。"
            "你不仅出题严谨，还能从学生的错误模式中洞察其知识薄弱点。"
            "你的每道题都有明确考察目标和能力层次定位。"
            "编程题会自动用工具验证答案正确性。"
        ),
        tools=tools,
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def _create_code_case_generator(tools: list) -> Agent:
    llm = get_spark_llm(temperature=GENERATOR_TEMPERATURE)
    return Agent(
        role="实战案例设计专家",
        goal=(
            "设计真实场景的JavaScript代码实战案例（Markdown + 可执行代码）。"
            "案例要紧贴学生画像中的学习目标，代码必须能在Deno沙箱中正确运行。"
            "包含场景说明、完整代码、运行结果预期和关键点注释。"
        ),
        backstory=(
            "你是一位全栈JavaScript开发者，拥有丰富的实战项目经验。"
            "你擅长设计贴近真实开发场景的教学案例，让抽象的概念变得具体可感。"
            "你生成的代码都会先自行验证可运行性，确保学生照着写不会报错。"
        ),
        tools=tools,
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def _create_project_designer(tools: list) -> Agent:
    llm = get_spark_llm(temperature=GENERATOR_TEMPERATURE)
    return Agent(
        role="项目设计师",
        goal=(
            "设计结构化的JavaScript实践项目学习材料。"
            "包含项目需求说明、启动代码、测试用例和分步实现指引。"
            "项目难度与学生水平匹配，目标明确可衡量。"
        ),
        backstory=(
            "你是一位项目式学习（PBL）教学设计专家。"
            "你设计的项目既有挑战性又可达，学生完成后有明确的成就感。"
            "你精心设计分步指引，让学生在完成项目的过程中自然掌握知识点。"
        ),
        tools=tools,
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def _create_mindmap_generator(tools: list) -> Agent:
    llm = get_spark_llm(temperature=GENERATOR_TEMPERATURE)
    return Agent(
        role="知识可视化专家",
        goal=(
            "将JavaScript知识点组织为结构清晰的思维导图（JSON树形格式）。"
            "导图层次分明，从核心概念到细节分支，帮助学生建立知识结构。"
            "节点数量适中（15-30个），深度不超过4层。"
        ),
        backstory=(
            "你是一位知识管理专家，精通思维导图和概念图绘制。"
            "你善于发现知识点之间的层级和关联关系，"
            "能用最清晰的树形结构呈现复杂的JavaScript知识体系。"
        ),
        tools=tools,
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def _create_reading_generator(tools: list) -> Agent:
    llm = get_spark_llm(temperature=GENERATOR_TEMPERATURE)
    return Agent(
        role="拓展阅读师",
        goal=(
            "生成与JavaScript知识点相关的深入拓展阅读材料（Markdown）。"
            "内容涵盖知识点的历史背景、设计哲学、相关ECMAScript规范、"
            "业界最佳实践和进阶方向。适合学有余力的学生。"
        ),
        backstory=(
            "你是一位JavaScript语言深度研究者，跟踪ECMAScript规范演进。"
            "你的阅读材料既有深度又有广度，能激发学生的求知欲。"
            "你善于将看似零散的知识点串联成完整的知识网络。"
        ),
        tools=tools,
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def _create_video_animator(tools: list) -> Agent:
    llm = get_spark_llm(temperature=GENERATOR_TEMPERATURE)
    return Agent(
        role="动画脚本师",
        goal=(
            "为JavaScript概念生成教学动画的场景脚本（JSON格式）。"
            "脚本需包含逐场景的旁白文本、动画类型指令和代码演示片段。"
            "特别适合解释执行流程类概念（事件循环、闭包、原型链等）。"
        ),
        backstory=(
            "你是一位教学动画导演，擅长用视觉化方式解释抽象编程概念。"
            "你的动画脚本让变量赋值变成盒子装物、让事件循环变成排队打饭——"
            "每个学生都能一看就懂。你的场景编排紧凑，节奏得当。"
        ),
        tools=tools,
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def _create_reviewer(tools: list) -> Agent:
    """ResourceReviewer: quality gate. Cross-checks all generated content."""
    llm = get_spark_llm(temperature=REVIEWER_TEMPERATURE)
    return Agent(
        role="资源审核专家",
        goal=(
            "严格审核所有生成的JavaScript学习资源，确保："
            "1）内容与知识库一致（无幻觉）；2）代码可正确运行；"
            "3）难度匹配学生水平；4）无安全或不当内容。"
            "审核不通过的资源必须给出具体修改意见，让生成Agent修正。"
        ),
        backstory=(
            "你是一位严谨的JavaScript教育质量审核专家。"
            "你对技术准确性有极高的要求，任何一处API错误或概念偏差都逃不过你的眼睛。"
            "你的审核意见精确、可操作，生成Agent能直接按照意见修改。"
            "你对初学者特别保护——任何可能引起混淆的表述你都会标注并要求修改。"
        ),
        tools=tools,
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


# ── Crew builder ─────────────────────────────────────────────────────

def build_resource_crew(
    resource_tasks: list[ResourceTask],
    student_profile_summary: str = "",
    rag_context: str = "",
    manager_tools: list | None = None,
    generator_tools: list | None = None,
    reviewer_tools: list | None = None,
    step_callback: Callable | None = None,
) -> Crew:
    """Build a ResourceCrew for one resource generation session.

    The crew uses Hierarchical Process: ResourcePlanner as manager
    delegates to specialized generators, then ResourceReviewer checks
    quality. The service layer handles the review-retry loop.

    Args:
        resource_tasks: List of ResourceTask defining what to generate.
        student_profile_summary: Human-readable profile summary for context.
        rag_context: Pre-retrieved knowledge base snippets.
        manager_tools: Tools for the planner (knowledge, graph, profile).
        generator_tools: Tools for generators (knowledge, code_exec, safety).
        reviewer_tools: Tools for reviewer (knowledge, code_exec, safety).
        step_callback: Optional callback for each agent step.

    Returns:
        Configured Crew instance. Call crew.kickoff() to run.
    """
    manager_tools = manager_tools or []
    generator_tools = generator_tools or []
    reviewer_tools = reviewer_tools or []

    # Create agents
    planner = _create_planner(manager_tools)
    doc_gen = _create_doc_generator(generator_tools)
    ppt_gen = _create_ppt_generator(generator_tools)
    exercise_gen = _create_exercise_generator(generator_tools)
    code_case_gen = _create_code_case_generator(generator_tools)
    project_designer = _create_project_designer(generator_tools)
    mindmap_gen = _create_mindmap_generator(generator_tools)
    reading_gen = _create_reading_generator(generator_tools)
    video_animator = _create_video_animator(generator_tools)
    reviewer = _create_reviewer(reviewer_tools)

    # Build task descriptions
    tasks_summary = "\n".join(
        f"- [{t.task_id}] {RESOURCE_TYPE_LABELS.get(t.resource_type, t.resource_type)}"
        f" 关于「{t.topic_title}」(难度:{t.difficulty})"
        for t in resource_tasks
    )

    task_contexts = "\n\n".join(
        t.to_prompt_context() for t in resource_tasks
    )

    # Manager task: plan and coordinate
    plan_task = Task(
        description=(
            f"## 资源生成任务\n\n"
            f"学生画像摘要：\n{student_profile_summary or '（画像数据待收集）'}\n\n"
            f"需要生成的资源列表：\n{tasks_summary}\n\n"
            f"## 每个资源的详细信息\n{task_contexts}\n\n"
            f"## 知识库参考\n{rag_context or '（使用工具查询知识库）'}\n\n"
            f"## 你的工作流程\n"
            f"1. 分析学生画像和知识图谱，确认资源组合是否合理，如有必要可调整\n"
            f"2. 将每个资源类型分配给对应的专业生成Agent\n"
            f"3. 等待所有Agent完成生成\n"
            f"4. 将生成结果提交给资源审核专家(ResourceReviewer)审核\n"
            f"5. 收集审核结果，汇总最终可交付的资源清单\n\n"
            f"## 重要提示\n"
            f"- 所有生成必须基于知识库内容，不可自由发挥编造知识点\n"
            f"- 难度必须严格匹配学生水平（beginner/intermediate/advanced）\n"
            f"- 每个资源的输出格式必须符合该类型的规范\n"
            f"- 对于代码类资源，生成后必须用工具验证代码可运行性"
        ),
        expected_output=(
            "一份资源生成汇总报告，包含：\n"
            "1. 每个已生成资源的简要说明和存储路径\n"
            "2. 审核状态（通过/需修改/未生成）\n"
            "3. 如有未通过的资源，附上修改建议"
        ),
        agent=planner,
    )

    if step_callback:
        plan_task.callback = step_callback

    # Generator tasks: one per resource type (manager delegates to these)
    generator_task = Task(
        description=(
            f"根据规划师分配的以下任务，生成对应类型的学习资源。\n\n"
            f"资源任务列表：\n{tasks_summary}\n\n"
            f"任务详情：\n{task_contexts}\n\n"
            f"每种资源类型的输出格式要求：\n"
            + "\n".join(f"- {label}: {RESOURCE_OUTPUT_FORMATS.get(rt, '标准格式')}"
                       for rt, label in RESOURCE_TYPE_LABELS.items())
            + "\n\n"
            f"请严格按照指定的输出格式生成内容。"
            f"所有JavaScript代码必须可运行，所有技术论断必须有知识库依据。"
        ),
        expected_output="按指定格式生成的学习资源内容。",
        agent=doc_gen,  # placeholder, manager will delegate to appropriate agents
    )

    if step_callback:
        generator_task.callback = step_callback

    # Reviewer task
    review_task = Task(
        description=(
            f"审核所有已生成的资源，逐个检查以下项目：\n\n"
            f"1. **内容准确性**：所有技术术语和API使用是否正确？是否与知识库一致？\n"
            f"2. **代码可运行性**：JavaScript代码是否能在Deno中正常运行？\n"
            f"3. **难度匹配**：内容难度是否匹配 {resource_tasks[0].difficulty if resource_tasks else 'beginner'}？\n"
            f"4. **内容安全**：有无敏感、不当或误导性内容？\n"
            f"5. **完整性**：是否包含了题目要求的所有要素？\n\n"
            f"## 审核标准\n"
            f"- 通过(approved): 所有检查项均合格\n"
            f"- 需修改(needs_revision): 有小问题但可以通过修改解决，请给出具体修改意见\n"
            f"- 不通过(rejected): 有严重问题需要重新生成，请说明原因\n\n"
            f"## 需要审核的资源\n{tasks_summary}"
        ),
        expected_output=(
            "JSON格式的审核报告：\n"
            '{"reviews": [{"task_id": "..", "resource_type": "..", '
            '"status": "approved|needs_revision|rejected", '
            '"issues": [], "suggestions": [], "score": 0-10}]}'
        ),
        agent=reviewer,
    )

    if step_callback:
        review_task.callback = step_callback

    # Build crew with Hierarchical Process
    return Crew(
        agents=[
            planner,
            doc_gen,
            ppt_gen,
            exercise_gen,
            code_case_gen,
            project_designer,
            mindmap_gen,
            reading_gen,
            video_animator,
            reviewer,
        ],
        tasks=[plan_task, generator_task, review_task],
        process=Process.hierarchical,
        verbose=False,
        manager_agent=planner,
    )
