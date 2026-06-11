# 旅游助手 — 当前问题与后续优化清单

> 更新时间：2026-06-05（最新追加：Planner Agent 输出透传问题）
> 说明：本文档基于对所有 `doc/` 文档（proposal、high-level-design、prompt、各任务文件）与实际代码的交叉分析，记录当前状态、剩余问题和优化建议。

---

## 一、文档与代码一致性分析

### 1.1 任务文件状态（doc/tasks/）

| 任务文件 | 文档状态 | 实际状态 | 差异说明 |
|----------|----------|----------|----------|
| M12-data-access.md | 全部 `[ ]` 未勾选 | ✅ 已完成 | ORM 模型、CRUD、数据库初始化均已实现 |
| M02-user-management.md | 全部 `[ ]` 未勾选 | ✅ 已完成 | 注册/登录/个人信息 API 均已实现并通过测试 |
| M11-external-services.md | 全部 `[ ]` 未勾选 | ✅ 已完成 | 高德 POI/路线、天气、预算服务已实现；小红书已移除 |
| M03-spot-query.md | 全部 `[ ]` 未勾选 | ✅ 已完成 | 搜索/详情 API、缓存策略已实现 |
| M04-trip-management.md | 全部 `[ ]` 未勾选 | ✅ 已完成 | CRUD + PDF 导出已实现 |
| M05-agent-orchestration.md | 全部 `[ ]` 未勾选 | ✅ 已完成 | SSE 流式推送、会话管理已实现 |
| M06-planner-agent.md | 全部 `[ ]` 未勾选 | ✅ 已完成 | 规划 Agent + 子 Agent 调度已实现 |
| M07-spot-agent.md | 全部 `[ ]` 未勾选 | ✅ 已完成 | 使用 `langchain.agents.create_agent` |
| M08-route-agent.md | 全部 `[ ]` 未勾选 | ✅ 已完成 | 含 multi_route 多条路线对比 |
| M09-weather-agent.md | 全部 `[ ]` 未勾选 | ✅ 已完成 | 天气查询 + 影响评估 |
| M10-budget-agent.md | 全部 `[ ]` 未勾选 | ✅ 已完成 | 费用估算 + 超预算提示 |
| M01-frontend.md | 全部 `[ ]` 未勾选 | ✅ 已完成 | 所有页面和组件均已实现 |

### 1.2 设计文档与实际实现的差异

| 文档位置 | 文档描述 | 实际实现 | 差异评估 |
|----------|----------|----------|----------|
| M11/M07 - 小红书爬虫 | 包含 `xiaohongshu_search` 工具 | 未实现（prompt.md 明确移除） | 一致，已按 prompt.md 执行 |
| high-level-design M10 输入 | `{trip_days, spots, routes, budget_limit}` | `{trip_days, ticket_prices, transport_mode, budget_limit}` | 轻微简化，功能等价 |
| prompt.md Agent 构建 | `create_react_agent` | `langchain.agents.create_agent` | 已更新为最新 API |
| high-level-design 数据库 | `budget_breakdown` 为 JSON 类型 | SQLite Text 字段存储 | SQLite 无原生 JSON，用 Text 替代合理 |
| trip_activities 经纬度 | 设计未包含 | 实际增加了 `longitude`/`latitude` | 正向扩展，支持地图展示 |
| M11 天气服务 | `city, date_range?` 参数 | `city` 单参数（高德天气 API 返回全部预报） | 实现简化，使用方自行过滤日期 |

---

## 二、当前遗留问题

### 2.2 任务文件未勾选（P2 — 文档债务）

| 项目 | 说明 |
|------|------|
| 现状 | 12 个任务文件（M01-M12）中所有任务项仍为 `[ ]` 未勾选状态 |
| 影响 | 新开发者阅读文档时无法判断实际进度 |
| 建议 | 将全部已完成模块的 `[ ]` 改为 `[x]` |

### 2.3 前端 chunk 较大（P3 — 性能优化）

| 项目 | 说明 |
|------|------|
| 现状 | Vite 构建后主 chunk 约 1.16MB（含 Ant Design + 高德地图） |
| 影响 | 首屏加载可能较慢 |
| 建议 | 后续考虑路由懒加载和代码分割 |

### 2.4 前端测试缺失（P2 — 质量）

| 项目 | 说明 |
|------|------|
| 现状 | prompt.md 要求前端有 Vitest + React Testing Library 测试，但实际未实现 |
| 影响 | 前端 UI 变更无自动化回归保护 |
| 建议 | 后续为核心页面（Chat、TripDetail）补充组件测试 |

### 2.5 ReportLab 类型 stub 缺失（P3 — 工具链）

| 项目 | 说明 |
|------|------|
| 现状 | `reportlab` 无官方类型 stub，已用 `# type: ignore[import-untyped]` 处理 |
| 影响 | trips.py 中 reportlab 相关导入无类型检查 |
| 建议 | 可忽略，属生态系统限制 |

### 2.6 Planner Agent 输出缺少处理中间层，内容混乱透传（P0 — 核心功能缺陷）

**问题描述**

这是当前系统最核心的运行时缺陷：**前后端都没有对 Agent 的输出做任何处理就直接透传给了用户**，导致原始 JSON 数据、Agent 内部推理过程、多个子 Agent 返回的未合并内容全部混在一起展示出来。加上文本在某个环节被错误分词，每个字之间都有空格，整体内容既混乱又无法阅读。归根结底是缺少一个对 Agent 输出进行清洗、合并、结构化渲染的中间层。

**根因逐层分析**

**层一：`backend/agents/planner.py` — ReAct 推理步骤全量流出**

`run_planner_stream` 中监听 `astream_events` 时，对所有 `on_chat_model_stream` 事件不加区分地转发：

```python
if kind == "on_chat_model_stream":
    content = chunk.content
    if isinstance(content, str):
        full_text += content
        yield {"type": "token", "data": content}   # ← 包含了 ReAct 所有中间步骤
```

`on_chat_model_stream` 在 LangChain 的 ReAct 循环中会触发于每次 LLM 生成阶段，包括：
- `Thought: 我需要先搜索杭州景点...`（内部推理，不应展示）
- `Action: find_spots_agent`（工具调用决策文本）
- `Action Input: {"city": "杭州", ...}`（工具参数 JSON）
- 多轮循环叠加后的所有中间文本

这些本应是 Agent 内部状态，全部被作为 `token` 事件向后传递。

**层二：`backend/api/chat.py` — 清洗后的文本未送达前端**

`planner.py` 在流式结束后确实生成了清洗后的 `display_text`（去除 TripPlan JSON 代码块），并在内部 `done` 事件中携带：

```python
# planner.py：流结束时
display_text = strip_trip_plan_json(full_text) if trip_plan else full_text
yield {"type": "done", "data": {"text": display_text}}
```

但 `chat.py` 的 `event_generator` 接收到此 `done` 事件后，只将 `display_text` 写入 `full_response` 用于存库，**并未转发给前端**：

```python
# chat.py：done 事件处理
elif event_type == "done":
    done_data = event.get("data", {})
    if isinstance(done_data, dict):
        full_response = str(done_data.get("text", full_response))  # ← 仅存库
# ...
# 给前端的 done 事件只含 title，不含 text
yield {"event": "done", "data": json.dumps(done_payload, ensure_ascii=False)}
```

前端因此永远无法用干净文本替换流式积累的混乱内容。

**层三：`frontend/src/pages/Chat.tsx` — 无区分地累积所有 token**

前端对 `token` 事件一视同仁地拼接，无任何过滤：

```typescript
case 'token':
    assistantContent += evt.data;   // ← Thought/Action/JSON 全部追加
    updateLastMessage();
    break;
case 'done':
    // 只读 title，不读 text，无法替换为干净内容
    const doneData = JSON.parse(evt.data);
    if (doneData.title) { ... }
    break;
```

最终渲染到用户面前的 `assistantContent` 包含了整个 ReAct 链路的全部原始输出。

**字符间空格问题**

文本在某个环节出现"每字之间有空格"（如"你 好 世 界"），可能原因：
- LangChain ReAct 格式化模板（`PromptTemplate`）在拼接时在 token 之间插入了空白占位符
- DeepSeek 的 tokenizer 在流式输出时将 Chinese 字符拆分为多个 token，相邻 token 边界处携带了空格
- `astream_events` 中部分 token chunk 的 `content` 字段本身以空格起头（常见于 Function Calling 模式下参数 JSON 的格式化输出被错误透传）

**缺少的处理中间层**

设计文档（`high-level-design.md` §3.5）要求 M5 Agent 编排模块"将 Agent 的 streaming 输出转换为 SSE 事件流"，但当前实现仅做了机械转发，未实现以下必要处理：

| 缺失能力 | 说明 |
|----------|------|
| 推理步骤过滤器 | 区分 ReAct 内部推理 token 与最终 Final Answer token，只将后者发送给用户 |
| 流结束替换机制 | 流式阶段结束后，用干净的 `display_text` 替换前端已累积的混乱内容 |
| 字符间空格清洗 | 对流出的每个 token chunk 做 normalize，去除异常空格 |
| 子 Agent 输出聚合 | 多个子 Agent 的工具结果由 Planner 统一汇总后再输出，而不是将中间 JSON 泄露到 token 流 |

**影响范围**

| 组件 | 文件 | 问题 |
|------|------|------|
| Planner 流式输出 | `backend/agents/planner.py` | `run_planner_stream` 对所有 LLM token 无差别转发 |
| Agent 编排层 | `backend/api/chat.py` | `event_generator` 中 `done.text` 未转发给前端 |
| 聊天前端 | `frontend/src/pages/Chat.tsx` | `token` 事件处理无过滤；`done` 处理器未用干净文本替换显示内容 |

**修复方向**

1. **后端过滤推理步骤**：在 `run_planner_stream` 中增加状态机，识别 Final Answer 阶段（可检测 LangChain 内置的 `on_chain_end` 事件中 `output` 字段获取最终文本），只在最终回答阶段才 yield `token` 事件；或改为等待 Agent 完成后再以非流式方式推送完整回复。
2. **转发 `display_text` 给前端**：`chat.py` 在收到 `planner.py` 的 `done` 事件后，将 `text` 字段包含在发给前端的 `done` 事件中。
3. **前端用 `done.text` 替换内容**：前端的 `done` 处理器接收到 `text` 后，用其替换 `assistantContent`，保证最终展示的是经过清洗的纯净内容。
4. **清洗字符间空格**：在 token 发送前后对 chunk 内容执行 `content.replace(' ', '')` 或使用正则替换连续空格，排除分词边界引入的异常空白。

---

## 三、需求覆盖度分析

对照 proposal.md 中定义的功能需求：

| 编号 | 需求 | 实现状态 | 验证方式 |
|------|------|----------|----------|
| U-01 | 用户注册 | ✅ | test_auth.py |
| U-02 | 用户登录/登出 | ✅ | test_auth.py |
| U-03 | 个人信息管理 | ✅ | test_auth.py |
| S-01 | 景点搜索 | ✅ | test_spots.py |
| S-02 | 景点详情 | ✅ | test_spots.py + SpotDetail.tsx |
| S-03 | 景点地图展示 | ✅ | AMapView.tsx |
| P-01 | 对话式行程规划 | ✅ | test_planner.py + test_chat.py |
| P-02 | 行程调整 | ✅ | Planner System Prompt |
| P-03 | 行程信息汇总 | ✅ | Planner 汇总输出 |
| R-01 | 路线推荐 | ✅ | test_route_planner.py |
| R-02 | 路线地图展示 | ✅ | AMapView.tsx + TripDetail.tsx |
| R-03 | 路线对比 | ✅ | RouteComparison.tsx |
| W-01 | 目的地天气 | ✅ | test_weather_checker.py |
| W-02 | 行程天气整合 | ✅ | WeatherCard.tsx + TripDetail.tsx |
| B-01 | 费用估算 | ✅ | test_budget.py |
| B-02 | 预算设置 | ✅ | budget_limit 参数 |
| B-03 | 费用明细 | ✅ | BudgetBreakdown.tsx |
| E-01 | 行程保存 | ✅ | test_trips.py |
| E-02 | 历史行程 | ✅ | test_trips.py |
| E-03 | 行程导出 PDF | ✅ | test_trips.py + export endpoint |

**覆盖率：19/19 需求全部实现 (100%)**

---

## 四、建议优先级

| 优先级 | 问题 | 理由 |
|--------|------|------|
| P0 | **Planner Agent 输出缺少处理中间层** | 当前用户看到的是 Agent 原始推理过程，内容混乱不可读，是最严重的用户体验缺陷 |
| P1 | 任务文件 checkbox 勾选 | 文档与代码一致性，降低维护困惑 |
| P2 | 前端组件测试 | 保护 UI 不因后续改动退化 |
| P3 | 前端 chunk 优化 | 性能优化，非阻塞 |
| P3 | ReportLab stub | 生态系统限制，可接受 |

---

## 五、技术债务跟踪

| 项目 | 严重度 | 预计工作量 | 建议期限 |
|------|--------|-----------|----------|
| **Planner 输出处理中间层（新增）** | **高** | **4-8h** | **演示前（阻塞）** |
| 前端测试 | 低 | 3-4h | 下个迭代 |
| 代码分割 | 低 | 1h | 下个迭代 |
| 任务文件更新 | 低 | 0.5h | 随时 |

> **注**：Planner 输出处理中间层的工作量估算包含：后端 `run_planner_stream` 推理步骤过滤（1-2h）+ `chat.py` done 事件转发 `text` 字段（0.5h）+ 前端 `Chat.tsx` 用 `done.text` 替换内容 + 空格清洗（1-2h）+ 联调测试（1-2h）。
