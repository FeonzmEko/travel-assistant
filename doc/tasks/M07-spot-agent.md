# M7 — 景点 Agent（Spot Finder）

> 根据搜索条件调用高德 POI 和小红书工具获取景点信息，经筛选排序后返回结构化数据。

## 前置依赖

- M11 外部服务集成模块（`amap_poi_search`、`xiaohongshu_search`）
- M12 数据访问模块（`spot_db_search`）
- DeepSeek LLM

## 任务列表

### 7.1 Tool 定义

- [ ] 用 `@tool` 装饰器注册 `amap_poi_search` 为 LangChain Tool
- [ ] 用 `@tool` 装饰器注册 `xiaohongshu_search` 为 LangChain Tool
- [ ] 用 `@tool` 装饰器注册 `spot_db_search` 为 LangChain Tool
- [ ] 为每个 Tool 编写描述和 Pydantic 入参 Schema

### 7.2 Agent 构建

- [ ] 编写景点 Agent 的 System Prompt（景点搜索专家角色）
- [ ] 使用 LangChain 构建 ReAct Agent，注册上述 Tool
- [ ] 定义输入 Schema：`{city, keyword?, type?, count?}`
- [ ] 定义输出 Schema：`[Spot]` 结构化景点列表

### 7.3 包装为规划 Agent 的 Tool

- [ ] 将景点 Agent 封装为 `find_spots` 函数
- [ ] 编写函数签名和 docstring，供规划 Agent 调用
- [ ] 测试：输入 `{city: "杭州", type: "自然风景"}`，验证返回景点列表
