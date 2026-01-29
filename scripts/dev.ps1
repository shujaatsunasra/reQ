# FloatChat Development Startup Script
# Run both frontend and backend for development

Write-Host "🌊 FloatChat Development Environment" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$apiDir = Join-Path $projectRoot "apps\api"
$webDir = Join-Path $projectRoot "apps\web"

# Check if virtual environment exists
if (-not (Test-Path $venvPython)) {
    Write-Host "❌ Python virtual environment not found at $venvPython" -ForegroundColor Red
    Write-Host "Please create it with: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n📦 Checking dependencies..." -ForegroundColor Yellow

# Check if node_modules exists
if (-not (Test-Path (Join-Path $webDir "node_modules"))) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location $webDir
    pnpm install
    Pop-Location
}

Write-Host "`n🚀 Starting services..." -ForegroundColor Green
Write-Host "   Backend API: http://localhost:8000" -ForegroundColor White
Write-Host "   API Docs:    http://localhost:8000/docs" -ForegroundColor White
Write-Host "   Frontend:    http://localhost:3000" -ForegroundColor White
Write-Host "`nPress Ctrl+C to stop all services" -ForegroundColor Yellow

# Start backend in background
Write-Host "`n🐍 Starting Python backend..." -ForegroundColor Cyan
$backendJob = Start-Job -ScriptBlock {
    param($pythonPath, $apiPath)
    Set-Location $apiPath
    & $pythonPath -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
} -ArgumentList $venvPython, $apiDir

# Give backend a moment to start
Start-Sleep -Seconds 2

# Start frontend in foreground
Write-Host "⚛️  Starting Next.js frontend..." -ForegroundColor Cyan
Push-Location $webDir
try {
    pnpm dev
}
finally {
    # Cleanup on exit
    Write-Host "`n🛑 Stopping backend..." -ForegroundColor Yellow
    Stop-Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob -Force -ErrorAction SilentlyContinue
    Pop-Location
}
