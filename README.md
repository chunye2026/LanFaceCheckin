# 网页版局域网打卡系统

基于 Flask、Vue 3、Element Plus 和 InsightFace 的局域网人脸识别考勤系统。系统包含公开监控大屏、管理员后台、成员管理、人脸样本录入、摄像头识别和考勤记录查询。

## 技术栈

- 后端: Python Flask, Flask-SQLAlchemy, SQLite/MySQL
- 前端: Vue 3, Vite, Element Plus
- 人脸识别: InsightFace buffalo_s, RetinaFace, ArcFace, ONNXRuntime

## 目录结构

```text
backend/                 后端服务
backend/routes/          API 路由
backend/uploads/         人脸样本上传目录，本地运行生成
backend/data/            SQLite 数据库目录，本地运行生成
backend/models/          InsightFace 模型目录，本地下载生成
frontend/                前端应用
frontend/src/views/      页面组件
download_model.bat       下载 InsightFace 模型
start.bat                启动已构建的生产服务
```

## 快速开始

1. 准备后端环境

```bash
cd backend
pip install -r requirements.txt
copy .env.example .env
```

编辑 `backend/.env`，至少设置一个强随机 `SECRET_KEY`。如果 `ADMIN_INIT_PASSWORD` 留空，首次启动会在控制台打印随机管理员密码。

2. 下载人脸识别模型

```bash
download_model.bat
```

3. 准备前端

```bash
cd frontend
npm install
npm run build
```

4. 启动服务

```bash
start.bat
```

默认访问地址: `http://127.0.0.1:5000`

## 开发模式

后端:

```bash
cd backend
python app.py
```

前端:

```bash
cd frontend
npm run dev
```

Vite 开发服务默认运行在 `http://127.0.0.1:5173`，API 会代理到后端 `5000` 端口。

## 使用流程

1. 访问 `/admin/login` 登录后台。
2. 新增成员，填写姓名、学号、班级等信息。
3. 在成员管理中录入 3 到 5 张人脸样本。
4. 在摄像头管理中启动识别。
5. 首页大屏查看实时识别和考勤统计，后台查看完整记录。

## 运行数据

以下内容为本地运行生成，已在 `.gitignore` 中忽略:

- `backend/.env`
- `backend/data/`
- `backend/uploads/`
- `backend/logs/`
- `backend/models/insightface/`
- `frontend/dist/`
- `frontend/node_modules/`
