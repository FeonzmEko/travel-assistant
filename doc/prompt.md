# Travel Assistant — Vibe Coding Master Prompt

## 角色定义

你是一个自动化软件开发主 Agent。你的任务是从零实现"旅游助手"项目的完整后端和前端代码。你将按照模块依赖顺序逐一实现每个模块，为每个模块生成子 Agent 任务。整个过程不会有人工参与。

---

## 项目概述

旅游助手是一个面向国内旅游场景的 Web 应用，采用前后端分离架构（React + FastAPI），集成 LangChain 多 Agent 协作与 DeepSeek LLM，通过对话式交互提供智能行程规划、景点推荐、路线规划、天气查询和预算管理等一站式旅游规划服务。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.12+) |
| 前端框架 | React + TypeScript + Vite |
| 数据库 | SQLite + SQLAlchemy |
| Agent 框架 | LangChain (ReAct 模式) |
| LLM 服务 | DeepSeek (OpenAI 兼容接口) |
| 外部 API | 高德地图 API、天气 API |
| 包管理 | uv (后端), npm (前端) |
| 代码质量 | pytest + mypy + ruff (后端), ESLint + TypeScript (前端) |

---

## 项目目录结构

```
travel-assistant/
├── pyproject.toml              # Python 项目配置 (uv)
├── .env                        # 环境变量 (API Keys, 不入版本控制)
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置管理 (读取 .env)
│   ├── database.py             # SQLAlchemy 引擎与会话
│   ├── models/                 # SQLAlchemy ORM 模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── chat.py
│   │   ├── trip.py
│   │   └── spot_cache.py
│   ├── schemas/                # Pydantic 数据模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── chat.py
│   │   ├── trip.py
│   │   └── spot.py
│   ├── crud/                   # 数据库 CRUD 操作
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── chat.py
│   │   ├── trip.py
│   │   └── spot_cache.py
│   ├── api/                    # FastAPI 路由
│   │   ├── __init__.py
│   │   ├── auth.py             # 认证路由
│   │   ├── user.py             # 用户信息路由
│   │   ├── spots.py            # 景点查询路由
│   │   ├── trips.py            # 行程管理路由
│   │   └── chat.py             # 对话/Agent 编排路由
│   ├── services/               # 外部服务集成
│   │   ├── __init__.py
│   │   ├── amap.py             # 高德地图 API 封装
│   │   ├── weather.py          # 天气 API 封装
│   │   └── budget.py           # 费用估算逻辑
│   ├── agents/                 # LangChain Agent
│   │   ├── __init__.py
│   │   ├── planner.py          # M6 规划 Agent
│   │   ├── spot_finder.py      # M7 景点 Agent
│   │   ├── route_planner.py    # M8 路线 Agent
│   │   ├── weather_checker.py  # M9 天气 Agent
│   │   └── budget_estimator.py # M10 预算 Agent
│   └── utils/
│       ├── __init__.py
│       ├── security.py         # 密码哈希 + JWT
│       └── rate_limiter.py     # API 频率限制
├── tests/                      # pytest 单元测试
│   ├── __init__.py
│   ├── conftest.py             # 公共 fixtures
│   ├── test_crud/
│   ├── test_api/
│   ├── test_services/
│   └── test_agents/
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    └── src/
        ├── App.tsx
        ├── main.tsx
        ├── api/                # API 调用封装
        ├── pages/              # 页面组件
        ├── components/         # 通用组件
        ├── hooks/              # 自定义 Hooks
        └── store/              # 状态管理
```

---

## 环境变量 (.env)

```env
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
AMAP_API_KEY=xxx
WEATHER_API_KEY=xxx
JWT_SECRET_KEY=your-secret-key
JWT_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite:///./travel_assistant.db
```

---

## 质量要求（所有模块必须遵守）

### Python 后端

1. **pytest 单元测试**：每个模块必须有完整的单元测试覆盖，包括正常路径和边界情况
2. **mypy 类型检查**：所有代码必须通过 `mypy --strict` 检查，函数签名必须有完整类型注解
3. **ruff 格式化与 lint**：所有代码必须通过 `ruff check` 和 `ruff format --check`
4. **测试中的外部依赖**：所有外部 API 调用（高德、天气、DeepSeek）在单元测试中必须使用 Mock/Fixture，不依赖真实 API Key
5. **异步代码**：FastAPI 路由和外部 API 调用使用 `async/await`

### React 前端

1. **TypeScript 严格模式**：`tsconfig.json` 中启用 `strict: true`
2. **ESLint 检查**：所有代码必须通过 ESLint 检查
3. **组件测试**：核心页面组件需有 Vitest + React Testing Library 测试

### 通用

- 不写多余注释，代码自文档化
- 每个模块实现完成后立即运行测试并确认通过
- 如果测试失败，立即修复后再继续下一个模块

---

## 模块依赖与开发顺序

```
M12 → M2 → M11 → M3 → M7/M8/M9/M10（可并行） → M6 → M5 → M4 → M1
```

---

## 模块详细规格

### M12 — 数据访问模块

**职责：** 封装 SQLite + SQLAlchemy 操作，提供 ORM 模型与 CRUD 接口。

**实现要求：**

1. 初始化 FastAPI 项目骨架，配置 `pyproject.toml` 依赖（fastapi, uvicorn, sqlalchemy, pydantic, httpx, python-jose, passlib, langchain, langchain-openai, sse-starlette, reportlab, python-dotenv）
2. 配置 SQLAlchemy 异步引擎连接 SQLite
3. 定义 ORM 模型：
   - `User`: id, username, password_hash, email, created_at
   - `ChatSession`: id, user_id(FK), title, created_at, updated_at
   - `ChatMessage`: id, session_id(FK), role, content, created_at
   - `Trip`: id, user_id(FK), title, destination, start_date, end_date, budget_total, budget_breakdown(JSON), created_at, updated_at
   - `TripDay`: id, trip_id(FK), day_index, date, weather
   - `TripActivity`: id, trip_day_id(FK), order_index, spot_name, time_slot, transport, notes, estimated_cost
   - `SpotCache`: id, source, source_id, name, city, longitude, latitude, type_tags(JSON), description, images(JSON), rating, open_time, ticket_price, review_summary, cached_at
4. 编写 Pydantic Schema（Create/Update/Out 三套）
5. 实现 CRUD 函数（async）
6. 编写 `init_db.py` 脚本创建所有表

**测试要求：**
- 使用内存 SQLite (`sqlite:///:memory:`) 作为测试数据库
- 测试每个 CRUD 函数的创建、查询、更新、删除
- 测试外键级联关系

---

### M2 — 用户管理模块

**职责：** 用户注册、登录/登出、JWT 认证、个人信息管理。

**API 接口：**
- `POST /api/auth/register` → `{username, password, email}` → `{user_id, username}`
- `POST /api/auth/login` → `{username, password}` → `{access_token, token_type}`
- `POST /api/auth/logout` (需认证) → `{message}`
- `GET /api/user/profile` (需认证) → `{user_id, username, email, created_at}`
- `PUT /api/user/profile` (需认证) → `{username?, email?}` → `{user_id, username, email}`

**实现要求：**
1. `utils/security.py`：bcrypt 密码哈希/验证、JWT 生成/验证
2. `get_current_user` FastAPI 依赖：从 Authorization header 解析 Token
3. 注册时校验用户名唯一性、邮箱格式、密码长度 ≥ 6
4. 登录失败返回 401，用户名/邮箱重复返回 409

**测试要求：**
- 测试注册成功/重复用户名/无效邮箱
- 测试登录成功/错误密码/不存在用户
- 测试 Token 认证流程
- 测试个人信息获取与更新

---

### M11 — 外部服务集成模块

**职责：** 封装高德地图、天气 API、费用估算的调用逻辑。

**注意：小红书爬虫功能已移除，不实现 `xiaohongshu_search`。**

**实现要求：**

1. `services/amap.py`:
   - `amap_poi_search(keyword, city, type?, page?, size?)` → `list[Spot]`
   - `amap_route_plan(origin, destination, waypoints?, strategy?)` → `Route`
   - 使用 httpx AsyncClient
   - 实现请求频率限制

2. `services/weather.py`:
   - `weather_query(city, date_range?)` → 天气预报列表
   - 使用高德天气 API 或和风天气 API

3. `services/budget.py`:
   - `budget_estimate(trip_days, spots, transport_mode?)` → `{total, breakdown}`
   - 基于规则的本地计算（住宿 300/晚, 餐饮 150/天, 市内交通 50/天, 门票取景点 ticket_price）

**测试要求：**
- 使用 `httpx` MockTransport 或 `respx` 库 mock HTTP 请求
- 测试正常响应解析、API 错误处理、超时重试
- 测试 budget_estimate 的计算逻辑

---

### M3 — 景点查询模块

**职责：** 提供景点搜索和详情查询 API。

**API 接口：**
- `GET /api/spots/search` → `{keyword?, city?, type?, page, size}` → `{total, items: [Spot]}`
- `GET /api/spots/{id}` → `Spot`

**实现要求：**
1. 先查本地 SpotCache，再调高德 POI，合并去重
2. 新获取的景点数据写入缓存
3. 缓存过期策略（cached_at 超过 7 天重新获取）

**测试要求：**
- Mock 外部 API，测试缓存命中/未命中两种路径
- 测试分页和筛选逻辑

---

### M7 — 景点 Agent

**职责：** LangChain ReAct Agent，搜索和筛选景点。

**可用 Tool：** `amap_poi_search`, `spot_db_search`（小红书已移除）

**输入：** `{city, keyword?, type?, count?}`
**输出：** `list[Spot]` 结构化景点列表

**实现要求：**
1. 用 `@tool` 装饰器注册 Tool，定义 Pydantic 入参 Schema
2. 编写 System Prompt（景点搜索专家角色）
3. 使用 `create_react_agent` 构建
4. 封装为 `find_spots(input)` 函数供规划 Agent 调用

**测试要求：**
- Mock LLM 响应，验证 Tool 调度逻辑
- 测试输入输出 Schema 正确性

---

### M8 — 路线 Agent

**职责：** LangChain ReAct Agent，规划游览路线。

**可用 Tool：** `amap_route_plan`

**输入：** `{spots: list[Spot], transport_preference?}`
**输出：** `list[Route]`（含路线段、距离、耗时）

**实现要求：**
1. 用 `@tool` 注册 `amap_route_plan`
2. 编写 System Prompt（路线规划专家）
3. 封装为 `plan_route(input)` 函数

**测试要求：**
- Mock LLM 和高德 API，验证路线计算逻辑

---

### M9 — 天气 Agent

**职责：** LangChain ReAct Agent，查询天气并评估影响。

**可用 Tool：** `weather_query`

**输入：** `{city, start_date, end_date}`
**输出：** 天气预报 + 影响评估 + 建议

**实现要求：**
1. 用 `@tool` 注册 `weather_query`
2. 编写 System Prompt（天气分析专家）
3. 封装为 `check_weather(input)` 函数

**测试要求：**
- Mock LLM 和天气 API，验证天气数据解析

---

### M10 — 预算 Agent

**职责：** LangChain ReAct Agent，估算行程费用。

**可用 Tool：** `budget_estimate`

**输入：** `{trip_days, spots, routes, budget_limit?}`
**输出：** `{total, breakdown, over_budget, suggestions?}`

**实现要求：**
1. 用 `@tool` 注册 `budget_estimate`
2. 编写 System Prompt（预算分析专家）
3. 封装为 `estimate_budget(input)` 函数

**测试要求：**
- Mock LLM，验证预算计算和超预算提示

---

### M6 — 规划 Agent（核心）

**职责：** 接收用户旅游需求，ReAct 推理拆解任务，调度 M7-M10 子 Agent，汇总生成行程方案。

**可用 Tool：** `find_spots`, `plan_route`, `check_weather`, `estimate_budget`

**实现要求：**
1. 编写详细的 System Prompt：
   - 角色：专业旅游规划师
   - 指引何时调用各 Tool
   - 输出格式要求（自然语言 + 结构化 TripPlan JSON）
2. 使用 LangChain `create_react_agent` + `AgentExecutor`
3. 配置 max_iterations 限制（防止无限循环）
4. 实现 streaming 输出
5. 实现从 Agent 输出中提取 TripPlan JSON 的解析逻辑（带降级方案）

**测试要求：**
- Mock 所有子 Agent Tool，验证调度逻辑
- 测试 TripPlan JSON 提取解析
- 测试 streaming 输出

---

### M5 — Agent 编排模块

**职责：** API 层与 Agent 层的桥梁，管理对话会话，SSE 流式推送。

**API 接口：**
- `POST /api/chat/session` (需认证) → `{session_id}`
- `GET /api/chat/sessions` (需认证) → `{sessions: [SessionSummary]}`
- `GET /api/chat/session/{id}/history` (需认证) → `{messages: [Message]}`
- `POST /api/chat/message` (需认证) → SSE 流式响应

**SSE 事件类型：** `token`, `tool_call`, `tool_result`, `trip_plan`, `done`, `error`

**实现要求：**
1. 使用 `sse-starlette` 实现 SSE
2. 保存用户消息到数据库
3. 加载对话历史构建 LangChain Memory
4. 调用规划 Agent，将 streaming 输出转为 SSE 事件
5. 保存 Assistant 响应到数据库
6. 实现超时处理和错误恢复

**测试要求：**
- Mock Agent，测试 SSE 事件流格式
- 测试会话 CRUD
- 测试对话历史加载

---

### M4 — 行程管理模块

**职责：** 行程 CRUD 和 PDF 导出。

**API 接口：**
- `POST /api/trips` (需认证) → `{trip_id}`
- `GET /api/trips` (需认证) → `{total, items: [TripSummary]}`
- `GET /api/trips/{id}` (需认证) → `TripPlan`
- `DELETE /api/trips/{id}` (需认证) → `{message}`
- `GET /api/trips/{id}/export` (需认证) → PDF 文件流

**实现要求：**
1. 级联创建 Trip → TripDay → TripActivity
2. 验证行程所属用户（防越权）
3. 使用 reportlab 生成 PDF
4. PDF 内容包含行程标题、目的地、每日安排、预算摘要

**测试要求：**
- 测试 CRUD 全流程
- 测试权限校验（用户只能操作自己的行程）
- 测试 PDF 生成（验证返回的是有效 PDF 文件）

---

### M1 — 前端展示模块

**职责：** React + TypeScript 前端，提供完整用户界面。

**实现要求：**

1. **项目初始化：** Vite + React + TypeScript, 安装 Ant Design, react-router-dom, axios
2. **全局布局：** 导航栏 + 侧边栏 + 内容区，路由守卫
3. **页面：**
   - 注册/登录页
   - 对话页（核心）：会话列表侧边栏 + 消息区域 + SSE 流式渲染 + Agent 思考过程展示
   - 景点搜索页 + 详情页
   - 行程列表页 + 详情页 + PDF 导出
   - 个人中心页
4. **地图组件：** 高德地图 JS SDK，景点标注 + 路线绘制
5. **API 封装：** axios 拦截器自动携带 Token，封装各模块 API 调用
6. **SSE 客户端：** 处理 EventSource 流式响应，渲染 token/tool_call/trip_plan 事件

**测试要求：**
- TypeScript 严格模式编译通过
- ESLint 检查通过
- 核心页面组件有 Vitest 测试

---

## 执行协议

### 主 Agent 职责

1. 按依赖顺序逐一（或可并行时并行）为每个模块生成子 Agent 任务
2. 每个子 Agent 完成后，验证：
   - 所有 pytest 测试通过
   - mypy --strict 通过
   - ruff check 通过
   - ruff format --check 通过
3. 如果验证失败，指示子 Agent 修复后重新验证
4. 当前模块通过验证后再启动下一个模块
5. 所有模块完成后，运行全量测试套件确认集成无误

### 子 Agent 任务模板

每个子 Agent 接收以下信息：
- 模块编号与名称
- 详细实现规格（从本文档对应模块章节摘取）
- 前置模块的代码位置（已实现的模块路径）
- 质量要求清单

每个子 Agent 必须：
1. 阅读前置模块代码了解接口
2. 实现模块代码
3. 编写完整单元测试
4. 运行并确认所有检查通过：
   ```bash
   uv run pytest tests/test_<module>/ -v
   uv run mypy backend/<module_path> --strict
   uv run ruff check backend/<module_path>
   uv run ruff format --check backend/<module_path>
   ```
5. 如有失败，修复后重新运行直到全部通过

### 验证命令

```bash
# 后端全量检查
uv run pytest tests/ -v --tb=short
uv run mypy backend/ --strict
uv run ruff check .
uv run ruff format --check .

# 前端检查
cd frontend && npm run type-check && npm run lint && npm run test
```

---

## 约束与注意事项

1. **不实现小红书爬虫**：`xiaohongshu_search` 功能已从需求中移除
2. **外部 API Mock**：单元测试中所有外部 API 调用必须 Mock，不依赖真实 Key
3. **环境变量**：通过 `.env` 文件提供 API Key，代码使用 `python-dotenv` 或 Pydantic Settings 读取
4. **数据库**：使用 SQLite，测试使用内存数据库
5. **LLM 调用**：Agent 测试中 Mock DeepSeek 响应，不产生真实 API 费用
6. **错误处理**：所有 API 接口需有适当的 HTTP 错误码和错误消息
7. **异步优先**：FastAPI 路由和外部服务调用全部使用 async/await
