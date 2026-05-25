# 个性化学习多智能体系统

第十五届中国软件杯大赛 A 组赛题 —— 基于大模型的个性化资源生成与学习多智能体系统。

为 JavaScript 课程构建个性化学习平台，通过 **CrewAI 多智能体协作**生成适配学生画像的学习资源，用 **NetworkX 图算法**规划个性化学习路径。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python 3.12 / FastAPI |
| 多智能体 | CrewAI + 讯飞星火 4.0 Ultra |
| 数据库 | SQLite + ChromaDB（向量存储） |
| 图分析 | NetworkX |
| 前端 | Vue 3 + TypeScript + Vite + Pinia + Naive UI |
| RAG | SentenceTransformer + ChromaDB |

## 核心功能

- **画像评估** — AI 面试官对话式了解学生 JS 水平，6 维度画像建模
- **个性化学习路径** — Dijkstra + PageRank + 拓扑排序，动态规划最优学习顺序
- **智能资源生成** — 8 种资源类型（教案/思维导图/练习题/代码案例/PPT/项目/阅读/视频脚本）
- **实时答疑辅导** — 基于 RAG 知识库检索的精准回答
- **学习评估仪表盘** — 行为数据聚合 + 进度可视化
- **知识图谱** — 85 个 JS 知识点及其依赖关系可视化

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- Deno（代码沙箱执行）

### 一键配置（Windows）

```bash
.\setup.ps1
```

### 手动配置

**后端：**
```bash
cd backend
pip install -r requirements.txt
PYTHONPATH=. alembic upgrade head      # 数据库迁移
PYTHONPATH=. python -m app.rag.indexer # 知识库索引
PYTHONPATH=. uvicorn app.main:app --reload  # 启动 (http://localhost:8000)
```

**前端：**
```bash
cd frontend
npm install
npm run dev   # 启动 (http://localhost:5173)
```

### 环境变量

复制 `.env.example` 为 `.env`，填入讯飞星火 API Key：

```bash
SPARK_API_KEY=你的API密钥
SPARK_API_BASE=https://spark-api-open.xf-yun.com/v1
SPARK_MODEL=4.0Ultra
HF_ENDPOINT=https://hf-mirror.com
```

## 项目结构

```
├── backend/
│   ├── app/
│   │   ├── agents/      # 5个Crew + 6个Tool（多智能体核心）
│   │   ├── api/         # 7组API端点（36个路由）
│   │   ├── services/    # 7个业务服务
│   │   ├── models/      # 8张数据表 ORM
│   │   ├── rag/         # RAG管线（embedding + 检索）
│   │   ├── streaming/   # SSE流式事件推送
│   │   ├── schemas/     # Pydantic数据校验
│   │   └── iflytek/     # 讯飞星火LLM适配
│   └── knowledge_base/  # JS课程10章知识库
├── frontend/
│   └── src/
│       ├── pages/       # 11个页面
│       ├── components/  # 8个组件
│       ├── stores/      # Pinia状态管理
│       └── api/         # Axios + SSE客户端
└── docs/                # 需求文档 + 设计计划
```

## 智能体系统

| Crew | 流程 | Agent |
|------|------|-------|
| ProfileCrew | Sequential | ProfileInterviewer → ProfileAnalyzer |
| ResourceCrew | Hierarchical | ResourcePlanner(管理) → 8个生成Agent → ResourceReviewer |
| PathCrew | Sequential | PathDesigner → PathEvaluator |
| TutoringCrew | Sequential | TutorAgent → ExplanationGenerator |
| EvaluationCrew | Sequential | LearningEvaluator |

## License

MIT
