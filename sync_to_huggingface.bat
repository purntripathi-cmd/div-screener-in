@echo off
title Hugging Face Space Sync Tool - PurnT/Screener
cd /d "%~dp0"

echo ======================================================================
echo    Syncing Production to Hugging Face Space: PurnT/Screener
echo ======================================================================
echo.

python sync_to_huggingface.py %*

echo.
echo Press any key to exit...
pause >nul
