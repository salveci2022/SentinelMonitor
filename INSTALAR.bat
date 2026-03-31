@echo off
title Instalador Sentinel Ultimate
color 0A
echo ========================================
echo    SENTINEL ULTIMATE - INSTALADOR
echo ========================================
echo.
echo Instalando dependencias...
echo.
pip install pyautogui sounddevice soundfile pynput requests numpy reportlab
echo.
echo ========================================
echo    INSTALACAO CONCLUIDA!
echo ========================================
echo.
echo Para iniciar o programa, execute:
echo python sentinel_ultimate.py
echo.
pause