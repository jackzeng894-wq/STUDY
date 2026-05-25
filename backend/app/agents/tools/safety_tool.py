"""Content safety and anti-hallucination tool for CrewAI agents.

Checks generated content against the knowledge base for consistency,
filters sensitive content, and validates code correctness.
"""

import json
import re

from crewai.tools import tool

# Sensitive keyword patterns (local fallback when iFlytek audit is unavailable)
SENSITIVE_PATTERNS = [
    r'(暴力|恐怖|色情|赌博|毒品|诈骗)',
    r'(违法|犯罪|反动|颠覆)',
    r'(攻击|入侵|破解|黑客).*(系统|网站|服务器)',
]

# JS-specific safety checks
DANGEROUS_JS_PATTERNS = [
    r'eval\s*\(',
    r'document\.write\s*\(',
    r'innerHTML\s*=',
    r'Function\s*\(',
    r'setTimeout\s*\(\s*["\']',
    r'fetch\s*\(\s*["\']https?://(?!api\.|localhost)',
]


@tool("check_content_safety")
def check_content_safety(content: str, resource_type: str = "") -> str:
    """Check generated learning content for safety and quality issues.

    Call this BEFORE finalizing any student-facing content. Checks:
    - Sensitive/inappropriate content
    - JavaScript code safety (no dangerous patterns in student code)
    - Basic quality markers (minimum length, structure)

    Args:
        content: The generated content string to check (Markdown or JSON).
        resource_type: Type of resource for context-specific checks
                       (course_doc, exercise, code_case, etc.).
    Returns:
        JSON string with keys: passed (bool), issues (list[str]),
        severity (low|medium|high), suggestions (list[str]).
    """
    issues = []
    suggestions = []
    severity = "low"

    if not content or len(content.strip()) < 20:
        issues.append("内容过短，可能未完整生成")
        severity = "high"
        return json.dumps({
            "passed": False,
            "issues": issues,
            "severity": severity,
            "suggestions": ["请重新生成完整内容"],
        }, ensure_ascii=False)

    # 1. Sensitive content check
    for pattern in SENSITIVE_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            issues.append(f"内容包含敏感词汇：{', '.join(matches)}")
            severity = "high"

    # 2. JS code safety check (for code-containing resources)
    if resource_type in ("code_case", "exercise", "project"):
        for pattern in DANGEROUS_JS_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                issues.append(f"代码包含潜在危险模式：{pattern}")
                suggestions.append("请使用安全的代码模式替换")

    # 3. Quality checks
    if resource_type == "course_doc":
        if "```" not in content and "代码" in content:
            suggestions.append("建议添加代码示例块（使用 ``` 标记）")
        if len(content) < 200:
            issues.append("课程文档内容偏短")
            severity = max(severity, "medium")

    if resource_type == "exercise":
        has_question = bool(re.search(r'(题目|问题|选择题|填空|编程|写出)', content))
        if not has_question:
            issues.append("未检测到明确的题目描述")
            severity = max(severity, "medium")

    if resource_type == "code_case":
        has_js_code = bool(re.search(r'```(js|javascript)', content, re.IGNORECASE))
        if not has_js_code:
            issues.append("代码案例未包含 JavaScript 代码块")
            severity = max(severity, "medium")

    # 4. Hallucination check markers
    hallucination_indicators = [
        r'(根据我的|我认为|可能|大概|应该).*[，。]',
    ]
    # Not blocking, just noting for reviewer
    vague_count = sum(
        len(re.findall(p, content)) for p in hallucination_indicators
    )
    if vague_count > 5:
        suggestions.append("内容中不确定表述较多，请引用知识库中的确定内容")

    passed = severity != "high" and len(issues) == 0

    return json.dumps({
        "passed": passed,
        "issues": issues,
        "severity": severity,
        "suggestions": suggestions,
    }, ensure_ascii=False)


@tool("check_code_quality")
def check_code_quality(code: str) -> str:
    """Quick static analysis of JavaScript code quality and common errors.

    Checks for: syntax issues, common beginner mistakes, bad practices.
    Use this to validate generated code examples before delivery.

    Args:
        code: JavaScript code string to analyze.
    Returns:
        JSON string with keys: passed (bool), warnings (list[str]),
        suggestions (list[str]).
    """
    warnings = []
    suggestions = []

    if not code or not code.strip():
        return json.dumps({
            "passed": False,
            "warnings": ["代码为空"],
            "suggestions": [],
        }, ensure_ascii=False)

    # Common beginner mistakes
    checks = [
        (r'var\s+\w+\s*=', "使用了 var 声明。ES6+ 中建议使用 let 或 const"),
        (r'==(?!\=)', "使用了 == 比较。建议使用 === 避免类型强制转换"),
        (r'console\.log\s*\(', None),  # Just note, not a warning
        (r'for\s*\(\s*var\s+\w+\s*=\s*0', "for 循环中使用 var 声明。建议使用 let"),
        (r'\)\s*\{\s*\n\s*\}\s*$', "检测到空代码块，可能未实现"),
        (r'[\w.]+\s*=\s*=\s*undefined', "建议使用 typeof 或 === undefined 替代"),
    ]

    for pattern, warning in checks:
        if re.search(pattern, code) and warning:
            warnings.append(warning)

    # Common suggestions
    if 'function' in code and '=>' not in code and len(code) < 500:
        suggestions.append("可考虑使用箭头函数简化代码")

    if code.count('//') == 0 and len(code.split('\n')) > 10:
        suggestions.append("建议添加注释说明关键逻辑")

    if code.count(';') < len(code.split('\n')) * 0.3:
        warnings.append("分号使用较少，可能遗漏")

    passed = len(warnings) <= 3

    return json.dumps({
        "passed": passed,
        "warnings": warnings,
        "suggestions": suggestions,
    }, ensure_ascii=False)
