@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==============================================
echo  穿搭助手 - Outfit Assistant
echo ==============================================
python main.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 运行失败，请检查依赖是否安装。
    echo 请运行: pip install -r requirements.txt
    pause
)
