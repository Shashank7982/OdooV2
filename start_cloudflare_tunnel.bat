@echo off
echo Starting Cloudflare Tunnel for Odoo...
wscript.exe "C:\Users\shash\.cloudflared\start_tunnel.vbs"
echo Cloudflare Tunnel launched in background.
echo Run check_cloudflare_tunnel.ps1 in PowerShell to verify connectivity.
pause
