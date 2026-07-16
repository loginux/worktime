@echo off
chcp 65001 >nul
title WokTime 打包工具

echo ============================================
echo  WokTime - 打包为 exe
echo ============================================
echo.

:: 使用虚拟环境的 Python 和 PyInstaller
set VENV_DIR=%~dp0.venv
set PYTHON=%VENV_DIR%\Scripts\python.exe
set PYINSTALLER=%VENV_DIR%\Scripts\pyinstaller.exe

if not exist "%PYTHON%" (
    echo [错误] 未找到虚拟环境，请先执行:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

echo [1/3] 清理旧缓存...
if exist "%~dp0dist"    rmdir /s /q "%~dp0dist"
if exist "%~dp0build"   rmdir /s /q "%~dp0build"
if exist "%~dp0*.spec"  del /q "%~dp0*.spec" 2>nul
echo      完成

echo [2/3] 打包中，请稍候...
"%PYINSTALLER%" --onefile --name WokTime ^
    --add-data "app\templates;app\templates" ^
    --add-data "app\static;app\static" ^
    --add-data "app\holiday;app\holiday" ^
    --hidden-import flask ^
    --hidden-import flask_login ^
    --hidden-import flask_wtf ^
    --hidden-import flask_wtf.csrf ^
    --hidden-import wtforms ^
    --hidden-import jinja2 ^
    --hidden-import markupsafe ^
    --hidden-import werkzeug ^
    --hidden-import itsdangerous ^
    --hidden-import click ^
    --hidden-import blinker ^
    run.py

if %errorlevel% neq 0 (
    echo [错误] 打包失败，请检查上方日志。
    pause
    exit /b 1
)

echo.
echo [3/3] 打包成功！
echo.
echo   输出文件: %~dp0dist\WokTime.exe
echo.
echo   双击 dist\WokTime.exe 即可启动
echo   访问 http://127.0.0.1:5000
echo.
pause
