@echo off
chcp 65001 >nul
cd /d "%~dp0"

where node >nul 2>nul
if errorlevel 1 (
  echo [Food Radar] 未检测到 Node.js。
  echo 请先安装 Node.js 20 或更高版本：https://nodejs.org/
  pause
  exit /b 1
)

if not exist "web\node_modules" (
  echo [Food Radar] 首次运行，正在安装 Web 依赖...
  call npm install
  if errorlevel 1 (
    echo [Food Radar] 依赖安装失败，请检查网络后重试。
    pause
    exit /b 1
  )
)

echo [Food Radar] 正在启动 Web 版...
start "Food Radar Web Server" /D "%~dp0" cmd /k npm run dev
timeout /t 2 /nobreak >nul
start "" "http://localhost:5173"
exit /b 0
