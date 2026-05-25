"""Agent tools for CrewAI agents.

Tools provide agents with abilities beyond text generation:
- knowledge_tool: RAG knowledge base retrieval
- code_exec_tool: Deno sandbox JS execution
- safety_tool: Content safety and quality checks
- graph_tool: Knowledge graph queries
- multimodal_tool: Animation script/PPT formatting and validation
- profile_tool: Student profile dimension updates
"""

from app.agents.tools.code_exec_tool import execute_javascript
from app.agents.tools.graph_tool import create_graph_tool
from app.agents.tools.knowledge_tool import create_knowledge_tool
from app.agents.tools.multimodal_tool import (
    format_animation_script,
    format_ppt_slides,
    text_to_speech_placeholder,
)
from app.agents.tools.profile_tool import update_student_profile
from app.agents.tools.safety_tool import check_code_quality, check_content_safety

__all__ = [
    "create_knowledge_tool",
    "create_graph_tool",
    "execute_javascript",
    "check_content_safety",
    "check_code_quality",
    "update_student_profile",
    "format_animation_script",
    "format_ppt_slides",
    "text_to_speech_placeholder",
]
