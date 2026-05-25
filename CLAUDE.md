# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

第十五届中国软件杯大赛A组赛题 —— 基于大模型的个性化资源生成与学习多智能体系统。为 JavaScript 课程构建个性化学习平台，通过 CrewAI 多智能体协作生成适配学生画像的学习资源，用 NetworkX 图算法规划个性化学习路径。评分权重：创新实用性35% + 功能实现45% + 文档10% + 演示10%。

## 开发状态

**后端**：5个Crew、14个Agent、6个Service、7组API端点（36路由），全部实现并导入通过。
**前端**：9个页面、路由鉴权、SSE流式对话、JWT登录注册，TypeScript编译通过。
**数据库**：SQLite（关系数据）+ ChromaDB（向量存储），零系统依赖，已验证运行。
**已验证 API**：注册(201) / 登录(200+JWT) / 知识搜索(200,3条结果) / 健康检查(200)。
**待完成**：讯飞星火 API 集成测试、前端 E2E 测试、文档/Demo。

## 关键约束

- **LLM 必须是讯飞星火**（赛题强制），通过 OpenAI 兼容接口 + LiteLLM 桥接接入 CrewAI。已验证通过：`validate_spark_crewai.py`
- **开发周期 ~12 周**，团队小型。不做微服务、不做分布式、不提前优化。
- **知识库课程是 JavaScript**（不是 AI / CS / 电子信息）
- **移动端和3D 等技术可以降级处理**，评委只关心功能的体现
- **Python 3.12 类型注解**：使用 `from collections.abc import Callable`，然后 `Callable | None`，**不要**用小写 `callable | None`（Python 3.12 不支持）

## 常用命令

```bash
# 后端
cd backend
pip install -r requirements.txt      # 安装依赖
PYTHONPATH=. alembic upgrade head    # 数据库迁移（SQLite，首次运行）
PYTHONPATH=. python -m app.rag.indexer  # 知识库索引到 ChromaDB（首次运行）
PYTHONPATH=. uvicorn app.main:app --reload  # 启动 (http://localhost:8000, ~10s启动)
pytest tests/ -v                     # 运行测试

# 前端
cd frontend
npm install                           # 安装依赖
npm run dev                           # 启动 Vite (http://localhost:5173)
npm run build                         # 生产构建（vue-tsc + vite）

# 一键环境配置（首次）
.\setup.ps1
```

## 数据库

**开发环境默认使用 SQLite + ChromaDB**，零系统依赖。生产部署可切换到 PostgreSQL + pgvector。

| 组件 | 开发（默认） | 生产（可选） |
|------|-------------|------------|
| 关系数据 | SQLite (`sqlite+aiosqlite`) | PostgreSQL (`postgresql+asyncpg`) |
| 向量存储 | ChromaDB（本地文件 `./chroma_data/`） | pgvector 扩展 |
| ID 类型 | `String(36)`（UUID字符串） | `UUID`（PostgreSQL native） |
| JSON 字段 | `JSON`（SQLAlchemy 通用类型） | `JSONB` |

**切换到 PostgreSQL**：在 `.env` 中设置 `DATABASE_URL=postgresql+asyncpg://...` 和 `DATABASE_URL_SYNC=postgresql://...`，改回 `backend/app/models/knowledge.py` 中的 Vector 列，用 Docker Compose 启动 `pgvector/pgvector:pg16`。

**ChromaDB 注意事项**：`chromadb.PersistentClient` 在 1.1.1 版本是函数而非类，类型注解需加 `from __future__ import annotations` 或使用 `typing.Optional`。

## 架构原则

**模块化单体，4 层分层**：`api/ → services/ → agents+rag/ → models/iflytek/streaming/`

核心依赖方向：上层可调下层，下层绝不引上层。Domain 层（agents/、rag/）不依赖 Infrastructure（models/、iflytek/）。

**7 个 Service 及其职责**：

| Service | 职责 | 调用关系 |
|---------|------|----------|
| `profile_service.py` | 画像对话编排 | 触发 ProfileCrew → 解析输出 → 更新画像 |
| `resource_service.py` | 资源生成编排 | RAG检索 → ResourceCrew → 审核-重试(≤2次) → 持久化 → SSE |
| `path_service.py` | 路径规划编排 | 调 graph_service 算图 → 触发 PathCrew → 组装路径 |
| `graph_service.py` | NetworkX 图算法 | 拓扑排序 / Dijkstra / PageRank / 断点检测 |
| `safety_service.py` | 内容安全 | 5层：RAG一致性 → 代码沙箱 → 审核 → 讯飞 → 溯源 |
| `tutoring_service.py` | 实时答疑编排 | RAG检索 → TutoringCrew → 画像联动更新 |
| `evaluation_service.py` | 学习评估 | 行为数据聚合 → EvaluationCrew → Dashboard统计 |

**数据设计原则**：查询用的字段提到表层（resource_type、difficulty、review_status），展示用的内容放在 JSON 字段（content、generation_context）。

**前端状态管理**：SSE 事件 → Pinia Store（单一状态树） → 组件响应式渲染。组件不直接监听 SSE。

**API 鉴权**：JWT token 存储在 localStorage，axios 拦截器自动附加 `Authorization: Bearer` 头，401 自动跳转 `/login`。路由守卫 `router.beforeEach` 拦截未登录访问。密码哈希使用 `bcrypt` 直接调用（不用 `passlib`，版本不兼容）。

## 多智能体系统核心

**5 个 Crew、14 个 Agent**：

| Crew | Process | Agent | 工具 |
|------|---------|-------|------|
| **ProfileCrew** | Sequential | ProfileInterviewer → ProfileAnalyzer | profile_tool |
| **ResourceCrew** | Hierarchical | ResourcePlanner(管理) → 8个专业生成Agent → ResourceReviewer | knowledge_tool, code_exec_tool, safety_tool, multimodal_tool, graph_tool |
| **PathCrew** | Sequential | PathDesigner → PathEvaluator | graph_tool, knowledge_tool |
| **TutoringCrew** | Sequential | TutorAgent → ExplanationGenerator | knowledge_tool, code_exec_tool, safety_tool |
| **EvaluationCrew** | Sequential | LearningEvaluator | knowledge_tool, graph_tool |

**Agent 间数据传递**用结构化 `ResourceTask` 对象（dataclass），不用字符串拼接。审核-反馈最多 2 次，失败有分级降级策略。

**6 个 Agent 工具**：

| 工具 | 文件 | 功能 |
|------|------|------|
| search_knowledge | `tools/knowledge_tool.py` | RAG知识库检索，工厂函数 `create_knowledge_tool(rag_context)` |
| execute_javascript | `tools/code_exec_tool.py` | Deno沙箱执行JS代码，10秒超时 |
| check_content_safety | `tools/safety_tool.py` | 敏感词+代码安全+质量检查 |
| query_knowledge_graph | `tools/graph_tool.py` | 知识图谱查询，工厂函数 `create_graph_tool(graph_service)` |
| format_animation_script | `tools/multimodal_tool.py` | 动画脚本/PPT格式化+TTS文本验证 |
| update_student_profile | `tools/profile_tool.py` | 画像维度更新（ProfileAnalyzer专用） |

**8 种资源类型**（R0-R8）：design_plan / course_doc / mind_map / exercise / code_case / ppt / project / reading / video_script

## API 端点地图

```
/api/v1/auth/            POST register, login              # JWT + bcrypt
/api/v1/conversations/   CRUD + SSE stream                 # 按类型路由 ProfileService/TutoringService
/api/v1/profiles/        GET, GET /dimensions, POST /refresh
/api/v1/resources/       POST /generate, GET 列表筛选, GET /{id}, SSE进度流
/api/v1/knowledge/       GET /tree, /graph, /search, /nodes, /nodes/{id}
/api/v1/learning-paths/  POST /generate, GET 列表, GET /active, GET /{id},
                         PATCH /{id}/nodes/{order}, POST /replan
/api/v1/evaluation/      POST /assess, GET /dashboard, GET /report
```

## 关键文件路径

| 文件 | 作用 |
|------|------|
| `validate_spark_crewai.py` | 星火+CrewAI兼容性验证（4步，已全部通过） |
| `setup.ps1` | Windows 一键环境配置脚本 |
| `.env` | API密钥 + HF镜像 + LiteLLM配置 |
| `docs/requirements.md` | 需求分析文档 |
| `docs/设计计划.md` | 设计计划（架构图/ER图/组件树/时序图） |
| `backend/app/config.py` | 所有配置（Pydantic Settings，默认 SQLite + ChromaDB） |
| `backend/app/database.py` | 数据库连接（SQLite WAL模式 + 外键约束，自动检测） |
| `backend/app/main.py` | FastAPI 入口（7个Service初始化 + 7组API挂载） |
| `backend/app/models/` | 9张表 ORM：student / profile / conversation+message / knowledge_node+relation / resource / learning_path+activity+exercise |
| `backend/app/agents/` | 5个Crew + 6个Tool（全部已实现） |
| `backend/app/services/` | 7个业务Service（全部已实现） |
| `backend/app/rag/` | RAG 管线：SentenceTransformer嵌入 → ChromaDB向量存储 → retriever → indexer |
| `backend/app/api/` | 7组API端点：auth / conversation / profile / resource / knowledge / learning / evaluation |
| `backend/app/streaming/` | EventBus（asyncio.Queue pub-sub）+ SSEManager |
| `backend/knowledge_base/` | JS 课程 10 章 Markdown + 练习题 JSON + 代码示例 |
| `backend/alembic/` | 数据库迁移（兼容 SQLite 和 PostgreSQL） |
| `frontend/src/stores/conversation.ts` | 对话状态管理（事件驱动 Pinia Store） |
| `frontend/src/composables/useSSE.ts` | SSE 流式消费（EventSource → Store） |
| `frontend/src/composables/useStreamingMarkdown.ts` | Markdown 流式渲染（50ms 防抖 + highlight.js） |
| `frontend/src/api/client.ts` | Axios 实例 + JWT 拦截器 + 7组 API 封装 |
| `frontend/src/router/index.ts` | 路由表 + beforeEach 鉴权守卫 |
| `frontend/src/pages/ConversationPage.vue` | 核心对话页（SSE流式 + Agent状态 + 多对话类型） |
| `frontend/src/pages/LoginPage.vue` | 登录/注册页（JWT + Naive UI Tabs） |
| `frontend/src/pages/DashboardPage.vue` | 仪表盘（evaluation API 真实数据） |

## 环境变量（.env）

```bash
SPARK_API_KEY=xxx               # 讯飞星火 API Key（必填）
SPARK_API_BASE=https://spark-api-open.xf-yun.com/v1
SPARK_MODEL=4.0Ultra
HF_ENDPOINT=https://hf-mirror.com           # HuggingFace 镜像（国内必需）
LITELLM_LOCAL_MODEL_COST_MAP=True           # 避免 LiteLLM 远程拉取超时
```

## 开发注意事项

- **不要过度抽象**：10 个 Agent 不需要 10 个 Factory。CrewAI 本身已是抽象层。
- **不假设外部 API 可靠**：每个外部调用都有超时+重试+降级三层保护。
- **测试分层**：确定性逻辑（图算法、数据变换）必测；LLM 输出只测格式，不测内容。
- **知识库内容优先**：Agent 生成前强制 RAG 检索，prompt 中注入检索片段，禁止自由发挥。
- **类型注解**：`step_callback` 用 `Callable | None`（从 `collections.abc` 导入 `Callable`），不用小写 `callable`。`from __future__ import annotations` 解决 ChromaDB 函数类型注解问题。
- **API 路由前缀**：所有 router 内部不加 `prefix=`，统一由 `api/router.py` 的 `include_router(..., prefix=...)` 管理，避免双重前缀。
- **对话类型路由**：`conversation.py` 的 `send_message` 根据 `conversation_type` 分发到 ProfileService / TutoringService。
- **ID 字段**：所有模型 ID 使用 `String(36)` + `default=lambda: str(uuid.uuid4())`，对外接口也使用字符串 UUID。
- **密码哈希**：直接使用 `bcrypt.hashpw` / `bcrypt.checkpw`，不要引入 `passlib`（与新版 bcrypt 不兼容）。
- **模型下载**：国内环境设置 `HF_ENDPOINT=https://hf-mirror.com`，否则 SentenceTransformer 无法下载。
- **LiteLLM**：设置 `LITELLM_LOCAL_MODEL_COST_MAP=True` 避免启动时远程拉取超时（~10秒卡顿）。
- **Git 状态**：本项目当前不在 Git 仓库中。初始化时 `.env` 不要提交，`.env.example` 可提交。

## Agent skills

### Issue tracker

Issues are tracked as local markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default triage labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context repo. `CLAUDE.md` at root is the primary context file. See `docs/agents/domain.md`.
