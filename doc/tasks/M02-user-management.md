# M2 — 用户管理模块

> 处理用户注册、登录/登出、JWT 身份认证和个人信息管理。

## 前置依赖

- M12 数据访问模块（User CRUD）

## 任务列表

### 2.1 密码工具与 JWT 配置

- [ ] 安装依赖：`passlib[bcrypt]`、`python-jose[cryptography]`
- [ ] 编写密码哈希/验证工具函数（`utils/security.py`）
- [ ] 编写 JWT Token 生成/验证函数，配置 `SECRET_KEY`、过期时间
- [ ] 实现 `get_current_user` FastAPI 依赖（从请求头解析 Token）

### 2.2 注册接口

- [ ] 创建 `POST /api/auth/register` 路由
- [ ] 入参校验：`username`（唯一性）、`password`（长度）、`email`（格式）
- [ ] 密码哈希后存储，返回 `{user_id, username}`
- [ ] 处理用户名/邮箱重复的异常

### 2.3 登录接口

- [ ] 创建 `POST /api/auth/login` 路由
- [ ] 校验用户名和密码，签发 JWT Token
- [ ] 返回 `{access_token, token_type: "bearer"}`

### 2.4 登出接口

- [ ] 创建 `POST /api/auth/logout` 路由（需认证）
- [ ] 返回 `{message: "已登出"}`（JWT 无状态方案，前端删除 Token 即可）

### 2.5 个人信息接口

- [ ] 创建 `GET /api/user/profile` 路由（需认证）
- [ ] 创建 `PUT /api/user/profile` 路由（需认证）
- [ ] 支持修改 `username`、`email`，并校验唯一性
