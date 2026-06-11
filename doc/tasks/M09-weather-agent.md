# M9 — 天气 Agent（Weather Checker）

> 查询目的地天气预报，评估天气对行程的影响并给出建议。

## 前置依赖

- M11 外部服务集成模块（`weather_query`）
- DeepSeek LLM

## 任务列表

### 9.1 Tool 定义

- [x] 用 `@tool` 装饰器注册 `weather_query` 为 LangChain Tool
- [x] 编写描述和 Pydantic 入参 Schema

### 9.2 Agent 构建

- [x] 编写天气 Agent 的 System Prompt（天气分析专家角色）
- [x] 使用 LangChain 构建 ReAct Agent
- [x] 定义输入 Schema：`{city, start_date, end_date}`
- [x] 定义输出 Schema：天气预报 + 影响评估 + 建议

### 9.3 包装为规划 Agent 的 Tool

- [x] 将天气 Agent 封装为 `check_weather` 函数
- [x] 编写函数签名和 docstring
- [x] 测试：输入 `{city: "杭州", start_date: "2026-07-01", end_date: "2026-07-03"}`，验证返回天气数据
