# Jyothisha Insight environment for this PowerShell session.
# Usage (dot-source, so the settings stay in your terminal):   . .\env.ps1

# 1. Activate the Python 3.14 venv
& (Join-Path $PSScriptRoot ".venv\Scripts\Activate.ps1")

# 2. UTF-8 console output (Sinhala text)
$env:PYTHONIOENCODING = "utf-8"

# 3. Let Pango find ./fonts by family name (the script's file:// font URLs fail on Windows)
$env:FONTCONFIG_FILE = Join-Path $PSScriptRoot "fonts.conf"

# 4. Use MSYS2's current Pango/HarfBuzz
#    (don't reinstall the 2022 GTK3 runtime: its DLLs clash with these and it mis-spaces Sinhala)
$env:WEASYPRINT_DLL_DIRECTORIES = "C:\msys64\ucrt64\bin"

Write-Host "Jyothisha env ready: $(python --version), fonts.conf + MSYS2 Pango"
