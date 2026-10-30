@echo off
echo Stopping Cloudflare Tunnel...
taskkill /F /IM cloudflared.exe >nul 2>&1
echo Cloudflare Tunnel stopped.
pause
