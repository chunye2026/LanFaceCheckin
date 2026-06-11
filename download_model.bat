@echo off
chcp 65001 >nul
echo ============================================
echo   InsightFace 模型下载工具
echo ============================================
echo.
echo 算法: RetinaFace (检测) + ArcFace (识别)
echo 大小: ~140MB
echo.
set MODEL_DIR=%~dp0backend\models\insightface\models\buffalo_s
set ZIP_FILE=%TEMP%\buffalo_s.zip

echo 目标路径: %MODEL_DIR%
echo.

if exist "%MODEL_DIR%\det_10g.onnx" (
    if exist "%MODEL_DIR%\w600k_r50.onnx" (
        echo [OK] 模型已存在，无需下载！
        goto :end
    )
)

echo 正在下载模型文件...
echo URL: https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_s.zip
echo.

powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_s.zip' -OutFile '%ZIP_FILE%'; Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%~dp0backend\models\insightface\models\' -Force; Remove-Item '%ZIP_FILE%'}"

if exist "%MODEL_DIR%\det_10g.onnx" (
    echo.
    echo ============================================
    echo  模型下载完成！
    echo  路径: %MODEL_DIR%
    echo ============================================
) else (
    echo.
    echo [ERROR] 下载失败，请手动下载:
    echo   https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_s.zip
    echo   解压到: %MODEL_DIR%
)

:end
pause
