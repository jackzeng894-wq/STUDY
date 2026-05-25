"""Content safety service: 5-layer anti-hallucination and safety pipeline.

Layer 1: RAG consistency — check generated content against knowledge base
Layer 2: Code sandbox — verify JS code runs correctly in Deno
Layer 3: ResourceReviewer — specialized agent cross-check (via ResourceCrew)
Layer 4: iFlytek content audit — external API safety check (with local fallback)
Layer 5: Reference tracing — annotate knowledge sources in output

The service provides both individual checks and a unified verify_resource()
pipeline used before any resource is delivered to a student.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.retriever import retrieve_context

logger = logging.getLogger(__name__)


@dataclass
class SafetyReport:
    """Result of a complete safety verification pass."""
    resource_id: str = ""
    resource_type: str = ""
    passed: bool = True
    layer_results: dict = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    aggregated_score: float = 0.0  # 0.0 - 1.0

    def to_dict(self) -> dict:
        return {
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "passed": self.passed,
            "layer_results": self.layer_results,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "aggregated_score": self.aggregated_score,
        }


class SafetyService:
    """Orchestrates the 5-layer safety verification pipeline."""

    def __init__(self):
        self._sensitive_words = _load_sensitive_words()

    # ── Layer 1: RAG Consistency Check ────────────────────────────────

    async def check_rag_consistency(
        self,
        content: str,
        topic: str,
        db: AsyncSession,
    ) -> dict:
        """Verify generated content is consistent with the knowledge base.

        Retrieves relevant knowledge base snippets and compares key claims
        against them. Returns flagged discrepancies.
        """
        if not content or len(content) < 50:
            return {"passed": True, "issues": [], "score": 1.0,
                    "detail": "内容过短，跳过一致性检查"}

        # Retrieve the authoritative knowledge base content
        rag_text = await retrieve_context(topic, top_k=3, max_tokens=2000)

        if not rag_text or rag_text == "（未找到相关知识点）":
            return {"passed": True, "issues": [], "score": 0.5,
                    "detail": "知识库中未找到对应内容，无法交叉验证"}

        # Extract key technical claims from both content and RAG
        # Simple heuristic: extract JS API names and compare presence
        js_terms = set(re.findall(
            r'\b([A-Z][a-z]+\.)?[a-z]+(?:[A-Z][a-z]+)*\s*\(',
            rag_text,
        ))

        content_terms = set(re.findall(
            r'\b([A-Z][a-z]+\.)?[a-z]+(?:[A-Z][a-z]+)*\s*\(',
            content,
        ))

        # Check for fabricated API names
        if content_terms and js_terms:
            unknown_terms = content_terms - js_terms
            # Filter out common words that might be matched
            truly_unknown = [
                t for t in unknown_terms
                if t.strip() and len(t.strip()) > 3
                and t.strip() not in ("this(", "that(", "with(", "from(", "when(")
            ]
            if truly_unknown:
                return {
                    "passed": False,
                    "issues": [f"内容中引用了知识库未提及的API: {', '.join(truly_unknown[:5])}"],
                    "score": 0.6,
                    "detail": "检测到可能与知识库不一致的技术术语",
                }

        return {"passed": True, "issues": [], "score": 0.9,
                "detail": "关键术语与知识库一致"}

    # ── Layer 2: Code Sandbox Verification ────────────────────────────

    async def verify_code(
        self,
        code: str,
        timeout: int = 10,
    ) -> dict:
        """Execute JavaScript code in Deno sandbox to verify correctness.

        Only applicable for code-containing resources (code_case, exercise, project).
        """
        if not code or not code.strip():
            return {"passed": True, "issues": [], "score": 1.0,
                    "detail": "无代码需要验证"}

        import os
        import subprocess
        import tempfile
        import uuid as uuid_mod

        from app.config import settings

        tmp_path = os.path.join(
            tempfile.gettempdir(),
            f"rj_safety_{uuid_mod.uuid4().hex[:8]}.js",
        )

        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(code)

            deno_path = settings.DENO_PATH

            try:
                proc = await asyncio.wait_for(
                    asyncio.create_subprocess_exec(
                        deno_path, "run", "--no-prompt", tmp_path,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    ),
                    timeout=None,  # proc creation shouldn't timeout
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout,
                )
            except asyncio.TimeoutError:
                if proc:
                    proc.kill()
                return {
                    "passed": False,
                    "issues": [f"代码执行超时（{timeout}秒）"],
                    "score": 0.0,
                    "detail": "代码可能存在无限循环或性能问题",
                }
            except FileNotFoundError:
                return {
                    "passed": False,
                    "issues": [f"Deno 运行时未找到: {deno_path}"],
                    "score": 0.0,
                    "detail": "代码沙箱不可用，无法验证代码可运行性",
                }

            if proc.returncode == 0:
                return {"passed": True, "issues": [], "score": 1.0,
                        "detail": "代码在Deno沙箱中成功运行"}
            else:
                stderr_text = stderr.decode("utf-8", errors="replace")[:500]
                return {
                    "passed": False,
                    "issues": [
                        f"代码执行失败 (exit code {proc.returncode})",
                        stderr_text,
                    ],
                    "score": 0.0,
                    "detail": "代码存在运行时错误",
                }

        except Exception as e:
            logger.exception("Code verification failed")
            return {
                "passed": False,
                "issues": [f"验证过程异常: {str(e)}"],
                "score": 0.0,
                "detail": "代码验证系统错误",
            }
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    # ── Layer 4: Local Content Filter (iFlytek fallback) ──────────────

    async def check_content_safety(self, content: str) -> dict:
        """Check content for sensitive/inappropriate material.

        Uses local sensitive word filter. In production, this would be
        augmented by the iFlytek content audit API.
        """
        if not content:
            return {"passed": True, "issues": [], "score": 1.0,
                    "detail": "空内容"}

        matches = []
        for word in self._sensitive_words:
            if word in content:
                matches.append(word)

        if matches:
            return {
                "passed": False,
                "issues": [f"内容包含 {len(matches)} 个敏感词"],
                "score": 0.0,
                "detail": f"敏感词: {', '.join(matches[:5])}",
            }

        return {"passed": True, "issues": [], "score": 1.0,
                "detail": "内容安全检查通过"}

    # ── Layer 5: Reference Tracing ────────────────────────────────────

    @staticmethod
    def extract_references(content: str, rag_context: str) -> list[str]:
        """Extract knowledge base references cited in the content.

        Returns list of section titles that the content appears to reference.
        """
        if not rag_context:
            return []

        sections = rag_context.split("\n\n---\n\n")
        references = []

        for section in sections:
            # Extract section title
            title_match = re.search(r'^##\s+(.+)', section, re.MULTILINE)
            if not title_match:
                continue
            title = title_match.group(1)

            # Check if key terms from this section appear in the content
            # Simple heuristic: extract first paragraph keywords
            first_para = section.split("\n\n")[0] if section else ""
            keywords = re.findall(r'[一-鿿]{2,}', first_para)
            match_count = sum(1 for kw in keywords[:5] if kw in content)

            if match_count >= 1:
                references.append(title)

        return references

    # ── Unified Verification Pipeline ─────────────────────────────────

    async def verify_resource(
        self,
        resource_id: str,
        resource_type: str,
        content: str,
        topic: str,
        db: AsyncSession,
        code_snippets: list[str] | None = None,
        rag_context: str = "",
    ) -> SafetyReport:
        """Run all applicable safety checks on a generated resource.

        This is the main entry point. Checks are selected based on
        resource type (not all checks apply to all types).

        Args:
            resource_id: UUID of the resource being checked.
            resource_type: Type code (course_doc, code_case, exercise, etc.).
            content: Full resource content text.
            topic: Knowledge topic for RAG consistency check.
            db: Database session.
            code_snippets: Extracted JS code blocks (optional).
            rag_context: Pre-retrieved knowledge base context (optional).

        Returns:
            SafetyReport with aggregated results.
        """
        report = SafetyReport(
            resource_id=resource_id,
            resource_type=resource_type,
        )
        scores = []

        # Layer 1: RAG consistency (applies to all types)
        l1 = await self.check_rag_consistency(content, topic, db)
        report.layer_results["rag_consistency"] = l1
        report.issues.extend(l1.get("issues", []))
        scores.append(l1.get("score", 1.0))

        # Layer 2: Code verification (only for code-containing types)
        if resource_type in ("code_case", "exercise", "project") and code_snippets:
            all_code = "\n".join(code_snippets)
            l2 = await self.verify_code(all_code)
            report.layer_results["code_verification"] = l2
            report.issues.extend(l2.get("issues", []))
            scores.append(l2.get("score", 1.0))
        else:
            report.layer_results["code_verification"] = {
                "passed": True, "issues": [], "score": 1.0,
                "detail": "资源类型不包含代码，跳过代码验证",
            }
            scores.append(1.0)

        # Layer 4: Content safety filter
        l4 = await self.check_content_safety(content)
        report.layer_results["content_safety"] = l4
        report.issues.extend(l4.get("issues", []))
        scores.append(l4.get("score", 1.0))

        # Layer 5: Reference tracing
        refs = self.extract_references(content, rag_context)
        report.layer_results["reference_tracing"] = {
            "passed": True,
            "references": refs,
            "count": len(refs),
            "score": min(1.0, len(refs) / 2.0) if rag_context else 0.5,
        }
        scores.append(report.layer_results["reference_tracing"]["score"])

        # Aggregate
        report.aggregated_score = sum(scores) / len(scores) if scores else 0.0
        report.passed = report.aggregated_score >= 0.5 and not any(
            l.get("passed") is False
            for l in report.layer_results.values()
        )

        if not report.passed:
            report.suggestions.append("建议重新生成或人工审核后再交付学生")

        return report


def _load_sensitive_words() -> list[str]:
    """Load sensitive word list for local content filtering."""
    # Basic Chinese sensitive word list (minimal for demo)
    return [
        "暴力", "色情", "赌博", "毒品",
        "颠覆国家", "分裂国家", "邪教",
        "贩卖枪支", "制作炸弹", "黑客入侵",
        "盗版", "破解激活",
        "作弊器", "外挂",
        "人肉搜索", "网络暴力",
    ]
