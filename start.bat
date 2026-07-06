@echo off
chcp 65001 >nul
title B站视频总结助手

echo 🚀 启动 B站视频总结助手...
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请先安装 Python 3.10 或以上版本
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b
)

REM 检查依赖
echo 📦 检查依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo 📥 正在安装依赖（首次启动需要 1~2 分钟）...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    echo ✅ 依赖安装完成
)

REM 检查 .env 文件
if not exist .env (
    echo ⚠️ 未找到 .env 文件
    echo 请将 .env.example 重命名为 .env，并填入你的 Agnes API 密钥
    pause
    exit /b
)

echo ✅ 启动后端服务...
start http://127.0.0.1:8000
python -m uvicorn backend:app --host 127.0.0.1 --port 8000

pause