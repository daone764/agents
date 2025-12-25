@echo off
title Polymarket Trading Bot
cd /d "C:\Users\user\OneDrive\Desktop\polymarket\agents"
echo.
echo ============================================================
echo    POLYMARKET AUTONOMOUS TRADING BOT
echo ============================================================
echo.
echo Starting market analysis... (this takes 1-2 minutes)
echo.
"C:\Users\user\OneDrive\Desktop\polymarket\agents\.venv\Scripts\python.exe" "C:\Users\user\OneDrive\Desktop\polymarket\agents\polymarket_trader.py"
pause
