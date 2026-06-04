# 旅游助手 — 概要设计文档

## 1. 引言

### 1.1 编写目的

本文档基于《旅游助手需求文档》，对系统进行模块划分，明确各模块职责、对外接口及模块间的依赖关系，为后续详细设计与开发提供指导。

### 1.2 系统概述

旅游助手是一个面向国内旅游场景的 Web 应用，采用前后端分离架构（React + FastAPI），集成 LangChain 多 Agent 协作与 DeepSeek LLM，通过对话式交互为用户提供智能行程规划、景点推荐、路线规划、天气查询和预算管理等一站式旅游规划服务。

### 1.3 技术架构概览

| 层级 | 技术 |
|------|------|
| 前端 | React |
| 后端 | FastAPI (Python) |
| 数据库 | SQLite |
| Agent 框架 | LangChain (ReAct 模式) |
| LLM 服务 | DeepSeek |
| 外部服务 | 高德地图 API、天气 API、小红书爬取 |
| 通信协议 | REST API + SSE（流式输出） |

---

## 2. 模块划分

系统按职责划分为以下模块：

| 编号 | 模块 | 层级 | 简述 |
|------|------|------|------|
| M1 | 前端展示模块 | 前端 | 用户界面与交互 |
| M2 | 用户管理模块 | 后端 | 注册、登录、认证、个人信息 |
| M3 | 景点查询模块 | 后端 | 景点搜索、详情、地图数据 |
| M4 | 行程管理模块 | 后端 | 行程的 CRUD、导出 |
| M5 | Agent 编排模块 | 后端 | 多 Agent 调度与协作 |
| M6 | 规划 Agent | Agent 层 | 需求拆解、子任务调度、结果汇总 |
| M7 | 景点 Agent | Agent 层 | 景点搜索与筛选 |
| M8 | 路线 Agent | Agent 层 | 路线规划与交通方案 |
| M9 | 天气 Agent | Agent 层 | 天气查询与影响评估 |
| M10 | 预算 Agent | Agent 层 | 费用估算与预算控制 |
| M11 | 外部服务集成模块 | 后端 | 高德地图、天气、小红书等外部 API 的封装 |
| M12 | 数据访问模块 | 后端 | 数据库 ORM 与数据持久化 |

---

## 3. 模块职责与接口

### 3.1 M1 — 前端展示模块

**职责：** 提供用户交互界面，包括页面路由、组件渲染、状态管理，以及与后端 API 的通信。

**子模块：**

| 子模块 | 职责 |
|--------|------|
| 用户页面 | 注册、登录、个人信息表单 |
| 对话页面 | 与 LLM Agent 的对话交互界面，接收 SSE 流式响应并逐步渲染 |
| 景点页面 | 景点搜索列表、景点详情展示 |
| 地图组件 | 高德地图集成，景点标注、路线绘制 |
| 行程页面 | 行程列表、行程详情、行程导出 |
| 预算组件 | 费用明细展示、预算设置 |
| 天气组件 | 天气信息卡片展示 |

**对外接口（消费的后端 API）：**

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 用户注册 | POST | `/api/auth/register` | 创建新用户 |
| 用户登录 | POST | `/api/auth/login` | 获取认证 Token |
| 用户登出 | POST | `/api/auth/logout` | 销毁会话 |
| 获取个人信息 | GET | `/api/user/profile` | 查询当前用户信息 |
| 更新个人信息 | PUT | `/api/user/profile` | 修改用户信息 |
| 搜索景点 | GET | `/api/spots/search` | 按条件搜索景点 |
| 景点详情 | GET | `/api/spots/{id}` | 获取景点详细信息 |
| 发起对话 | POST | `/api/chat/session` | 创建对话会话 |
| 发送消息 | POST | `/api/chat/message` | 发送用户消息，通过 SSE 接收流式响应 |
| 获取对话历史 | GET | `/api/chat/session/{id}/history` | 获取对话历史记录 |
| 保存行程 | POST | `/api/trips` | 保存行程计划 |
| 获取行程列表 | GET | `/api/trips` | 获取用户的行程列表 |
| 获取行程详情 | GET | `/api/trips/{id}` | 获取行程详情 |
| 删除行程 | DELETE | `/api/trips/{id}` | 删除行程 |
| 导出行程 | GET | `/api/trips/{id}/export` | 导出行程为 PDF |
| 查询天气 | GET | `/api/weather` | 查询城市天气 |

---

### 3.2 M2 — 用户管理模块

**职责：** 处理用户注册、登录/登出、身份认证（JWT Token）和个人信息管理。

**对外接口：**

| 接口 | 方法 | 路径 | 输入 | 输出 | 认证 |
|------|------|------|------|------|------|
| 注册 | POST | `/api/auth/register` | `{username, password, email}` | `{user_id, username}` | 无 |
| 登录 | POST | `/api/auth/login` | `{username, password}` | `{access_token, token_type}` | 无 |
| 登出 | POST | `/api/auth/logout` | — | `{message}` | 需要 |
| 获取个人信息 | GET | `/api/user/profile` | — | `{user_id, username, email, created_at}` | 需要 |
| 更新个人信息 | PUT | `/api/user/profile` | `{username?, email?}` | `{user_id, username, email}` | 需要 |

**依赖模块：** M12（数据访问模块）

---

### 3.3 M3 — 景点查询模块

**职责：** 提供景点搜索、详情查询功能。数据来源包括本地数据库缓存和高德地图 POI 接口。

**对外接口：**

| 接口 | 方法 | 路径 | 输入 | 输出 | 认证 |
|------|------|------|------|------|------|
| 搜索景点 | GET | `/api/spots/search` | `{keyword?, city?, type?, page, size}` | `{total, items: [Spot]}` | 可选 |
| 景点详情 | GET | `/api/spots/{id}` | — | `{Spot}` | 可选 |

**Spot 数据结构：**

```
{
  id, name, city, location: {lng, lat},
  type_tags, description, images,
  rating, open_time, ticket_price,
  review_summary
}
```

**依赖模块：** M11（外部服务集成 — 高德 POI）、M12（数据访问模块）

---

### 3.4 M4 — 行程管理模块

**职责：** 管理用户的行程计划，支持保存、查询、删除和导出（PDF）操作。行程数据由 Agent 对话过程中生成，用户确认后保存。

**对外接口：**

| 接口 | 方法 | 路径 | 输入 | 输出 | 认证 |
|------|------|------|------|------|------|
| 保存行程 | POST | `/api/trips` | `{TripPlan}` | `{trip_id}` | 需要 |
| 行程列表 | GET | `/api/trips` | `{page, size}` | `{total, items: [TripSummary]}` | 需要 |
| 行程详情 | GET | `/api/trips/{id}` | — | `{TripPlan}` | 需要 |
| 删除行程 | DELETE | `/api/trips/{id}` | — | `{message}` | 需要 |
| 导出行程 | GET | `/api/trips/{id}/export` | `{format: "pdf"}` | 文件流 | 需要 |

**TripPlan 数据结构：**

```
{
  trip_id, user_id, title, destination,
  start_date, end_date,
  days: [
    {
      date, weather,
      activities: [
        {spot_name, time_slot, transport, notes}
      ]
    }
  ],
  budget: {total, breakdown: {transport, accommodation, tickets, food, other}},
  created_at, updated_at
}
```

**依赖模块：** M12（数据访问模块）

---

### 3.5 M5 — Agent 编排模块

**职责：** 作为后端 API 层与 Agent 层之间的桥梁。接收前端的对话请求，创建并管理对话会话，将用户消息分发给规划 Agent，并将 Agent 的流式响应通过 SSE 推送给前端。

**对外接口：**

| 接口 | 方法 | 路径 | 输入 | 输出 | 认证 |
|------|------|------|------|------|------|
| 创建会话 | POST | `/api/chat/session` | `{title?}` | `{session_id}` | 需要 |
| 发送消息 | POST | `/api/chat/message` | `{session_id, content}` | SSE 流式响应 | 需要 |
| 对话历史 | GET | `/api/chat/session/{id}/history` | — | `{messages: [Message]}` | 需要 |
| 会话列表 | GET | `/api/chat/sessions` | — | `{sessions: [SessionSummary]}` | 需要 |

**SSE 响应事件类型：**

| 事件类型 | 数据 | 说明 |
|----------|------|------|
| `token` | `{content}` | LLM 生成的文本 token |
| `tool_call` | `{tool, args}` | Agent 正在调用工具（可选，用于前端展示思考过程） |
| `tool_result` | `{tool, result_summary}` | 工具执行结果摘要 |
| `trip_plan` | `{TripPlan}` | 生成的结构化行程方案 |
| `done` | — | 响应结束 |
| `error` | `{message}` | 错误信息 |

**内部职责：**
- 维护对话上下文（LangChain Memory）
- 实例化规划 Agent 并传入对话历史
- 将 Agent 的 streaming 输出转换为 SSE 事件流

**依赖模块：** M6（规划 Agent）、M12（数据访问模块）

---

### 3.6 M6 — 规划 Agent（Planner）

**职责：** 系统的核心 Agent。接收用户的自然语言旅游需求，通过 ReAct 推理模式分析需求、拆解子任务，调度其他 Agent（作为 LangChain Tool）获取信息，最终汇总生成完整的行程方案。

**LangChain 实现方式：** 使用 LangChain 的 Agent 框架，将 M7–M10 四个子 Agent 包装为 Tool 注册到规划 Agent 上。

**可用 Tool（子 Agent）：**

| Tool 名称 | 对应模块 | 功能描述 |
|-----------|----------|----------|
| `find_spots` | M7 景点 Agent | 根据条件搜索和筛选景点 |
| `plan_route` | M8 路线 Agent | 根据景点列表规划游览路线 |
| `check_weather` | M9 天气 Agent | 查询目的地天气 |
| `estimate_budget` | M10 预算 Agent | 估算行程费用 |

**输入：** 用户自然语言消息 + 对话历史上下文

**输出：** 流式文本响应 + 结构化行程方案（TripPlan）

**依赖模块：** M7、M8、M9、M10，DeepSeek LLM 服务

---

### 3.7 M7 — 景点 Agent（Spot Finder）

**职责：** 根据规划 Agent 下发的搜索条件，调用高德 POI 搜索和小红书实时爬取工具获取景点信息，经筛选和排序后返回结构化景点数据。

**可用 Tool：**

| Tool 名称 | 对应模块 | 功能描述 |
|-----------|----------|----------|
| `amap_poi_search` | M11 | 调用高德 POI 搜索接口 |
| `xiaohongshu_search` | M11 | 实时爬取小红书攻略和评价数据 |
| `spot_db_search` | M12 | 查询本地景点数据库（缓存） |

**输入：** `{city, keyword?, type?, count?}`

**输出：** `[Spot]` 结构化景点列表

**依赖模块：** M11、M12，DeepSeek LLM 服务

---

### 3.8 M8 — 路线 Agent（Route Planner）

**职责：** 根据景点列表和用户偏好，调用高德路径规划 API 计算最优游览路线和交通方式，支持生成多条备选路线。

**可用 Tool：**

| Tool 名称 | 对应模块 | 功能描述 |
|-----------|----------|----------|
| `amap_route_plan` | M11 | 调用高德路径规划接口 |

**输入：** `{spots: [Spot], transport_preference?}`

**输出：** `[Route]`，每条 Route 包含 `{route_id, spots_order, segments: [{from, to, distance, duration, transport}], total_distance, total_duration}`

**依赖模块：** M11，DeepSeek LLM 服务

---

### 3.9 M9 — 天气 Agent（Weather Checker）

**职责：** 查询目的地城市在指定日期范围内的天气预报，评估天气对行程的影响，给出建议。

**可用 Tool：**

| Tool 名称 | 对应模块 | 功能描述 |
|-----------|----------|----------|
| `weather_query` | M11 | 调用天气预报接口 |

**输入：** `{city, start_date, end_date}`

**输出：** `{city, forecasts: [{date, temperature_range, condition, wind, rain_probability, suggestion}]}`

**依赖模块：** M11，DeepSeek LLM 服务

---

### 3.10 M10 — 预算 Agent（Budget Estimator）

**职责：** 根据行程中的景点、交通方式、天数等信息估算各项费用，结合用户预算约束进行调整建议。

**可用 Tool：**

| Tool 名称 | 对应模块 | 功能描述 |
|-----------|----------|----------|
| `budget_estimate` | M11 | 根据行程项目计算费用 |

**输入：** `{trip_days, spots: [Spot], routes: [Route], budget_limit?}`

**输出：** `{total, breakdown: {transport, accommodation, tickets, food, other}, over_budget: bool, suggestions?}`

**依赖模块：** M11，DeepSeek LLM 服务

---

### 3.11 M11 — 外部服务集成模块

**职责：** 封装所有外部第三方 API 的调用逻辑，对上层提供统一的 Python 函数接口，处理请求构造、响应解析、错误重试和限流控制。

**子模块与工具映射：**

| 子模块 | 工具名称 | 外部服务 | 功能 |
|--------|----------|----------|------|
| 高德 POI | `amap_poi_search` | 高德地图 POI 搜索 API | 关键词/分类搜索景点 |
| 高德路径规划 | `amap_route_plan` | 高德地图路径规划 API | 计算路线、距离、耗时 |
| 天气查询 | `weather_query` | 天气 API（高德/和风） | 查询未来多日天气预报 |
| 小红书爬取 | `xiaohongshu_search` | 小红书网站 | 实时爬取攻略和评价数据 |
| 费用估算 | `budget_estimate` | 本地计算 | 基于规则和数据的费用估算 |

**通用职责：**
- API Key 管理与安全存储
- 请求频率限制（防止超出 API 配额）
- 错误处理与重试机制
- 响应数据标准化

**依赖：** 外部第三方 API

---

### 3.12 M12 — 数据访问模块

**职责：** 封装 SQLite 数据库操作，对上层提供数据模型的 CRUD 接口。

**数据模型：**

| 模型 | 说明 | 所属表 |
|------|------|--------|
| User | 用户信息 | `users` |
| ChatSession | 对话会话 | `chat_sessions` |
| ChatMessage | 对话消息 | `chat_messages` |
| Trip | 行程计划 | `trips` |
| TripDay | 行程每日安排 | `trip_days` |
| TripActivity | 行程活动项 | `trip_activities` |
| SpotCache | 景点缓存 | `spot_cache` |

**对外接口：** 各模型的 CRUD 操作函数

**依赖：** SQLite 数据库

---

## 4. 模块关系图

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         M1 前端展示模块 (React)                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ 用户页面  │ │ 对话页面  │ │ 景点页面  │ │ 行程页面  │ │ 地图/天气/预算组件 │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────────┘ │
└──────────────────────────┬─────────────────────────────────────────────────┘
                           │ REST API + SSE
                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          FastAPI 后端                                        │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐   │
│  │ M2 用户管理   │  │ M3 景点查询   │  │ M4 行程管理   │  │ M5 Agent 编排   │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬─────────┘   │
│         │                 │                 │                  │              │
│         │                 │                 │                  │              │
│         ▼                 ▼                 ▼                  ▼              │
│  ┌───────────────────────────────────────────────────────────────────────┐    │
│  │                    M12 数据访问模块 (SQLite)                           │    │
│  └───────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
                                                    │
                                    M5 Agent 编排    │ 调用
                                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       LangChain Agent 层                                     │
│                                                                              │
│                    ┌──────────────────────┐                                   │
│                    │  M6 规划 Agent        │                                   │
│                    │  (Planner)           │                                   │
│                    └──────────┬───────────┘                                   │
│                               │ 作为 Tool 调用                                │
│              ┌────────────────┼────────────────┬────────────────┐             │
│              ▼                ▼                ▼                ▼             │
│     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │
│     │ M7 景点 Agent │ │ M8 路线 Agent │ │ M9 天气 Agent │ │ M10 预算Agent │      │
│     └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘      │
│            │                │                │                │               │
└────────────┼────────────────┼────────────────┼────────────────┼───────────────┘
             │                │                │                │
             ▼                ▼                ▼                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       M11 外部服务集成模块                                     │
│                                                                              │
│  ┌────────────────┐ ┌────────────────┐ ┌─────────────┐ ┌──────────────────┐  │
│  │ amap_poi_search │ │ amap_route_plan│ │weather_query│ │xiaohongshu_search│  │
│  └───────┬────────┘ └───────┬────────┘ └──────┬──────┘ └────────┬─────────┘  │
│          │                  │                 │                 │             │
│  ┌───────▼────────┐ ┌──────▼─────────┐ ┌─────▼──────┐ ┌───────▼──────────┐  │
│  │  高德地图 API   │ │  高德地图 API   │ │  天气 API   │ │   小红书网站      │  │
│  └────────────────┘ └────────────────┘ └────────────┘ └──────────────────┘  │
│                                                                              │
│  ┌────────────────┐                                                          │
│  │ budget_estimate │ ← 本地计算（无外部依赖）                                  │
│  └────────────────┘                                                          │
└──────────────────────────────────────────────────────────────────────────────┘

                      ┌──────────────────┐
                      │   DeepSeek LLM   │  ← 所有 Agent (M6-M10) 共同依赖
                      │   推理服务        │
                      └──────────────────┘
```

---

## 5. 模块依赖关系矩阵

下表展示模块间的依赖关系（行依赖列）：

| | M1 | M2 | M3 | M4 | M5 | M6 | M7 | M8 | M9 | M10 | M11 | M12 | DeepSeek |
|-----|----|----|----|----|----|----|----|----|----|----|-----|-----|----------|
| **M1** | — | ✓ | ✓ | ✓ | ✓ | | | | | | | | |
| **M2** | | — | | | | | | | | | | ✓ | |
| **M3** | | | — | | | | | | | | ✓ | ✓ | |
| **M4** | | | | — | | | | | | | | ✓ | |
| **M5** | | | | | — | ✓ | | | | | | ✓ | |
| **M6** | | | | | | — | ✓ | ✓ | ✓ | ✓ | | | ✓ |
| **M7** | | | | | | | — | | | | ✓ | ✓ | ✓ |
| **M8** | | | | | | | | — | | | ✓ | | ✓ |
| **M9** | | | | | | | | | — | | ✓ | | ✓ |
| **M10** | | | | | | | | | | — | ✓ | | ✓ |
| **M11** | | | | | | | | | | | — | | |
| **M12** | | | | | | | | | | | | — | |

---

## 6. 数据流

### 6.1 对话式行程规划 — 主数据流

```
用户 ──[自然语言消息]──► M1 前端
                          │
                    POST /api/chat/message (REST)
                          │
                          ▼
                    M5 Agent 编排 ──[加载对话历史]──► M12 数据库
                          │
                    [传入消息+上下文]
                          │
                          ▼
                    M6 规划 Agent
                          │
                  ReAct 推理循环
                          │
            ┌─────────────┼─────────────────────────────┐
            │ Thought: 需要搜索杭州景点                    │
            │ Action: 调用 find_spots Tool                │
            │             │                               │
            │             ▼                               │
            │       M7 景点 Agent                          │
            │             │                               │
            │     ┌───────┼───────┐                       │
            │     ▼       ▼       ▼                       │
            │  M11     M11      M12                       │
            │  高德POI  小红书    景点DB                     │
            │     │       │       │                       │
            │     └───────┼───────┘                       │
            │             │                               │
            │ Observation: 返回景点列表                     │
            │                                             │
            │ Thought: 需要查询天气                         │
            │ Action: 调用 check_weather Tool              │
            │             │                               │
            │             ▼                               │
            │       M9 天气 Agent ──► M11 天气API           │
            │             │                               │
            │ Observation: 返回天气数据                     │
            │                                             │
            │  ...（继续调用路线/预算 Agent）...              │
            │                                             │
            │ Thought: 信息充分，生成行程方案                 │
            │ Final Answer: 完整行程方案                    │
            └─────────────┼─────────────────────────────┘
                          │
                   [流式 token + 结构化行程]
                          │
                          ▼
                    M5 Agent 编排
                          │
                    SSE 事件流推送
                          │
                          ▼
                    M1 前端 ──[逐步渲染]──► 用户
```

### 6.2 景点搜索 — 数据流

```
用户 ──[搜索关键词]──► M1 前端
                        │
                  GET /api/spots/search
                        │
                        ▼
                  M3 景点查询模块
                        │
                 ┌──────┴──────┐
                 ▼             ▼
           M12 查本地缓存   M11 调高德POI
                 │             │
                 └──────┬──────┘
                        │ 合并去重
                        ▼
                  返回景点列表
                        │
                        ▼
                  M1 前端展示
```

### 6.3 行程保存与导出 — 数据流

```
用户 ──[确认保存行程]──► M1 前端
                          │
                    POST /api/trips
                          │
                          ▼
                    M4 行程管理模块
                          │
                          ▼
                    M12 持久化到 SQLite
                          │
                    返回 trip_id
                          │
                          ▼
                    M1 前端提示保存成功

用户 ──[导出行程]──► M1 前端
                      │
                GET /api/trips/{id}/export
                      │
                      ▼
                M4 行程管理模块
                      │
                M12 读取行程数据 → 生成 PDF
                      │
                      ▼
                返回 PDF 文件流
```

---

## 7. 数据库设计概要

### 7.1 ER 关系

```
User (1) ──── (N) ChatSession (1) ──── (N) ChatMessage
  │
  └── (1) ──── (N) Trip (1) ──── (N) TripDay (1) ──── (N) TripActivity

SpotCache（独立表，不与用户关联）
```

### 7.2 表结构概要

#### users 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | 用户 ID |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 用户名 |
| password_hash | VARCHAR(255) | NOT NULL | 密码哈希 |
| email | VARCHAR(100) | UNIQUE | 邮箱 |
| created_at | DATETIME | NOT NULL, DEFAULT NOW | 创建时间 |

#### chat_sessions 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | 会话 ID |
| user_id | INTEGER | FK → users.id, NOT NULL | 所属用户 |
| title | VARCHAR(200) | | 会话标题 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 最后更新时间 |

#### chat_messages 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | 消息 ID |
| session_id | INTEGER | FK → chat_sessions.id, NOT NULL | 所属会话 |
| role | VARCHAR(20) | NOT NULL | 消息角色（user / assistant / tool） |
| content | TEXT | NOT NULL | 消息内容 |
| created_at | DATETIME | NOT NULL | 创建时间 |

#### trips 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | 行程 ID |
| user_id | INTEGER | FK → users.id, NOT NULL | 所属用户 |
| title | VARCHAR(200) | NOT NULL | 行程标题 |
| destination | VARCHAR(100) | NOT NULL | 目的地 |
| start_date | DATE | | 开始日期 |
| end_date | DATE | | 结束日期 |
| budget_total | DECIMAL(10,2) | | 总预算 |
| budget_breakdown | JSON | | 预算明细 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 最后更新时间 |

#### trip_days 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | 日程 ID |
| trip_id | INTEGER | FK → trips.id, NOT NULL | 所属行程 |
| day_index | INTEGER | NOT NULL | 第几天（从 1 开始） |
| date | DATE | | 具体日期 |
| weather | VARCHAR(100) | | 天气信息 |

#### trip_activities 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | 活动 ID |
| trip_day_id | INTEGER | FK → trip_days.id, NOT NULL | 所属日程 |
| order_index | INTEGER | NOT NULL | 活动顺序 |
| spot_name | VARCHAR(200) | NOT NULL | 景点/地点名称 |
| time_slot | VARCHAR(50) | | 时间段（如 "09:00-11:30"） |
| transport | VARCHAR(50) | | 到达交通方式 |
| notes | TEXT | | 备注 |
| estimated_cost | DECIMAL(10,2) | | 预估费用 |

#### spot_cache 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | 缓存 ID |
| source | VARCHAR(20) | NOT NULL | 数据来源（amap / xiaohongshu） |
| source_id | VARCHAR(100) | | 外部数据源 ID |
| name | VARCHAR(200) | NOT NULL | 景点名称 |
| city | VARCHAR(50) | | 所在城市 |
| longitude | DECIMAL(10,6) | | 经度 |
| latitude | DECIMAL(10,6) | | 纬度 |
| type_tags | JSON | | 类型标签 |
| description | TEXT | | 简介 |
| images | JSON | | 图片 URL 列表 |
| rating | DECIMAL(3,1) | | 评分 |
| open_time | VARCHAR(200) | | 开放时间 |
| ticket_price | VARCHAR(100) | | 门票价格 |
| review_summary | TEXT | | 用户评价摘要 |
| cached_at | DATETIME | NOT NULL | 缓存时间 |

---

## 8. 关键设计决策

| 决策项 | 决策 | 理由 |
|--------|------|------|
| 前后端通信 | REST API + SSE | REST 满足常规 CRUD 需求；SSE 适合 LLM 流式输出的单向推送场景，比 WebSocket 更轻量 |
| Agent 间协作 | LangChain 内部调度（子 Agent 作为 Tool） | 避免跨进程通信开销，共享对话上下文，实现简单 |
| 小红书数据获取 | 用户查询时实时爬取 | 保证数据时效性，避免大量离线数据存储和更新维护 |
| 数据库 | SQLite | 个人项目无需独立数据库服务，SQLite 零配置、轻量 |
| 认证方式 | JWT Token | 无状态认证，前后端分离架构的标准做法 |
| 景点数据缓存 | 本地 SQLite spot_cache 表 | 减少重复外部 API 调用，节省配额 |
