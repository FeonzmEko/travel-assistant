# 旅游助手 — 总体开发进度

## 模块完成状态

### 第一期：基础框架 + 核心功能

- [x] **M12 数据访问模块** — 数据库 ORM 与数据持久化
- [x] **M2 用户管理模块** — 注册、登录、认证、个人信息
- [x] **M11 外部服务集成模块** — 高德地图、天气、小红书等 API 封装
- [x] **M3 景点查询模块** — 景点搜索与详情

### 第二期：Agent 层 + 智能功能

- [x] **M7 景点 Agent** — 景点搜索与筛选 Agent（使用 `create_react_agent`，拥有独立 LLM 推理）
- [x] **M8 路线 Agent** — 路线规划与交通方案 Agent（使用 `create_react_agent`，支持多条备选路线）
- [x] **M9 天气 Agent** — 天气查询与影响评估 Agent（使用 `create_react_agent`）
- [x] **M10 预算 Agent** — 费用估算与预算控制 Agent（使用 `create_react_agent`）
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
1. 将所有子 Agent（`spot_finder.py`、`route_planner.py`、`weather_checker.py`、`budget_estimator.py`）改为使用 `langgraph.prebuilt.create_react_agent`
2. 每个子 Agent 拥有独立的 LLM 实例和专属工具
3. `planner.py` 中将子 Agent 包装为 LangChain Tool（`find_spots_agent`、`plan_route_agent`、`check_weather_agent`、`estimate_budget_agent`），注册到 Planner Agent
4. Planner Agent 通过 ReAct 推理自动调度子 Agent，实现层级协作

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
