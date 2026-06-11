# M6 — 规划 Agent（Planner）

> 核心 Agent。接收用户旅游需求，通过 ReAct 推理拆解任务、调度子 Agent、汇总生成行程方案。

## 前置依赖

- M7 景点 Agent、M8 路线 Agent、M9 天气 Agent、M10 预算 Agent
- DeepSeek LLM API Key

## 任务列表

### 6.1 LangChain 环境搭建

- [x] 安装依赖：`langchain`、`langchain-openai`（DeepSeek 兼容 OpenAI 接口）
- [x] 配置 DeepSeek LLM 连接（API Key、Base URL、模型名称）
- [x] 验证 LLM 基本调用正常（简单问答测试）

### 6.2 System Prompt 设计

- [x] 编写规划 Agent 的 System Prompt
- [x] 定义 Agent 角色：旅游规划专家
- [x] 明确输出格式要求（自然语言描述 + 结构化 TripPlan JSON）
- [x] 加入工具使用指引（何时调用哪个子 Agent）

### 6.3 子 Agent 注册为 Tool

- [x] 将 `find_spots`（M7）注册为 LangChain Tool
- [x] 将 `plan_route`（M8）注册为 LangChain Tool
- [x] 将 `check_weather`（M9）注册为 LangChain Tool
- [x] 将 `estimate_budget`（M10）注册为 LangChain Tool
- [x] 为每个 Tool 编写清晰的 `description` 和参数 Schema

### 6.4 Agent 构建与推理

- [x] 使用 LangChain 的 `create_react_agent` 或 `AgentExecutor` 构建 Agent
- [x] 配置 ReAct 推理循环的最大步数限制
- [x] 实现 streaming 输出（逐 token 返回）
- [x] 测试：输入 "帮我规划一个杭州3天的旅行"，验证完整 ReAct 流程

### 6.5 结构化行程输出

- [x] 实现从 Agent 文本输出中提取结构化 `TripPlan` JSON 的解析逻辑
- [x] 处理解析失败的降级方案（仅返回文本）
