# 前端说明

这是局域网打卡系统的 Vue 3 前端，包含公开监控大屏和管理员后台。

## 常用命令

```bash
npm install
npm run dev
npm run build
```

开发服务默认端口为 `5173`，`vite.config.js` 会将 `/api` 和 `/uploads` 代理到后端 `http://127.0.0.1:5000`。

生产构建产物输出到 `frontend/dist/`，由 Flask 后端统一托管。
