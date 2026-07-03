param(
    [switch]$Reload
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Push-Location -Path (Join-Path $scriptDir "healthcare-backend")
Write-Host "Starting uvicorn in healthcare-backend..."
if ($Reload) {
    uvicorn app.main:app --reload
} else {
    uvicorn app.main:app
}
Pop-Location
