Param(
    [string]$EnvFile = ".env"
)

Write-Host "Creating venv (if not exists) and activating..."
if (-not (Test-Path -Path .\venv)) {
    python -m venv .\venv
}
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
. .\venv\Scripts\Activate.ps1

Write-Host "Upgrading pip and installing requirements..."
python -m pip install --upgrade pip
pip install -r requirements.txt

if (Test-Path $EnvFile) {
    Write-Host "Loading env from $EnvFile"
    Get-Content $EnvFile | Foreach-Object {
        if ($_ -match '^\s*#') { return }
        if ($_ -match '=') {
            $parts = $_ -split '=', 2
            $name = $parts[0].Trim()
            $val = $parts[1].Trim().Trim("\"")
            Set-Item -Path env:$name -Value $val
        }
    }
}

Write-Host "Starting app..."
python .\clinic_app.py
