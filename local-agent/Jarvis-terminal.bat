@echo off
chcp 65001 >nul
title Jarvis (terminal)
cd /d "%~dp0"
python agent.py %*
pause
