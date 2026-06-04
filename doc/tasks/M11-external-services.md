# M11 — 外部服务集成模块

> 封装所有第三方 API 调用，提供统一 Python 函数接口，处理请求构造、响应解析、错误重试和限流。

## 前置依赖

- 无后端模块依赖，需要外部 API Key

## 任务列表

### 11.1 通用基础设施

- [ ] 安装依赖：`httpx`（异步 HTTP 客户端）
- [ ] 编写 API Key 配置管理（从环境变量 / `.env` 文件读取）
- [ ] 实现通用的异步 HTTP 请求封装（含重试、超时、错误处理）
- [ ] 实现简易的请求频率限制器（令牌桶或滑动窗口）

### 11.2 高德 POI 搜索（`amap_poi_search`）

- [ ] 注册高德开放平台，获取 Web 服务 API Key
- [ ] 实现 `amap_poi_search(keyword, city, type?, page?, size?)` 函数
- [ ] 解析高德 POI 搜索响应，转换为标准 `Spot` 数据结构
- [ ] 处理无结果、API 错误等边界情况

### 11.3 高德路径规划（`amap_route_plan`）

- [ ] 实现 `amap_route_plan(origin, destination, waypoints?, strategy?)` 函数
- [ ] 支持驾车 / 公交 / 步行路径规划
- [ ] 解析响应，提取距离、耗时、路线段信息
- [ ] 返回标准 `Route` 数据结构

### 11.4 天气查询（`weather_query`）

- [ ] 选定天气 API（高德天气或和风天气），获取 Key
- [ ] 实现 `weather_query(city, date_range?)` 函数
- [ ] 解析响应，提取温度、天气状况、风力、降水概率
- [ ] 返回标准天气数据结构

### 11.5 小红书数据爬取（`xiaohongshu_search`）

- [ ] 分析小红书搜索页接口，确定爬取方案
- [ ] 实现 `xiaohongshu_search(keyword, count?)` 函数
- [ ] 提取笔记标题、内容摘要、点赞数、图片等字段
- [ ] 加入反爬应对策略（User-Agent、请求间隔等）
- [ ] 返回标准化的攻略数据结构

### 11.6 费用估算（`budget_estimate`）

- [ ] 实现 `budget_estimate(trip_days, spots, transport_mode?)` 函数
- [ ] 基于规则估算：门票、交通、餐饮、住宿各项费用
- [ ] 返回 `{total, breakdown}` 结构
