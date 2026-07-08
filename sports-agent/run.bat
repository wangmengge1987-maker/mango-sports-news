@echo off
chcp 65001 > nul
cd /d "%~dp0"

REM =============================================
REM  本地任务 vs GitHub Actions 防重复协调机制
REM  标记文件: output/.last_push_date（仓库跟踪）
REM =============================================

setlocal enabledelayedexpansion

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "TODAY=%%i"

REM 先把同步代码（含 .last_push_date）拉下来
echo [协调] 同步远程仓库...
git pull --rebase --autostash >nul 2>&1
if %errorlevel% equ 0 (
    echo [协调] 同步成功
) else (
    echo [协调] 同步失败，继续执行本地逻辑
)

REM 检查今天是否已被推送（本地标记或 GitHub Actions 留下的标记）
if exist "output\.last_push_date" (
    set /p LASTPUSH=<"output\.last_push_date"
    if "!LASTPUSH!"=="%TODAY%" (
        echo [协调] 今天 (%TODAY%) 已被 GitHub Actions 或本地推送过，跳过执行
        goto :end
    )
)

if /i "%1"=="push" (
    python main.py --push
) else if /i "%1"=="push-only" (
    python main.py --push-only
) else (
    python main.py %*
)

set "PYEXIT=%errorlevel%"

echo.
if %PYEXIT% neq 0 (
    echo [错误] 执行失败，请检查控制台输出
) else (
    echo [成功] 完成

    REM 推送成功后，更新共享标记文件并同步到 GitHub
    echo %TODAY% > "output\.last_push_date"
    echo [协调] 已更新推送标记

    git add "output\.last_push_date"
    git commit -m "标记简报已推送 %TODAY%" >nul 2>&1
    git push >nul 2>&1
    if %errorlevel% equ 0 (
        echo [协调] 标记已同步到 GitHub
    ) else (
        echo [协调] 标记同步失败（下次会再同步）
    )
)

:end
REM 仅在交互式命令行中暂停，计划任务中不等待
echo %SESSIONNAME% | findstr /i "Console" > nul
if not errorlevel 1 (
    pause
)
