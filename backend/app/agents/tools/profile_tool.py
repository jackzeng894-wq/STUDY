"""Profile tool for CrewAI agents: validate and format profile dimension updates.

The tool validates profile data structure; actual DB writes are handled
by profile_service after crew completion.
"""

import json

from crewai.tools import tool

VALID_DIMENSIONS = {
    "knowledge_foundation",
    "cognitive_style",
    "common_errors",
    "learning_preferences",
    "learning_goals",
    "time_commitment",
}

VALID_COGNITIVE_STYLES = {
    "visual", "auditory", "kinesthetic", "reading_writing", "mixed", "unknown"
}

VALID_TIME_COMMITMENTS = {"minimal", "moderate", "substantial", "intensive"}


@tool("update_student_profile")
def update_student_profile(dimension: str, value: str) -> str:
    """Update one dimension of the student's learning profile.

    Called by ProfileAnalyzer after analyzing interview responses.
    Args:
        dimension: One of: knowledge_foundation, cognitive_style, common_errors,
                   learning_preferences, learning_goals, time_commitment
        value: JSON string of the dimension value. Format depends on dimension:
               - knowledge_foundation: {"topic_code": "mastery", ...}
               - cognitive_style: e.g. "visual"
               - common_errors: [{"pattern": "...", "topic": "...", "frequency": N}, ...]
               - learning_preferences: {"resource_types": [...], "pace": "moderate"}
               - learning_goals: [{"goal": "...", "priority": "high", "target_date": null}, ...]
               - time_commitment: "moderate"
    Returns:
        Confirmation string describing what was updated.
    """
    if dimension not in VALID_DIMENSIONS:
        return f"错误: 无效的画像维度 '{dimension}'。有效维度: {', '.join(sorted(VALID_DIMENSIONS))}"

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return f"错误: value 必须是有效的 JSON 字符串。收到: {value[:100]}"

    # Validate per dimension
    if dimension == "cognitive_style":
        if isinstance(parsed, str) and parsed in VALID_COGNITIVE_STYLES:
            return f"已更新认知风格为: {parsed}"
        return f"错误: cognitive_style 必须是以下之一: {', '.join(sorted(VALID_COGNITIVE_STYLES))}"

    if dimension == "time_commitment":
        if isinstance(parsed, str) and parsed in VALID_TIME_COMMITMENTS:
            return f"已更新时间投入为: {parsed}"
        return f"错误: time_commitment 必须是以下之一: {', '.join(sorted(VALID_TIME_COMMITMENTS))}"

    if dimension == "knowledge_foundation":
        if isinstance(parsed, dict):
            topics = len(parsed)
            return f"已更新知识基础，覆盖 {topics} 个知识点"
        return "错误: knowledge_foundation 必须是 JSON 对象 {topic_code: mastery}"

    if dimension == "common_errors":
        if isinstance(parsed, list):
            return f"已更新常见错误模式，共 {len(parsed)} 个"
        return "错误: common_errors 必须是 JSON 数组"

    if dimension == "learning_preferences":
        if isinstance(parsed, dict):
            return f"已更新学习偏好"
        return "错误: learning_preferences 必须是 JSON 对象"

    if dimension == "learning_goals":
        if isinstance(parsed, list):
            return f"已更新学习目标，共 {len(parsed)} 个"
        return "错误: learning_goals 必须是 JSON 数组"

    return f"已更新 {dimension}"
