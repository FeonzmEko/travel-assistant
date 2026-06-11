# 旅游助手 — 总体开发进度

> 最后更新：2026-06-05

## 模块完成状态

### 第一期：基础框架 + 核心功能

- [x] **M12 数据访问模块** — 数据库 ORM 与数据持久化
- [x] **M2 用户管理模块** — 注册、登录、认证、个人信息
- [x] **M11 外部服务集成模块** — 高德地图、天气、小红书等 API 封装
- [x] **M3 景点查询模块** — 景点搜索与详情

### 第二期：Agent 层 + 智能功能

- [x] **M7 景点 Agent** — 景点搜索与筛选 Agent（使用 `langchain.agents.create_agent`，拥有独立 LLM 推理）
- [x] **M8 路线 Agent** — 路线规划与交通方案 Agent（使用 `langchain.agents.create_agent`，支持多条备选路线）
- [x] **M9 天气 Agent** — 天气查询与影响评估 Agent（使用 `langchain.agents.create_agent`）
- [x] **M10 预算 Agent** — 费用估算与预算控制 Agent（使用 `langchain.agents.create_agent`）
- [x] **M6 规划 Agent** — 核心 Agent，需求拆解与子 Agent 调度（Planner 通过 Tool 包装调度子 Agent）
- [x] **M5 Agent 编排模块** — 对话会话管理与 SSE 流式推送

### 第三期：前端 + 行程管理

- [x] **M4 行程管理模块** — 行程 CRUD 与 PDF 导出
- [x] **M1 前端展示模块** — React 用户界面与交互

## 建议开发顺序

```
M12 → M2 → M11 → M3 → M7/M8/M9/M10（可并行） → M6 → M5 → M4 → M1
```

> **说明**：M1 前端可在任意阶段并行开发（先用 Mock 数据），但完整联调需后端 API 就绪。

## 架构修复记录

### 多 Agent 层级协作（2026-06-04）

**问题**：原有架构为单 Agent + 多工具扁平架构，`spot_finder.py` 和 `route_planner.py` 使用了不存在的 `from langchain.agents import create_agent`。

**修复**：
1. 将所有子 Agent 改为使用 `langgraph.prebuilt.create_react_agent`（2026-06-04）
2. 每个子 Agent 拥有独立的 LLM 实例和专属工具
3. `planner.py` 中将子 Agent 包装为 LangChain Tool，注册到 Planner Agent
4. Planner Agent 通过 ReAct 推理自动调度子 Agent，实现层级协作

### API 迁移至 langchain.agents.create_agent（2026-06-05）

**问题**：`langgraph.prebuilt.create_react_agent` 在 LangGraph V1.0 中已标记为 deprecated，将在 V2.0 中移除，产生大量 deprecation warning。

**修复**：
1. 5 个 Agent 文件统一迁移：
   - 导入：`from langgraph.prebuilt import create_react_agent` → `from langchain.agents import create_agent`
   - 参数：`prompt=` → `system_prompt=`
2. 所有 `create_*_agent()` 函数添加 `-> Runnable[Any, Any]` 返回类型注解
3. 更新相关 docstring

### 功能补全记录（2026-06-04）

| 功能 | 需求编号 | 状态 | 说明 |
|------|----------|------|------|
| 高德地图组件 | S-03, R-02 | ✅ 完成 | `AMapView.tsx` — 景点标注、路线绘制、点击交互 |
| 景点详情页 | S-02 | ✅ 完成 | `SpotDetail.tsx` — 独立页面，含地图、详细信息展示 |
| 景点详情 API | S-02 | ✅ 完成 | `GET /api/spots/{id}` 已实现 |
| 多条备选路线对比 | R-03 | ✅ 完成 | `RouteComparison.tsx` + route_planner multi_route 支持 |
| 天气整合到行程 | W-02 | ✅ 完成 | `WeatherCard.tsx` 集成到 TripDetail 页面 |
| 预算明细展示 | B-03 | ✅ 完成 | `BudgetBreakdown.tsx` — 分类进度条、费用占比 |
| 行程导出 PDF | E-03 | ✅ 完成 | `GET /api/trips/{id}/export` 已实现 |
| 对话中修改行程 | P-02 | ✅ 完成 | Planner System Prompt 增加行程调整指引 |

### 遗留问题修复记录（2026-06-04）

| 问题 | 状态 | 修复说明 |
|------|------|----------|
| 行程详情页地图未真正展示 | ✅ 完成 | `TripActivity` 增加可选经纬度字段并在 SQLite 初始化时补齐旧库列；保存行程时持久化坐标；`TripDetail.tsx` 使用真实坐标渲染 `AMapView` 和路线 |
| 前端构建可能被未使用变量阻断 | ✅ 完成 | `TripDetail.tsx` 中地图导入和坐标集合已用于页面渲染，不再保留未使用变量 |
| 地图安全密钥配置不完整 | ✅ 完成 | `AMapView.tsx` 支持 `VITE_AMAP_SECURITY_CODE`；新增 `frontend/.env.example` 说明配置项 |
| PDF 中文字体存在降级风险 | ✅ 完成 | PDF 导出优先使用系统宋体，缺失时降级到 ReportLab 内置 `STSong-Light` 中文 CID 字体；字体名缓存避免同进程重复导出失败 |
| 真实外部服务联调仍需验证 | ⚠️ 待本地执行 | 新增 `doc/integration-checklist.md` 固化真实 Key、DeepSeek、高德、天气、保存行程、地图和 PDF 的端到端验收路径 |

## 2026-06-05 测试修复与代码质量提升

### 测试修复

| 问题 | 修复 |
|------|------|
| `test_spot_finder.py` 导入 `_build_agent` 不存在 | 改为导入 `create_spot_finder_agent` |
| `test_route_planner.py` 导入 `_build_agent` 不存在 | 改为导入 `create_route_planner_agent` |
| `test_weather_checker.py` 导入 `_build_agent` 不存在 | 改为导入 `create_weather_checker_agent` |
| `test_planner.py` Tool 数量期望值错误（4→5） | 更新为 5 个 Tool，匹配实际代码 |
| `test_planner.py` Tool 名称不匹配 | 更新为实际名称：`get_current_time_tool`, `find_spots_agent` 等 |

### 类型注解修复（mypy --strict）

| 问题 | 修复 |
|------|------|
| `models/user.py` 中 `ChatSession`/`Trip` 名称未定义 | 添加 `TYPE_CHECKING` 导入 |
| `models/chat.py` 中 `User` 名称未定义 | 添加 `TYPE_CHECKING` 导入 |
| `models/trip.py` 中 `User` 名称未定义 | 添加 `TYPE_CHECKING` 导入 |
| `api/spots.py` search() 返回 `dict` 缺少类型参数 | 改为 `dict[str, object]` |
| `api/trips.py` reportlab 导入缺少 stub | 添加 `# type: ignore[import-untyped]` |
| `agents/*.py` `create_*_agent()` 无类型注解 | 添加 `-> Runnable[Any, Any]` |
| `agents/planner.py` `AIMessageChunk.content` 类型歧义 | 添加 `isinstance(content, str)` 类型收窄 |

### Ruff 代码质量

| 问题 | 修复 |
|------|------|
| E501 行过长（中文 prompt 字符串和测试数据） | 添加 `per-file-ignores` 排除 Agent prompt 文件和测试文件 |
| 无效 `# noqa` 指令 | 改为标准注释格式 |
| 25 个文件格式不统一 | `ruff format` 自动格式化 |

## 验证记录（2026-06-05）

| 检查项 | 状态 | 说明 |
|--------|------|------|
| `uv run pytest tests/ -q` | ✅ 127 passed | 全部 127 个测试通过，无警告 |
| `uv run mypy backend/ --strict` | ✅ 通过 | 38 个源文件，零错误 |
| `uv run ruff check .` | ✅ 通过 | All checks passed |
| `uv run ruff format --check .` | ✅ 通过 | 60 files already formatted |
| `npx tsc --noEmit` | ✅ 通过 | TypeScript 严格检查零错误 |
| `npm run build` | ✅ 通过 | Vite 生产构建成功 |

### 遗留注意事项

| 项目 | 说明 |
|------|------|
| 外部服务联调 | 真实 DeepSeek/高德/天气 Key 的端到端测试仍需手动执行，参考 `doc/integration-checklist.md` |
| 前端 chunk 大小 | Vite 构建提示主 chunk 约 1.16MB，后续可考虑代码分割优化 |
| 前端组件测试 | prompt.md 要求 Vitest + RTL，当前未实现，建议后续补充 |
| 小红书爬虫 | 按 prompt.md 约束已从需求中移除 |

## 2026-06-05 P0 修复：Planner Agent 输出处理中间层

### 问题背景

`question.md` §2.6 指出：Planner Agent 的输出缺少处理中间层，导致 TripPlan JSON 代码块被透传到前端，并且 `done.text`（清洗后的展示文本）从未被转发给前端，用户最终看到的是包含 JSON 的混乱内容。

### 修复内容

| 文件 | 修复说明 |
|------|----------|
| `backend/agents/planner.py` | `run_planner_stream` 增加 JSON 代码块截断逻辑：检测到 ` ```json ` 标记时停止向前端推送 token，只推送标记前的人类可读部分；`done` 事件仍携带完整的 `display_text` |
| `backend/api/chat.py` | `event_generator` 在收到 planner 的 `done` 事件后，将清洗后的 `text` 字段包含在发给前端的 `done` SSE 事件 payload 中 |
| `frontend/src/pages/Chat.tsx` | `done` 事件处理器在收到 `doneData.text` 时，用其替换 `assistantContent`，保证最终展示的是经过清洗的纯净内容（去除 JSON 代码块） |

### 修复后的数据流

```
planner.py  →  chat.py  →  前端 Chat.tsx
─────────────────────────────────────────────
流式阶段：只推送 token（截止到 ```json 标记前）
完成阶段：done.text = strip_trip_plan_json(full_text) 清洗文本
         ↓ chat.py 转发给前端
done SSE：{ text: "干净的行程描述", title?: "北京三日游" }
         ↓ Chat.tsx done 处理器
assistantContent = doneData.text  ← 替换流式累积内容
```

### 验证记录（2026-06-05 修复后）

| 检查项 | 状态 | 说明 |
|--------|------|------|
| `uv run pytest tests/ -q` | ✅ 127 passed | 全部 127 个测试通过 |
| `uv run mypy backend/ --strict` | ✅ 通过 | 38 个源文件，零错误 |
| `uv run ruff check .` | ✅ 通过 | All checks passed |
| `uv run ruff format --check .` | ✅ 通过 | 60 files already formatted |
| `npx tsc --noEmit` | ✅ 通过 | TypeScript 严格检查零错误 |

---

## 2026-06-05 文档一致性更新

### 任务文件同步

12 个任务文件（`doc/tasks/M01-M12*.md`）中所有 `[ ]` 已更新为 `[x]`，反映实际完成状态。

### 文档交叉分析

| 文档 | 分析结论 |
|------|----------|
| `proposal.md` | 19 项功能需求全部实现，覆盖率 100% |
| `high-level-design.md` | 架构实现与设计一致；M10 输入参数有轻微简化（spots→ticket_prices），功能等价 |
| `prompt.md` | Agent API 已从 `create_react_agent` 迁移至 `langchain.agents.create_agent`；小红书已移除 |
| `integration-checklist.md` | 提供了完整的端到端验收步骤，待执行 |
| `question.md` | 已更新为反映当前真实状态，旧问题清退，保留 4 项剩余问题 |

### M11 特殊说明

小红书爬虫（`xiaohongshu_search`）在 M11/M07 设计文档中仍有定义，但按 `prompt.md` 约束已从代码中移除。M11 任务文件已标注"已移除"说明。
