@echo off
:: 设置CMD窗口标题
title AirNavigator

:: 切换到conda环境
cd E:\yolo\Scripts
./activate.bat
E:\yolo\Scripts\python.exe use_cmd.py
pause
