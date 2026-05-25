"""ProfileCrew: ProfileInterviewer + ProfileAnalyzer in Sequential process.

The interviewer conducts a natural-language conversation to understand the
student's JavaScript knowledge level. The analyzer extracts structured
6-dimension profile data from the interview transcript.
"""

import json
from collections.abc import Callable

from crewai import Agent, Crew, Process, Task

from app.agents.llm_config import (
    get_spark_llm,
    INTERVIEWER_TEMPERATURE,
    ANALYZER_TEMPERATURE,
)
from app.agents.tools.profile_tool import update_student_profile


def _create_interviewer() -> Agent:
    llm = get_spark_llm(temperature=INTERVIEWER_TEMPERATURE)
    return Agent(
        role="JavaScript学习画像面试官",
        goal=(
            "通过友好的对话了解学生在JavaScript各知识领域的掌握程度、"
            "学习习惯、常见困难和学习目标。每次只问1-2个有针对性的问题，"
            "逐步深入了解学生的真实水平。"
        ),
        backstory=(
            "你是一位经验丰富的编程教师，拥有10年JavaScript教学经验。"
            "你善于通过开放式问题引导学生表达自己的知识边界，"
            "能够从学生的回答中判断其真实理解深度。"
            "你的访谈风格亲切但不失专业，用中文与学生交流。"
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def _create_analyzer() -> Agent:
    llm = get_spark_llm(temperature=ANALYZER_TEMPERATURE)
    return Agent(
        role="学习画像分析专家",
        goal=(
            "根据面试对话内容，精确分析学生画像的6个维度："
            "知识基础(knowledge_foundation)、认知风格(cognitive_style)、"
            "常见错误模式(common_errors)、学习偏好(learning_preferences)、"
            "学习目标(learning_goals)、时间投入(time_commitment)。"
            "对每个维度调用 update_student_profile 工具保存分析结果。"
        ),
        backstory=(
            "你是教育心理学专家，同时精通JavaScript技术栈。"
            "你擅长从对话中提取关键信息，判断学生对各知识点的掌握程度，"
            "识别其学习风格和常见错误模式。你的分析客观精准，"
            "每个结论都有对话内容作为依据。"
        ),
        tools=[update_student_profile],
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def build_profile_crew(
    conversation_history: str,
    user_message: str,
    rag_context: str = "",
    step_callback: Callable | None = None,
) -> Crew:
    """Build a ProfileCrew for one round of profile interview.

    Args:
        conversation_history: Formatted chat history string.
        user_message: The latest user message to respond to.
        rag_context: RAG-retrieved knowledge base snippets for accuracy.
        step_callback: Optional callback(step_output) for each agent step.

    Returns:
        Configured Crew instance. Call crew.kickoff() to run.
    """
    interviewer = _create_interviewer()
    analyzer = _create_analyzer()

    rag_section = ""
    if rag_context:
        rag_section = (
            "\n\n参考以下JavaScript知识库内容（必须基于此内容回答，不可自由发挥）：\n"
            f"{rag_context}\n"
        )

    interview_task = Task(
        description=(
            f"以下是学生画像访谈的对话历史：\n\n{conversation_history}\n\n"
            f"学生最新消息：{user_message}\n"
            f"{rag_section}\n"
            "请以JavaScript面试官的身份，用中文回复学生。"
            "根据学生的回答，判断其JS知识水平并适当追问以深入了解。"
            "每轮只问1-2个问题，保持对话自然流畅。"
        ),
        expected_output=(
            "一段中文回复，包含对学生的回应和1-2个后续问题。"
            "回复应体现对学生回答的理解，并针对性地深入询问。"
        ),
        agent=interviewer,
    )

    if step_callback:
        interview_task.callback = step_callback

    analyze_task = Task(
        description=(
            "基于以下完整的访谈对话记录，分析学生画像的6个维度。\n\n"
            f"完整对话记录：\n{conversation_history}\n"
            f"学生最新消息：{user_message}\n\n"
            "请逐一分析以下6个维度，对每个维度调用 "
            "update_student_profile(dimension, value) 工具保存结果：\n\n"
            "1. knowledge_foundation: 以JSON对象表示各知识点掌握程度，"
            "   mastery取值：beginner/intermediate/advanced/expert\n"
            "   示例：{\"js_var_let_const\": \"intermediate\", \"js_closure\": \"beginner\"}\n\n"
            "2. cognitive_style: 学生的学习风格\n"
            "   取值：visual/auditory/kinesthetic/reading_writing/mixed/unknown\n\n"
            "3. common_errors: JSON数组，记录常见错误模式\n"
            "   示例：[{\"pattern\": \"var作用域混淆\", \"topic\": \"js_var_let_const\", \"frequency\": 3}]\n\n"
            "4. learning_preferences: JSON对象，包含resource_types(数组)和pace(字符串)\n"
            "   示例：{\"resource_types\": [\"code_case\", \"exercise\"], \"pace\": \"moderate\"}\n\n"
            "5. learning_goals: JSON数组，记录学习目标\n"
            "   示例：[{\"goal\": \"掌握闭包\", \"priority\": \"high\", \"target_date\": null}]\n\n"
            "6. time_commitment: 可用学习时间\n"
            "   取值：minimal/moderate/substantial/intensive\n\n"
            "注意：每个维度都必须调用 update_student_profile 工具。"
            "如果某个维度没有足够信息，请标注为 unknown/空。"
        ),
        expected_output=(
            "确认所有6个维度已通过 update_student_profile 工具更新。"
        ),
        agent=analyzer,
    )

    if step_callback:
        analyze_task.callback = step_callback

    return Crew(
        agents=[interviewer, analyzer],
        tasks=[interview_task, analyze_task],
        process=Process.sequential,
        verbose=False,
    )
