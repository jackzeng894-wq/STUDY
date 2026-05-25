"""RAG knowledge retrieval tool for CrewAI agents.

Provides knowledge-grounded context to prevent hallucination.
All generated content must reference knowledge base snippets.
"""

import re

from crewai.tools import tool


def create_knowledge_tool(rag_context: str = ""):
    """Create a knowledge retrieval tool with pre-loaded RAG context.

    The service pre-loads relevant knowledge base snippets via the RAG
    pipeline, then injects them here. Agents call this tool to search
    within the pre-loaded context or retrieve specific topic details.

    Args:
        rag_context: Pre-retrieved knowledge base content (Markdown).
    """

    @tool("search_knowledge")
    def search_knowledge(query: str) -> str:
        """Search the JavaScript knowledge base for information about a topic.

        Use this tool BEFORE generating any learning content. It returns
        authoritative knowledge base snippets that you must base your
        output on. Never fabricate JavaScript facts not found here.

        Args:
            query: Topic or keyword to search for (e.g. "闭包", "事件循环",
                   "原型链", "Promise", "let const var 区别").
        Returns:
            Relevant knowledge base content, or a message indicating no results.
        """
        if not rag_context:
            return (
                "（知识库不可用。请基于通用JavaScript知识回答，"
                "并告知学生此内容未经知识库验证。）"
            )

        # Search within the pre-loaded context
        keywords = _extract_keywords(query)
        sections = rag_context.split("\n\n---\n\n")
        matched = []

        for section in sections:
            score = sum(1 for kw in keywords if kw.lower() in section.lower())
            if score > 0:
                matched.append((score, section))

        matched.sort(key=lambda x: x[0], reverse=True)

        if not matched:
            return (
                f"（在知识库中未找到与 '{query}' 直接相关的内容。"
                "请基于已有的相关知识库片段回答，不要编造内容。）\n\n"
                f"可用知识库内容概览：\n{_summarize_sections(sections)}"
            )

        # Return top matches, limited to avoid context overflow
        result_sections = []
        total_chars = 0
        for _, section in matched[:3]:
            if total_chars + len(section) > 3000:
                break
            result_sections.append(section)
            total_chars += len(section)

        return "\n\n---\n\n".join(result_sections)

    return search_knowledge


def _extract_keywords(query: str) -> list[str]:
    """Extract meaningful keywords from a query string."""
    # Remove common filler words and split
    cleaned = re.sub(r'[，。！？、；：""''（）\s]+', ' ', query)
    # Keep both the full query and individual words
    keywords = [query.strip(), *cleaned.split()]
    # Deduplicate while preserving order
    seen = set()
    result = []
    for kw in keywords:
        if kw and kw not in seen:
            seen.add(kw)
            result.append(kw)
    return result


def _summarize_sections(sections: list[str]) -> str:
    """Extract section titles for a summary overview."""
    titles = []
    for s in sections:
        match = re.search(r'^##\s+(.+)', s, re.MULTILINE)
        if match:
            titles.append(f"- {match.group(1)}")
    return "\n".join(titles) if titles else "（无章节标题）"
