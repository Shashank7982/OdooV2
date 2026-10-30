Write-Host "=== Cloudflare Tunnel Status ===" -ForegroundColor Cyan
$procs = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
if ($procs) {
    Write-Host "[OK] cloudflared is running (PID: $($procs.Id -join ', '))" -ForegroundColor Green
} else {
    Write-Host "[STOPPED] cloudflared is not currently running." -ForegroundColor Red
}

Write-Host "`n=== Testing Domain Reachability ===" -ForegroundColor Cyan
try {
    $res = Invoke-WebRequest -Uri "https://hireverse.dpdns.org/web/login" -UseBasicParsing -TimeoutSec 7
    Write-Host "[OK] https://hireverse.dpdns.org responded with HTTP $($res.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Could not reach https://hireverse.dpdns.org: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Odoo Configuration Parameters ===" -ForegroundColor Cyan
try {
    & "D:\odooV2\.venv\Scripts\python.exe" -c "
import odoo
odoo.tools.config.parse_config(['-c', 'odoo.conf'])
registry = odoo.registry('odoov2db')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    ICP = env['ir.config_parameter']
    print('web.base.url       :', ICP.get_param('web.base.url'))
    print('web.base.url.freeze:', ICP.get_param('web.base.url.freeze'))
"
} catch {
    Write-Host "Could not query Odoo parameters: $_" -ForegroundColor Yellow
}

Write-Host "`n=== Recent Tunnel Logs ===" -ForegroundColor Cyan
if (Test-Path "C:\Users\shash\.cloudflared\tunnel.log") {
    Get-Content "C:\Users\shash\.cloudflared\tunnel.log" -Tail 10
}
