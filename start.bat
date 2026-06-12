@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo ============================================
echo   网页版局域网打卡系统
echo ============================================
echo.

if not exist "backend\.env" (
    echo [ERROR] 未找到 backend\.env
    echo 请先复制 backend\.env.example 为 backend\.env，并设置 SECRET_KEY。
    echo.
    pause
    exit /b 1
)

if not exist "frontend\dist\index.html" (
    echo [ERROR] 未找到 frontend\dist\index.html
    echo 请先执行:
    echo   cd frontend
    echo   npm install
    echo   npm run build
    echo.
    pause
    exit /b 1
)

if not exist "backend\models\insightface\models\buffalo_s\det_10g.onnx" (
    echo [WARN] InsightFace 模型文件不存在，识别功能将不可用。
    echo 可运行 download_model.bat 下载模型。
    echo.
)

echo 正在启动后端服务...
echo 默认地址: http://127.0.0.1:5000
echo.

cd backend
python app.py

endlocal
