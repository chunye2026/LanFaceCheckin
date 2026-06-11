# 人脸识别局域网打卡系统

## 技术栈
- 后端: Python Flask + SQLite + face-recognition
- 前端: Vue 3 + Element Plus + Vite
- 人脸识别: face-recognition (基于dlib)

## 快速开始

### 1. 安装后端依赖
```bash
cd backend
pip install -r requirements.txt
```

### 2. 安装前端依赖
```bash
cd frontend
npm install
```

### 3. 构建前端
```bash
cd frontend
npm run build
```

### 4. 启动后端服务
```bash
cd backend
python app.py
```

服务启动后访问: http://127.0.0.1:5000

## 默认管理员
- 用户名: admin
- 密码: admin123

## 开发模式
前端开发（热更新，端口5173）:
```bash
cd frontend
npm run dev
```

后端开发:
```bash
cd backend
python app.py
```

开发模式下前端自动代理API到后端5000端口。

## 使用流程
1. 管理员登录后台 (http://127.0.0.1:5000/#/admin/login)
2. 新增成员（填写姓名、工号等信息）
3. 为成员上传人脸照片（录脸）
4. 成员在打卡页面 (http://127.0.0.1:5000) 进行人脸签到/签退
5. 在后台查看打卡记录和操作日志
