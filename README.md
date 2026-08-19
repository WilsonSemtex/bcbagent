# 📐 板插板校核智能体

基于 SBAGENT（FastAPI + 自定义单页前端）改造的单智能体网页应用：**登录页与原版一致，登录后只有一个「板插板校核智能体」**，其余聊天逻辑保留。

## 功能

- 🔐 用户名/密码登录（登录页与原版一致）
- 📐 单一智能体「板插板校核智能体」：用户上传板材 2D 图片，智能体自动分析图片内容，识别板插板结构的设计缺陷（尺寸配合、干涉、结构强度、装配性等）并输出缺陷分析结论与改进建议
- 💬 多轮对话（流式输出、会话记忆、历史聊天列表）
- 📚 文档知识库（上传 PDF/TXT/DOCX 等，RAG 检索增强回答）
- 🧠 模型：仅 DeepSeek **deepseek-v4-flash**（DeepSeek 官方 API）+ 图片分析使用视觉模型（glm-4.6v-flash）

## 快速开始（本地离线测试）

### 1. 环境要求

- Python 3.11+
- 可访问外网（调用 DeepSeek API）

### 2. 安装依赖

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

### 3. 配置环境变量

`.env` 已内置配置（含 DeepSeek 官方 API Key）。如未提供或需更换：

```bash
cp .env.example .env
```

关键配置项：

```env
LLM_API_KEY=sk-你的DeepSeek官方Key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-v4-flash
DEEPSEEK_API_KEY=sk-你的DeepSeek官方Key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
```

> ⚠️ `.env` 已加入 `.gitignore`，密钥不会提交到 GitHub。若 DeepSeek 官方 API 的模型名与此不同，只需修改 `LLM_MODEL`。

### 4. 启动

```bash
python app/main.py
```

访问：

- 🖥️ 网页界面: http://localhost:8000
- 📖 API 文档: http://localhost:8000/docs
- ❤️ 健康检查: http://localhost:8000/health

### 5. 登录账号

| 用户名 | 密码 | 角色 |
|---|---|---|
| **administrator** | **admin12345** | 管理员 |
| **hustroboconadmin** | **admin123** | 管理员（知识库全量管理） |
| **rc01** | **rc12345** | 普通用户 |
| jiangxy | 123456abc | 普通用户 |

> 账号在首次启动时自动创建，可在 `data/users/users.json` 中管理。

## API 接口

| 接口 | 说明 |
|---|---|
| `POST /api/v1/auth/login` | 登录，返回 JWT |
| `GET /api/v1/agents` | 获取当前用户的智能体列表（唯一：板插板校核智能体） |
| `GET /api/v1/models` | 获取可用模型（仅 deepseek-v4-flash） |
| `POST /api/v1/chat` | 与智能体对话（流式） |
| `POST /api/v1/upload` | 上传文档到知识库 |

## 部署到服务器

### 方式一：直接运行（Linux 服务器）

```bash
pip install -r requirements.txt
# 配置 .env（或环境变量）
python app/main.py   # 生产可用 nohup / systemd 守护
```

### 方式二：Docker

```bash
docker build -t failure-mode-analysis-agent .
docker run -d --name failure-mode-analysis-agent -p 8000:8000 \
  -e LLM_API_KEY=sk-xxx \
  -e DEEPSEEK_API_KEY=sk-xxx \
  failure-mode-analysis-agent
```

## 推送到 GitHub

```bash
git init
git add .
git commit -m "板插板校核智能体：单智能体 + deepseek-v4-flash"
git remote add origin https://github.com/<你的用户名>/failure-analysis-agent.git
git push -u origin main
```

> 注意：`.env` 与 `data/` 下的运行数据已被 `.gitignore` 排除，服务器部署时需单独配置环境变量。

## 项目结构

```
├── app/
│   ├── main.py              # FastAPI 入口（静态前端 + API）
│   ├── config.py            # 配置（模型列表、环境变量）
│   ├── api/routes.py        # REST API（登录/聊天/智能体/模型/知识库）
│   ├── agent/               # Agent 核心（LangGraph ReAct）、存储、提示词
│   ├── rag/document.py      # RAG 文档处理（加载/分块/向量化/检索）
│   ├── auth/                # 登录认证（账号、JWT、权限）
│   ├── memory/manager.py    # 会话记忆管理
│   ├── static/              # 前端（index.html 登录页、app.js、样式）
│   └── data/agents/         # 智能体种子配置（按账号）
├── .env                     # 环境变量（含 API Key，不入库）
└── requirements.txt         # Python 依赖
```

## 版本说明

- 智能体：由 7 个工作区 + 71 个子智能体精简为单一「板插板校核智能体」（`failure-mode-analysis-agent-sub-01`）
- 模型：仅保留 `deepseek-v4-flash`（DeepSeek 官方 API，`https://api.deepseek.com/v1`）
- 登录：管理员账号由 `admin/admin123` 调整为 `administrator/admin12345`
