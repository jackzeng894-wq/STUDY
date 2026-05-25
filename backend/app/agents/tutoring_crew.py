"""TutoringCrew: TutorAgent + ExplanationGenerator in Sequential process.

Provides real-time Q&A tutoring. The tutor answers JavaScript questions
grounded in knowledge base content, then the explanation generator
enhances the answer with multi-modal elements (diagrams, code walkthrough,
step-by-step breakdowns).
"""

from collections.abc import Callable

from crewai import Agent, Crew, Process, Task

from app.agents.llm_config import (
    get_spark_llm,
    GENERATOR_TEMPERATURE as TUTOR_TEMPERATURE,
    REVIEWER_TEMPERATURE as EXPLAINER_TEMPERATURE,
)


def _create_tutor(tools: list) -> Agent:
    llm = get_spark_llm(temperature=TUTOR_TEMPERATURE)
    return Agent(
        role="JavaScript辅导教师",
        goal=(
            "准确回答学生的JavaScript问题，基于知识库内容提供权威解答。"
            "用通俗易懂的语言解释复杂概念，根据学生的画像调整解释深度。"
            "遇到代码问题时要给出可运行的示例代码。所有回答使用中文。"
        ),
        backstory=(
            "你是一位经验丰富的JavaScript全栈开发者和教师。"
            "你拥有10年一线开发和教学经验，精通JavaScript核心概念、"
            "ES6+特性、异步编程、浏览器API和常见框架。"
            "你的教学风格亲切耐心，善于用生活类比解释抽象概念，"
            "用最小可运行代码演示核心原理。"
            "你严格基于知识库内容回答，绝不编造不存在的事实。"
        ),
        tools=tools,
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def _create_explainer(tools: list) -> Agent:
    llm = get_spark_llm(temperature=EXPLAINER_TEMPERATURE)
    return Agent(
        role="多模态解释专家",
        goal=(
            "将辅导教师的文字解答增强为多模态学习内容。"
            "为复杂概念生成分步图解描述、代码执行流程动画脚本、"
            "对比表格、记忆口诀等辅助理解材料。"
            "输出格式化的结构化内容，便于前端渲染为交互式学习组件。"
        ),
        backstory=(
            "你是教育技术专家，专注于将抽象知识转化为可视化学习体验。"
            "你精通信息设计、教学动画脚本编写、知识结构化。"
            "你的目标是让每个JavaScript概念都变得'看得见、摸得着'。"
            "你的输出格式精确、结构化，可直接被前端渲染引擎解析。"
        ),
        tools=tools,
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def build_tutoring_crew(
    student_question: str,
    conversation_history: str = "",
    student_profile_summary: str = "",
    rag_context: str = "",
    tutor_tools: list | None = None,
    explainer_tools: list | None = None,
    step_callback: Callable | None = None,
) -> Crew:
    """Build a TutoringCrew for one round of Q&A tutoring.

    Args:
        student_question: The student's question.
        conversation_history: Previous messages in this tutoring session.
        student_profile_summary: Student profile for personalized answers.
        rag_context: Knowledge base snippets for grounding.
        tutor_tools: Tools for TutorAgent (knowledge, code_exec).
        explainer_tools: Tools for ExplanationGenerator.
        step_callback: Optional callback for each agent step.

    Returns:
        Configured Crew instance. Call crew.kickoff() to run.
    """
    tutor_tools = tutor_tools or []
    explainer_tools = explainer_tools or []

    tutor = _create_tutor(tutor_tools)
    explainer = _create_explainer(explainer_tools)

    rag_section = ""
    if rag_context:
        rag_section = (
            "\n\n## 知识库参考内容（必须基于此回答）\n"
            f"{rag_context}\n"
            "\n重要：回答必须基于以上知识库内容。如果知识库没有相关信息，"
            "请基于通用JavaScript知识回答并提示学生此为通用知识。"
        )

    profile_section = ""
    if student_profile_summary:
        profile_section = (
            f"\n\n## 学生画像\n{student_profile_summary}\n"
            "请根据学生的知识水平和学习风格调整解释深度和方式。"
        )

    history_section = ""
    if conversation_history:
        history_section = (
            f"\n\n## 之前的对话\n{conversation_history}\n"
        )

    # Task 1: Answer the question
    answer_task = Task(
        description=(
            f"## 学生提问\n{student_question}\n"
            f"{history_section}"
            f"{profile_section}"
            f"{rag_section}\n\n"
            f"## 回答要求\n"
            f"1. 先确认你理解了学生的问题（一句话复述）\n"
            f"2. 给出核心答案（直接、准确、不绕弯子）\n"
            f"3. 提供代码示例（必须是可运行的JavaScript代码，用```javascript包裹）\n"
            f"4. 解释代码的关键部分（标注行内注释）\n"
            f"5. 如果有常见误区，简要提醒\n"
            f"6. 如果问题涉及多个知识点，说明它们之间的关系\n\n"
            f"## 长度控制\n"
            f"- 简单概念问题：200-400字\n"
            f"- 需要代码示例的问题：400-800字\n"
            f"- 复杂多知识点问题：800-1200字\n\n"
            f"请用中文回答，Markdown格式。"
        ),
        expected_output=(
            "结构化的中文解答，包含：核心答案、代码示例（```javascript）、"
            "关键解释、常见误区提醒。Markdown格式。"
        ),
        agent=tutor,
    )

    if step_callback:
        answer_task.callback = step_callback

    # Task 2: Enhance with multi-modal explanation
    explain_task = Task(
        description=(
            f"辅导教师已针对学生问题「{student_question}」给出了文字解答。\n"
            f"请阅读辅导教师的解答，为其生成以下增强内容：\n\n"
            f"## 需要生成的增强内容\n\n"
            f"1. **分步理解指南**: 如果概念较复杂，用2-5个步骤拆解理解过程\n"
            f"2. **可视化描述**: 如果概念涉及数据流动或执行过程（如事件循环、"
            f"闭包、原型链、this绑定），生成一个动画场景描述\n"
            f"3. **概念对比表**: 如果涉及容易混淆的概念（如let/const/var、"
            f"==/===、apply/call/bind、Promise/async-await），"
            f"生成Markdown对比表格\n"
            f"4. **记忆口诀**: 为知识点生成一个简短易记的中文口诀\n"
            f"5. **相关知识点**: 列出2-3个相关的JavaScript知识点及简要说明\n\n"
            f"## 输出格式\n"
            f"请输出以下JSON格式的结构化增强内容：\n"
            f'{{"steps": [{{"step": 1, "title": "...", "content": "..."}}], '
            f'"animation_scene": {{"description": "...", '
            f'"steps": [{{"action": "...", "narration": "..."}}]}}, '
            f'"comparison_table": {{"headers": ["特性", "A", "B"], '
            f'"rows": [["...", "...", "..."]]}}, '
            f'"mnemonic": "...", '
            f'"related_topics": [{{"topic": "...", "relation": "..."}}]}}\n\n'
            f"注意：并非所有问题都需要全部5项增强。根据问题的性质选择性生成最合适的增强类型。"
            f"如果没有可生成的增强类型，对应字段返回null。"
        ),
        expected_output="JSON格式的多模态增强内容，字段可为null。",
        agent=explainer,
    )

    if step_callback:
        explain_task.callback = step_callback

    return Crew(
        agents=[tutor, explainer],
        tasks=[answer_task, explain_task],
        process=Process.sequential,
        verbose=False,
    )
