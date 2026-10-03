@echo off
title Dividend Screener 15-Min Auto-Refresh Daemon
echo =====================================================================
echo  Starting Autonomous 15-Minute Screener Refresh Daemon
echo  Refreshes data every 15 minutes even when Streamlit app is closed
echo =====================================================================
cd /d "%~dp0"
python screener_daemon.py --interval 900
pause
