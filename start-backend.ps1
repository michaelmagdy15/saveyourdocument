Write-Host "----------------------------------------------------" -ForegroundColor Cyan
Write-Host "Initializing SAVEYOURDOCUMENT - FastAPI Backend Server..." -ForegroundColor Cyan
Write-Host "Powered by Mitrixo Systems" -ForegroundColor DarkGray
Write-Host "----------------------------------------------------" -ForegroundColor Cyan
uvicorn backend.main:app --reload --port 8000
