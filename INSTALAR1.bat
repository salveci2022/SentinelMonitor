@echo off
title Instalador Sentinel Cliente
color 0A
echo ========================================
echo    SENTINEL - INSTALADOR CLIENTE
echo ========================================
echo.
echo Instalando dependencias...
pip install pyautogui sounddevice soundfile pynput requests numpy
echo.
echo ========================================
echo    INSTALACAO CONCLUIDA!
echo ========================================
echo.
echo Para iniciar, execute: python cliente_local.py
echo.
pause