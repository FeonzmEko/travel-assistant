# M8 — 路线 Agent（Route Planner）

> 根据景点列表和用户偏好，调用高德路径规划 API 规划最优游览路线。

## 前置依赖

- M11 外部服务集成模块（`amap_route_plan`）
- DeepSeek LLM

## 任务列表

### 8.1 Tool 定义

- [ ] 用 `@tool` 装饰器注册 `amap_route_plan` 为 LangChain Tool
- [ ] 编写描述和 Pydantic 入参 Schema

### 8.2 Agent 构建

- [ ] 编写路线 Agent 的 System Prompt（路线规划专家角色）
- [ ] 使用 LangChain 构建 ReAct Agent
- [ ] 定义输入 Schema：`{spots: [Spot], transport_preference?}`
- [ ] 定义输出 Schema：`[Route]` 含路线段、距离、耗时

### 8.3 包装为规划 Agent 的 Tool

- [ ] 将路线 Agent 封装为 `plan_route` 函数
- [ ] 编写函数签名和 docstring
- [ ] 测试：输入多个杭州景点坐标，验证返回合理路线
