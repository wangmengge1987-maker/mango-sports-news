@echo off
chcp 65001 > nul
cd /d "%~dp0"

if /i "%1"=="push" (
    python main.py --push
) else if /i "%1"=="push-only" (
    python main.py --push-only
) else (
    python main.py %*
)

echo.
if %errorlevel% neq 0 (
    echo [错误] 执行失败，请检查控制台输出
) else (
    echo [成功] 完成
)

pause
