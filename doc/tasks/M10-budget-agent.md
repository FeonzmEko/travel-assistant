# M10 — 预算 Agent（Budget Estimator）

> 根据行程信息估算各项费用，结合用户预算约束进行调整建议。

## 前置依赖

- M11 外部服务集成模块（`budget_estimate`）
- DeepSeek LLM

## 任务列表

### 10.1 Tool 定义

- [x] 用 `@tool` 装饰器注册 `budget_estimate` 为 LangChain Tool
- [x] 编写描述和 Pydantic 入参 Schema

### 10.2 Agent 构建

- [x] 编写预算 Agent 的 System Prompt（预算分析专家角色）
- [x] 使用 LangChain 构建 ReAct Agent
- [x] 定义输入 Schema：`{trip_days, spots, routes, budget_limit?}`
- [x] 定义输出 Schema：`{total, breakdown, over_budget, suggestions?}`

### 10.3 包装为规划 Agent 的 Tool

- [x] 将预算 Agent 封装为 `estimate_budget` 函数
- [x] 编写函数签名和 docstring
- [x] 测试：输入 3 天行程数据和预算 3000，验证返回费用明细
