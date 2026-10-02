@echo off
chcp 65001 >nul
title Jarvis
cd /d "%~dp0"
python agent.py --web %*
if errorlevel 1 pause
