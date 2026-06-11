# M12 — 数据访问模块

> 封装 SQLite 数据库操作，提供数据模型的 CRUD 接口。所有其他后端模块依赖此模块。

## 任务列表

### 12.1 项目初始化与数据库配置

- [x] 初始化 FastAPI 项目骨架（目录结构、`main.py`、`pyproject.toml`）
- [x] 安装依赖：`fastapi`、`uvicorn`、`sqlalchemy`、`pydantic`
- [x] 配置 SQLAlchemy 引擎，连接 SQLite 数据库（`database.py`）
- [x] 创建 `Base` 声明基类和数据库会话工厂（`get_db` 依赖注入）

### 12.2 用户相关模型

- [x] 定义 `User` ORM 模型（`models/user.py`）：`id, username, password_hash, email, created_at`
- [x] 编写 `UserCreate` / `UserOut` Pydantic Schema
- [x] 实现 User CRUD 函数：`create_user`、`get_user_by_id`、`get_user_by_username`、`update_user`

### 12.3 对话相关模型

- [x] 定义 `ChatSession` ORM 模型：`id, user_id, title, created_at, updated_at`
- [x] 定义 `ChatMessage` ORM 模型：`id, session_id, role, content, created_at`
- [x] 编写对应 Pydantic Schema
- [x] 实现 ChatSession CRUD：`create_session`、`get_sessions_by_user`、`get_session_by_id`
- [x] 实现 ChatMessage CRUD：`add_message`、`get_messages_by_session`

### 12.4 行程相关模型

- [x] 定义 `Trip` ORM 模型：`id, user_id, title, destination, start_date, end_date, budget_total, budget_breakdown, created_at, updated_at`
- [x] 定义 `TripDay` ORM 模型：`id, trip_id, day_index, date, weather`
- [x] 定义 `TripActivity` ORM 模型：`id, trip_day_id, order_index, spot_name, time_slot, transport, notes, estimated_cost, longitude, latitude`
- [x] 编写对应 Pydantic Schema（`TripPlan`、`TripSummary` 等）
- [x] 实现 Trip CRUD：`create_trip`、`get_trips_by_user`、`get_trip_by_id`、`delete_trip`
- [x] 实现 TripDay / TripActivity 的级联创建与查询

### 12.5 景点缓存模型

- [x] 定义 `SpotCache` ORM 模型：`id, source, source_id, name, city, longitude, latitude, type_tags, description, images, rating, open_time, ticket_price, review_summary, cached_at`
- [x] 编写对应 Pydantic Schema
- [x] 实现 SpotCache CRUD：`upsert_spot`、`search_spots_by_keyword`、`get_spot_by_source_id`

### 12.6 数据库迁移与初始化脚本

- [x] 编写 `init_db.py`，自动创建所有表（`Base.metadata.create_all`）
- [x] 验证所有表成功创建，字段和约束正确
