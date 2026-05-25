"""Multi-modal generation tool for CrewAI agents.

Provides formatting and validation for multi-modal resource types:
video/animation scripts, PPT slide data, text-to-speech integration.
External API calls (SeeDance, iFlytek TTS/PPT) are handled with
timeout + retry + graceful degradation.
"""

import json
import logging

from crewai.tools import tool

logger = logging.getLogger(__name__)

# Animation instruction vocabulary for VideoAnimator
VALID_ANIMATION_TYPES = {
    "fade_in", "fade_out", "slide_in", "slide_out", "zoom_in",
    "typewriter", "highlight", "pulse", "morph", "code_execute",
    "flow_chart", "compare_side_by_side", "stack_trace", "memory_diagram",
}

VALID_EASING = {"linear", "ease_in", "ease_out", "ease_in_out"}


@tool("format_animation_script")
def format_animation_script(script_json: str) -> str:
    """Validate and format a teaching animation script into proper structure.

    Call this after generating an animation script (R8 resource) to
    validate its structure before storage. Ensures the frontend can
    render the animation correctly.

    Args:
        script_json: JSON string of the animation script with structure:
            {
              "title": "动画标题",
              "description": "概述",
              "scenes": [
                {
                  "scene_id": 1,
                  "narration": "旁白文本",
                  "duration_seconds": 10,
                  "animation_type": "fade_in|code_execute|...",
                  "animation_params": {},
                  "code_snippet": "可选，代码演示"
                }
              ]
            }
    Returns:
        JSON string with keys: valid (bool), formatted_script (dict|null),
        errors (list[str]), warnings (list[str]).
    """
    errors = []
    warnings = []

    try:
        script = json.loads(script_json)
    except json.JSONDecodeError as e:
        return json.dumps({
            "valid": False,
            "formatted_script": None,
            "errors": [f"JSON解析失败: {str(e)}"],
            "warnings": [],
        }, ensure_ascii=False)

    if not isinstance(script, dict):
        return json.dumps({
            "valid": False,
            "formatted_script": None,
            "errors": ["脚本必须是JSON对象"],
            "warnings": [],
        }, ensure_ascii=False)

    # Validate structure
    if "title" not in script:
        errors.append("缺少 title 字段")
    if "scenes" not in script:
        errors.append("缺少 scenes 数组")
    elif not isinstance(script.get("scenes"), list):
        errors.append("scenes 必须是数组")
    elif len(script["scenes"]) == 0:
        errors.append("scenes 不能为空")

    if "scenes" in script and isinstance(script["scenes"], list):
        for i, scene in enumerate(script["scenes"]):
            if not isinstance(scene, dict):
                errors.append(f"场景 {i} 必须是对象")
                continue

            if "narration" not in scene or not scene.get("narration"):
                warnings.append(f"场景 {i}: 缺少旁白文本")
            if "animation_type" in scene:
                at = scene["animation_type"]
                if at not in VALID_ANIMATION_TYPES:
                    warnings.append(f"场景 {i}: 未知动画类型 '{at}'，将使用默认类型")
            if "duration_seconds" not in scene:
                scene["duration_seconds"] = 10  # default
                warnings.append(f"场景 {i}: 未指定时长，默认为10秒")

    # Ensure required fields with defaults
    formatted = {
        "title": script.get("title", "未命名动画"),
        "description": script.get("description", ""),
        "estimated_total_seconds": script.get(
            "estimated_total_seconds",
            sum(s.get("duration_seconds", 10) for s in script.get("scenes", [])),
        ),
        "knowledge_point": script.get("knowledge_point", ""),
        "scenes": [],
    }

    for i, scene in enumerate(script.get("scenes", [])):
        formatted["scenes"].append({
            "scene_id": scene.get("scene_id", i + 1),
            "narration": scene.get("narration", ""),
            "duration_seconds": scene.get("duration_seconds", 10),
            "animation_type": scene.get("animation_type", "fade_in"),
            "animation_params": scene.get("animation_params", {}),
            "code_snippet": scene.get("code_snippet"),
            "diagram_data": scene.get("diagram_data"),
        })

    valid = len(errors) == 0

    return json.dumps({
        "valid": valid,
        "formatted_script": formatted if valid else None,
        "errors": errors,
        "warnings": warnings,
    }, ensure_ascii=False)


@tool("format_ppt_slides")
def format_ppt_slides(slides_json: str) -> str:
    """Validate and format PPT slide data for teaching presentations.

    Call this after generating PPT content (R5 resource) to validate
    the slide structure before storage. The frontend renders slides
    from this JSON structure.

    Args:
        slides_json: JSON string with structure:
            {
              "title": "PPT标题",
              "slides": [
                {
                  "slide_number": 1,
                  "title": "页面标题",
                  "content_type": "text|code|diagram|bullets|comparison",
                  "content": "Markdown内容",
                  "notes": "讲师备注",
                  "layout": "title_content|two_column|code_focus|full_image"
                }
              ]
            }
    Returns:
        JSON string with keys: valid (bool), formatted_slides (dict|null),
        errors (list[str]).
    """
    errors = []

    try:
        data = json.loads(slides_json)
    except json.JSONDecodeError as e:
        return json.dumps({
            "valid": False,
            "formatted_slides": None,
            "errors": [f"JSON解析失败: {str(e)}"],
        }, ensure_ascii=False)

    if not isinstance(data, dict):
        return json.dumps({
            "valid": False,
            "formatted_slides": None,
            "errors": ["幻灯片数据必须是JSON对象"],
        }, ensure_ascii=False)

    if "slides" not in data:
        errors.append("缺少 slides 数组")

    slides = data.get("slides", [])
    if not isinstance(slides, list) or len(slides) == 0:
        errors.append("slides 必须是非空数组")

    valid_types = {"text", "code", "diagram", "bullets", "comparison"}
    valid_layouts = {"title_content", "two_column", "code_focus", "full_image"}

    formatted = {
        "title": data.get("title", "未命名PPT"),
        "total_slides": len(slides),
        "slides": [],
    }

    for i, slide in enumerate(slides):
        content_type = slide.get("content_type", "text")
        if content_type not in valid_types:
            errors.append(f"幻灯片 {i+1}: 无效的 content_type '{content_type}'")

        formatted["slides"].append({
            "slide_number": slide.get("slide_number", i + 1),
            "title": slide.get("title", ""),
            "content_type": content_type,
            "content": slide.get("content", ""),
            "notes": slide.get("notes", ""),
            "layout": slide.get("layout", "title_content")
            if slide.get("layout", "") in valid_layouts
            else "title_content",
        })

    return json.dumps({
        "valid": len(errors) == 0,
        "formatted_slides": formatted if not errors else None,
        "errors": errors,
    }, ensure_ascii=False)


@tool("text_to_speech_placeholder")
def text_to_speech_placeholder(text: str) -> str:
    """Check if text is suitable for TTS conversion (length, structure).

    Note: Actual TTS API integration (iFlytek TTS) is handled by the
    service layer. This tool validates that the text meets TTS requirements.

    Args:
        text: The text to check for TTS-readiness.
    Returns:
        JSON: {suitable: bool, estimated_duration_seconds: int, issues: list[str]}
    """
    issues = []
    char_count = len(text)

    if char_count < 10:
        issues.append("文本过短，不适合TTS")

    if char_count > 5000:
        issues.append(f"文本过长 ({char_count}字符)，建议分段")

    # Chinese text check: at least some Chinese characters
    chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
    if chinese_chars == 0:
        issues.append("未检测到中文字符，TTS可能发音不准确")

    # Estimate: Chinese TTS ~4 chars/second
    estimated_seconds = char_count // 4

    return json.dumps({
        "suitable": len(issues) == 0,
        "estimated_duration_seconds": max(1, estimated_seconds),
        "issues": issues,
    }, ensure_ascii=False)
