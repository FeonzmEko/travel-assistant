# M4 — 行程管理模块

> 管理用户的行程计划，支持保存、查询、删除和导出（PDF）操作。

## 前置依赖

- M2 用户管理模块（认证依赖）
- M12 数据访问模块（Trip / TripDay / TripActivity CRUD）

## 任务列表

### 4.1 保存行程接口

- [x] 创建 `POST /api/trips` 路由（需认证）
- [x] 入参：`TripPlan` 结构体（含 days、activities、budget 等）
- [x] 级联创建 Trip → TripDay → TripActivity 记录
- [x] 返回 `{trip_id}`

### 4.2 行程列表接口

- [x] 创建 `GET /api/trips` 路由（需认证）
- [x] 入参：`page`、`size`
- [x] 返回当前用户的行程摘要列表（`TripSummary`）

### 4.3 行程详情接口

- [x] 创建 `GET /api/trips/{id}` 路由（需认证）
- [x] 验证行程所属用户
- [x] 级联查询并返回完整 `TripPlan`（含所有天和活动）

### 4.4 删除行程接口

- [x] 创建 `DELETE /api/trips/{id}` 路由（需认证）
- [x] 验证行程所属用户
- [x] 级联删除 Trip 及其关联的 TripDay / TripActivity

### 4.5 行程导出接口

- [x] 安装 PDF 生成库（如 `reportlab` 或 `weasyprint`）
- [x] 创建 `GET /api/trips/{id}/export` 路由（需认证）
- [x] 读取行程数据，渲染为 PDF 格式
- [x] 返回文件流响应（`StreamingResponse`）
