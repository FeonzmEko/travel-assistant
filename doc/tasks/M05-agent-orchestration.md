# M5 — Agent 编排模块

> 后端 API 层与 Agent 层的桥梁。管理对话会话，将用户消息分发给规划 Agent，通过 SSE 推送流式响应。

## 前置依赖

- M2 用户管理模块（认证依赖）
- M6 规划 Agent
- M12 数据访问模块（ChatSession / ChatMessage CRUD）

## 任务列表

### 5.1 对话会话管理

- [ ] 创建 `POST /api/chat/session` 路由（需认证）— 创建新对话会话
- [ ] 创建 `GET /api/chat/sessions` 路由（需认证）— 获取用户的会话列表
- [ ] 创建 `GET /api/chat/session/{id}/history` 路由（需认证）— 获取对话历史

### 5.2 SSE 流式响应基础设施

- [ ] 安装依赖：`sse-starlette`
- [ ] 实现 SSE 事件生成器（将 Agent 的 streaming 输出转换为 SSE 事件）
- [ ] 定义 SSE 事件类型：`token`、`tool_call`、`tool_result`、`trip_plan`、`done`、`error`

### 5.3 消息发送与 Agent 调用

- [ ] 创建 `POST /api/chat/message` 路由（需认证）
- [ ] 保存用户消息到数据库
- [ ] 加载对话历史，构建 LangChain Memory
- [ ] 调用规划 Agent（M6），传入消息和上下文
- [ ] 将 Agent 响应以 SSE 流式推送给前端
- [ ] 保存 Assistant 响应到数据库

### 5.4 错误处理与超时

- [ ] 处理 Agent 调用超时的情况
- [ ] 处理 LLM 服务不可用的异常
- [ ] SSE 连接断开时的资源清理
