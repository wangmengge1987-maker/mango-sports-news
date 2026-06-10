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

REM 仅在交互式命令行中暂停，计划任务中不等待
echo %SESSIONNAME% | findstr /i "Console" > nul
if not errorlevel 1 (
    pause
)
