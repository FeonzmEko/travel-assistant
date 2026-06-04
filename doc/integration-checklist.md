# 真实外部服务联调清单

## 环境变量

后端 `.env`：

```env
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
AMAP_API_KEY=your-amap-web-service-key
WEATHER_API_KEY=your-weather-api-key
JWT_SECRET_KEY=replace-with-a-random-secret
DATABASE_URL=sqlite+aiosqlite:///./travel_assistant.db
```

前端 `frontend/.env`：

```env
VITE_AMAP_KEY=your-amap-js-api-key
VITE_AMAP_SECURITY_CODE=your-amap-js-security-code
```

## 验收路径

1. 启动后端和前端，确认注册、登录、个人信息页可用。
2. 搜索一个国内城市景点，确认返回景点名称、经纬度、评分和详情页地图。
3. 在对话页生成完整行程，确认 Planner 调度景点、天气、路线和预算 Agent。
4. 保存行程后进入行程详情页，确认天气、预算、每日安排、地图标点和路线展示。
5. 导出 PDF，确认中文内容正常显示。
6. 检查服务日志中 DeepSeek、高德 POI、高德路线和天气接口无鉴权、额度或字段解析错误。
