# Jyothisha Studio: the website on this computer only (127.0.0.1), for making the paid reports.
# Every report is made, with boxes for the astrologer's notes and one that fills the form from a
# customer's pasted order. Started by "Jyothisha Studio.bat"; close this window to stop it.
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
. "$root\env.ps1"
$env:STUDIO = "1"
$port = 8765
$url = "http://127.0.0.1:$port/"
$server = Start-Process -FilePath "$root\.venv\Scripts\python.exe" -NoNewWindow -PassThru `
    -ArgumentList "-m", "uvicorn", "web.app:app", "--host", "127.0.0.1", "--port", "$port"
for ($i = 0; $i -lt 60; $i++) {
    try { Invoke-RestMethod "$($url)healthz" -TimeoutSec 2 | Out-Null; break } catch { Start-Sleep -Milliseconds 500 }
}
if (-not $env:STUDIO_NO_BROWSER) { Start-Process $url }   # (set by tests)
Write-Host ""
Write-Host "Jyothisha Studio is open at $url" -ForegroundColor Yellow
Write-Host "Keep this window open while you work; close it to stop the studio." -ForegroundColor Yellow
Wait-Process -Id $server.Id
